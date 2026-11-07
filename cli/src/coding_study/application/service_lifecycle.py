"""The lifecycle commands of a service project (docs/specs/service-projects.md#lifecycle-commands):
what `cstudy start` adds after it copies the starter, the install and its record, and `cstudy test`.

Two clocks run here and stay apart (docs/specs/service-projects.md#two-clocks). Everything up to
the moment a stack is ready spends the startup budget, and a failure there says so and changes no
result. The limit on `commands.test`, and the run time this reports, start at that moment.
"""

import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.ports import ContainerCommand, ProgressNotice
from coding_study.application.sandbox import (
    ensure_engine,
    missing_images,
    pull_images,
    running_stack,
    sweep_leftovers,
)
from coding_study.domain.attempts import Attempt
from coding_study.domain.docker_engine import INSTALL_REACHES
from coding_study.domain.errors import SandboxError, UsageError
from coding_study.domain.layout import RUNS_DIRECTORY
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY, project_lock
from coding_study.domain.sandbox import (
    APP_MEMORY,
    CONTROL_PORT,
    MOCK_SERVICE,
    PYTHON_IMAGE,
    AppContainer,
    CommandOutcome,
    InstallPlan,
    MockServerInput,
    OneShot,
    SandboxPaths,
    StackIdentity,
    StackKind,
    StackPlan,
    StackStartError,
    install_stack_name,
    run_stack_name,
    workspace_digest,
)
from coding_study.domain.service_project import (
    INSTALLED_DIRECTORIES,
    NeedRow,
    ServiceProject,
    service_needs,
    service_of,
)
from coding_study.domain.workspace_projects import project_folder

INSTALL_RECORD_SUFFIX = ".install.json"
RECORD_LOCK_KEY = "lock_sha256"
RUN_ID_BYTES = 4


@dataclass(frozen=True, slots=True)
class ServiceStartPreview:
    """What `cstudy start` shows before anything downloads; the engine is running by then."""

    needs: tuple[NeedRow, ...]
    missing_images: tuple[str, ...]
    installs: bool
    """The dependencies are not installed for the lock file as it stands."""

    @property
    def downloads(self) -> bool:
        return bool(self.missing_images) or self.installs


def preview_service_start(
    environment: Environment, problem: Problem, notify: ProgressNotice
) -> ServiceStartPreview:
    """Starts a stopped engine and sweeps this workspace's leftovers, and writes nothing else.
    Raises SandboxError, with the state's message, when the engine cannot be used."""
    engine = environment.sandbox
    ensure_engine(engine, notify)
    sweep_leftovers(engine, _workspace(environment), notify)
    service = _service(problem.meta)
    return ServiceStartPreview(
        needs=service_needs(problem.meta, service, engine.state(), engine.platform()),
        missing_images=missing_images(engine, _images(service)),
        installs=needs_install(environment, problem),
    )


def finish_service_start(
    environment: Environment, problem: Problem, notify: ProgressNotice
) -> None:
    """Pulls what is missing and installs what the lock file names; nothing else starts. Raises
    SandboxError when either fails, and keeps the attempt: `cstudy start` retries."""
    pull_images(environment.sandbox, _images(_service(problem.meta)), notify)
    if needs_install(environment, problem):
        install_dependencies(environment, problem, notify)


def service_needs_of(environment: Environment, slug: str) -> tuple[NeedRow, ...] | None:
    """What `cstudy show` lists above the statement, with each requirement's state; it reads the
    state and starts nothing. None for any other problem, which asks the engine nothing."""
    meta = environment.problems.load(slug).meta
    service = service_of(meta)
    if service is None:
        return None
    engine = environment.sandbox
    return service_needs(meta, service, engine.state(), engine.platform())


def needs_install(environment: Environment, problem: Problem) -> bool:
    """Whether the lock file differs from what the last install recorded, or what it installed is
    gone. A problem with no install needs none."""
    service = _service(problem.meta)
    lock = service.requires.lock
    if service.commands.install is None or lock is None:
        return False
    workspace = environment.workspace
    folder = project_folder(problem.meta.slug)
    installed = INSTALLED_DIRECTORIES.get(lock)
    if installed is not None and not workspace.exists(f"{folder}/{installed}"):
        return True
    return _recorded_lock(environment, problem.meta.slug) != workspace.content_hash(
        f"{folder}/{lock}"
    )


def install_dependencies(
    environment: Environment, problem: Problem, notify: ProgressNotice
) -> None:
    """`commands.install`, in a stack of its own, under the project's lock. It says what an install
    can reach, and the record holds the lock file's digest only after it succeeded.

    Raises SandboxError when it fails or changes its lock file, and keeps the attempt.
    """
    slug = problem.meta.slug
    service = _service(problem.meta)
    command, lock = service.commands.install, service.requires.lock
    if command is None or lock is None:
        return
    workspace = environment.workspace
    lock_path = f"{project_folder(slug)}/{lock}"
    if not workspace.exists(lock_path):
        raise SandboxError(f"{lock} is missing. Run: cstudy start --restore {lock}")
    with workspace.locked(project_lock(slug)):
        before = workspace.content_hash(lock_path)
        notify(f"installing dependencies: {' '.join(command)}")
        notify(INSTALL_REACHES)
        outcome = _run_install(environment, problem, service, notify)
        if outcome.exit_code != 0:
            raise SandboxError(_install_failure(command, outcome, slug, service))
        if workspace.content_hash(lock_path) != before:
            raise SandboxError(
                f"the install changed its lock file {lock}: it must use the lock exactly. "
                f"Run: cstudy start --restore {lock}"
            )
        workspace.write_text(_record_path(slug), json.dumps({RECORD_LOCK_KEY: before}) + "\n")


def _run_install(
    environment: Environment, problem: Problem, service: ServiceProject, notify: ProgressNotice
) -> CommandOutcome:
    engine = environment.sandbox
    plan = _install_plan(environment, problem, service)
    with engine.guard(plan.identity):
        try:
            return engine.install(plan, service.timeouts.install, notify)
        finally:
            problem_stopping = engine.stop_install(plan)
            if problem_stopping is not None:
                notify(problem_stopping)


def _install_failure(
    command: tuple[str, ...], outcome: CommandOutcome, slug: str, service: ServiceProject
) -> str:
    if outcome.timed_out:
        reason = f"did not finish within {service.timeouts.install} s"
    else:
        reason = f"exited with {outcome.exit_code}"
    return (
        f"the install failed: {' '.join(command)} {reason}\n{outcome.output.strip()}\n"
        f"If you are offline, connect to the network. Retry: cstudy start {slug}"
    )


def _record_path(slug: str) -> str:
    return f"{MANIFESTS_DIRECTORY}/{slug}{INSTALL_RECORD_SUFFIX}"


def _recorded_lock(environment: Environment, slug: str) -> str | None:
    path = _record_path(slug)
    if not environment.workspace.exists(path):
        return None
    try:
        document: object = json.loads(environment.workspace.read_text(path))
    except json.JSONDecodeError:
        return None
    if isinstance(document, dict):
        recorded = document.get(RECORD_LOCK_KEY)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        return recorded if isinstance(recorded, str) else None
    return None


def _workspace(environment: Environment) -> str:
    return workspace_digest(str(environment.root.resolve()))


def _service(meta: ProblemMeta) -> ServiceProject:
    service = service_of(meta)
    if service is None:
        raise ValueError(f"{meta.slug} is not a service project")
    return service


def _images(service: ServiceProject) -> tuple[str, ...]:
    """Backing services' images come with project.services, in P10."""
    return (service.image, PYTHON_IMAGE)


def _paths(environment: Environment, slug: str, stack: str) -> SandboxPaths:
    workspace = environment.workspace
    return SandboxPaths(
        project=str(workspace.absolute(project_folder(slug)).resolve()),
        run=str(workspace.absolute(f"{RUNS_DIRECTORY}/{stack}").resolve()),
    )


def _install_plan(
    environment: Environment, problem: Problem, service: ServiceProject
) -> InstallPlan:
    engine = environment.sandbox
    slug = problem.meta.slug
    digest = _workspace(environment)
    name = install_stack_name(slug, digest)
    command = service.commands.install
    assert command is not None
    return InstallPlan(
        identity=StackIdentity(name, StackKind.INSTALL, digest, slug, engine.owner_pid()),
        user=engine.host_user(),
        paths=_paths(environment, slug, name),
        image=service.image,
        command=command,
        environment=service.install_env,
    )


def test_stack_plan(environment: Environment, problem: Problem) -> StackPlan:
    """The stack of one `cstudy test`: a fresh name, and data that goes with it."""
    engine = environment.sandbox
    slug = problem.meta.slug
    service = _service(problem.meta)
    owner = engine.owner_pid()
    name = run_stack_name(StackKind.TEST, owner, secrets.token_hex(RUN_ID_BYTES))
    identity = StackIdentity(name, StackKind.TEST, _workspace(environment), slug, owner)
    commands = service.commands
    return StackPlan(
        identity=identity,
        user=engine.host_user(),
        paths=_paths(environment, slug, name),
        app=AppContainer(
            image=service.image,
            command=commands.run,
            port=service.app.port,
            environment=service.env,
            mem_limit=service.app.mem_limit or APP_MEMORY,
            health=service.app.health,
            port_env=service.app.port_env,
        ),
        mocks=_mock_server(service),
        bootstrap=OneShot(commands.bootstrap) if commands.bootstrap is not None else None,
    )


def _mock_server(service: ServiceProject) -> MockServerInput | None:
    """The seam for the mock server (P5): its config rendered to JSON, its token, and the command
    that starts it. Until then a problem that declares one cannot run."""
    if service.mocks:
        raise SandboxError("this problem's mock servers need the mock server, which is not built")
    if service.services is not None:
        raise SandboxError("this problem's backing services arrive with project.services (P10)")
    return None


def _test_environment(plan: StackPlan) -> dict[str, str]:
    """Only a test stack hands its control interface to `commands.test`; it holds visible scenarios
    only, and a graded stack never does this."""
    if plan.mocks is None:
        return {}
    return {
        "CSTUDY_MOCK_CONTROL_URL": f"http://{MOCK_SERVICE}:{CONTROL_PORT}",
        "CSTUDY_MOCK_CONTROL_TOKEN": plan.mocks.control_token,
    }


@dataclass(frozen=True, slots=True)
class ServiceTestRequest:
    slug: str | None = None
    language: Language | None = None
    on_output: Callable[[str], None] | None = None
    """Hears each line `commands.test` prints."""


@dataclass(frozen=True, slots=True)
class ServiceTestResult:
    meta: ProblemMeta
    attempt: Attempt
    outcome: CommandOutcome | None = None
    """None when the stack did not become ready."""
    failure: StackStartError | None = None
    """Your code kept the stack from becoming ready; another reason raises."""
    startup_seconds: float = 0.0
    """The first clock: up to the moment the stack was ready. No limit or result counts it."""
    test_seconds: float = 0.0
    """The second clock: `commands.test`, from that moment."""
    limit_s: int = 0

    @property
    def passed(self) -> bool:
        return self.outcome is not None and self.outcome.exit_code == 0

    @property
    def total_seconds(self) -> float:
        return self.startup_seconds + self.test_seconds


def service_attempt(
    environment: Environment, slug: str | None, language: Language | None
) -> Problem | None:
    """The problem of the attempt a command works on, when it is a service project."""
    attempt = find_attempt(environment.progress, slug, language)
    if attempt.language is None:
        return None
    problem = environment.problems.load(attempt.slug)
    return problem if service_of(problem.meta) is not None else None


def run_service_tests(
    environment: Environment, request: ServiceTestRequest, notify: ProgressNotice
) -> ServiceTestResult:
    """`cstudy test` on a service project: a fresh stack, `commands.test` in its running app, and
    the stack gone again. It stores nothing and opens nothing; the visible HTTP cases come with
    the grader (P6), which gets its stack the same way.

    Raises SandboxError or StackStartError when the sandbox failed and your code is not to blame:
    the exit code 4 of `Failure reporting`.
    """
    attempt = find_attempt(environment.progress, request.slug, request.language)
    problem = environment.problems.load(attempt.slug)
    if problem.meta.kind is not ProblemKind.PROJECT:
        raise UsageError(f"{problem.meta.slug} is not a service project")
    service = _service(problem.meta)
    _prepare(environment, problem, notify)
    plan = test_stack_plan(environment, problem)
    try:
        return _tests_in(environment, attempt, problem, plan, request, notify)
    except StackStartError as failure:
        if not failure.failure.is_your_code:
            raise
        return ServiceTestResult(
            problem.meta, attempt, failure=failure, limit_s=service.timeouts.test
        )


def _prepare(environment: Environment, problem: Problem, notify: ProgressNotice) -> None:
    engine = environment.sandbox
    ensure_engine(engine, notify)
    sweep_leftovers(engine, _workspace(environment), notify)
    pull_images(engine, _images(_service(problem.meta)), notify)
    if needs_install(environment, problem):
        install_dependencies(environment, problem, notify)


def _tests_in(
    environment: Environment,
    attempt: Attempt,
    problem: Problem,
    plan: StackPlan,
    request: ServiceTestRequest,
    notify: ProgressNotice,
) -> ServiceTestResult:
    service = _service(problem.meta)
    limit = service.timeouts.test
    engine = environment.sandbox
    clock = environment.clock
    with running_stack(engine, plan, service.startup_budget, notify) as ready:
        run_began = clock.monotonic()
        outcome = engine.exec_app(
            plan,
            ContainerCommand(
                service.commands.test, _test_environment(plan), limit, request.on_output
            ),
        )
        test_seconds = clock.monotonic() - run_began
    return ServiceTestResult(
        problem.meta,
        attempt,
        outcome=outcome,
        startup_seconds=ready.startup_seconds,
        test_seconds=test_seconds,
        limit_s=limit,
    )
