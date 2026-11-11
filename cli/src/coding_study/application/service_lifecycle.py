"""The lifecycle commands of a service project (docs/specs/service-projects.md#lifecycle-commands):
what `cstudy start` adds after it copies the starter, the install and its record, and `cstudy test`.

Two clocks run here and stay apart (docs/specs/service-projects.md#two-clocks). Everything up to
the moment a stack is ready spends the startup budget, and a failure there says so and changes no
result. The limit on `commands.test`, and the run time this reports, start at that moment.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Protocol, cast

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.graded_stack import RunningStack, SandboxGradedStack
from coding_study.application.http_grading import HttpCaseListener, HttpGradingRun, run_http_grading
from coding_study.application.ports import ContainerCommand, ProgressNotice
from coding_study.application.preferences import read_preferences
from coding_study.application.sandbox import (
    ensure_engine,
    missing_images,
    pull_images,
    reported_stack,
    staged,
    sweep_leftovers,
)
from coding_study.application.service_stacks import (
    images,
    install_plan,
    practice_stack_plan,
    service_project,
    workspace_id,
)
from coding_study.domain.attempts import Attempt
from coding_study.domain.code_intelligence import CacheInstall, cache_install_of
from coding_study.domain.docker_engine import INSTALL_REACHES, EngineStatus, engine_problem
from coding_study.domain.errors import SandboxError, UsageError
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY, project_lock
from coding_study.domain.sandbox import (
    CONTROL_PORT,
    MOCK_SERVICE,
    CommandOutcome,
    InstallPlan,
    StackPlan,
    StackStartError,
)
from coding_study.domain.service_project import (
    INSTALLED_DIRECTORIES,
    NeedRow,
    ServiceProject,
    service_needs,
    service_of,
)
from coding_study.domain.stack_progress import StackStage
from coding_study.domain.workspace_projects import project_folder

INSTALL_RECORD_SUFFIX = ".install.json"
RECORD_LOCK_KEY = "lock_sha256"
RECORD_SERVERS_KEY = "servers"
"""The language servers the install built into the install cache, by name, with their version."""


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
    sweep_leftovers(engine, workspace_id(environment), notify)
    service = service_project(problem)
    return ServiceStartPreview(
        needs=service_needs(problem.meta, service, engine.state(), engine.platform()),
        missing_images=missing_images(engine, images(problem)),
        installs=needs_install(environment, problem),
    )


def finish_service_start(
    environment: Environment, problem: Problem, notify: ProgressNotice
) -> None:
    """Pulls what is missing and installs what the lock file names; nothing else starts. Raises
    SandboxError when either fails, and keeps the attempt: `cstudy start` retries."""
    pull_images(environment.sandbox, images(problem), notify)
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


def require_service_engine(environment: Environment, problem: Problem) -> None:
    """The Web UI's Start: refuses, with the state's message, an engine this machine cannot run the
    project on, before anything is written. It asks and starts nothing: a stopped engine is no
    problem, since the first run starts it, and nothing downloads until then."""
    if service_of(problem.meta) is None:
        return
    engine = environment.sandbox
    state = engine.state()
    if state.status is EngineStatus.STOPPED:
        return
    problem_text = engine_problem(state, engine.platform())
    if problem_text is not None:
        raise SandboxError(problem_text)


def needs_install(environment: Environment, problem: Problem) -> bool:
    """Whether the lock file differs from what the last install recorded, or what it installed is
    gone: a folder of the project's, or the install cache of an app that keeps its dependencies
    there. A problem with no install needs none. Asks the engine only about such a cache, once the
    lock is as recorded."""
    service = service_project(problem)
    lock = service.requires.lock
    if service.commands.install is None or lock is None:
        return False
    workspace = environment.workspace
    folder = project_folder(problem.meta.slug)
    installed = INSTALLED_DIRECTORIES.get(lock)
    if installed is not None and not workspace.exists(f"{folder}/{installed}"):
        return True
    recorded = _recorded_lock(environment, problem.meta.slug)
    if recorded != workspace.content_hash(f"{folder}/{lock}"):
        return True
    if not service.app.install_cache:
        return False
    if _misses_its_language_server(environment, problem):
        return True
    plan = install_plan(environment, problem, folder)
    return not environment.sandbox.install_cache_present(plan)


def install_dependencies(
    environment: Environment, problem: Problem, notify: ProgressNotice
) -> None:
    """`commands.install` in the project folder, then the language server its sidecar runs where the
    install builds it, and the record of the lock file it installed and of that server, only after
    each succeeded. Raises as `install_in_folder`."""
    slug = problem.meta.slug
    folder = project_folder(slug)
    digest = install_in_folder(environment, problem, folder, notify)
    if digest is None:
        return
    record: dict[str, object] = {RECORD_LOCK_KEY: digest}
    server = _install_language_server(environment, problem, folder, notify)
    if server is not None:
        record[RECORD_SERVERS_KEY] = {server.name: server.version}
    environment.workspace.write_text(_record_path(slug), json.dumps(record) + "\n")


def server_in_install_cache(environment: Environment, slug: str, name: str) -> str | None:
    """The version of the server called `name` that the last install of `slug` built into its
    install cache; None if it built none (docs/specs/service-projects.md#language-servers)."""
    servers = _record(environment, slug).get(RECORD_SERVERS_KEY)
    found = servers.get(name) if isinstance(servers, dict) else None  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
    return found if isinstance(found, str) else None


def _wanted_server(environment: Environment, problem: Problem) -> CacheInstall | None:
    """The server the install builds into the install cache: only while `code_intelligence` is
    on, since a learner who never turns it on downloads nothing for it."""
    if not read_preferences(environment.preferences).code_intelligence:
        return None
    return cache_install_of(problem.meta)


def _misses_its_language_server(environment: Environment, problem: Problem) -> bool:
    wanted = _wanted_server(environment, problem)
    if wanted is None:
        return False
    built = server_in_install_cache(environment, problem.meta.slug, wanted.name)
    return built != wanted.version


def _install_language_server(
    environment: Environment, problem: Problem, folder: str, notify: ProgressNotice
) -> CacheInstall | None:
    """`go install` of gopls into the install cache, with the install's network, where the
    sidecar finds it. A failure is said and leaves the project as installed: code intelligence
    then says the server is missing, and the next install builds it again."""
    wanted = _wanted_server(environment, problem)
    if wanted is None:
        return None
    service = service_project(problem)
    plan = install_plan(environment, problem, folder)
    plan = replace(
        plan, command=wanted.command, environment={**plan.environment, **wanted.environment}
    )
    notify(f"installing {wanted.name} {wanted.version} for code intelligence")
    outcome = run_install_plan(environment, plan, service.timeouts.install, notify)
    if outcome.exit_code == 0:
        return wanted
    notify(
        f"{wanted.name} {wanted.version} was not installed, so code intelligence has none for "
        f"this project: exit {outcome.exit_code}"
    )
    return None


def install_in_folder(
    environment: Environment, problem: Problem, folder: str, notify: ProgressNotice
) -> str | None:
    """`commands.install`, in a stack of its own, under the project's lock. It says what an install
    can reach. Returns the lock file's digest; None for a problem with no install.

    Raises SandboxError when it fails or changes its lock file, and keeps the attempt.
    """
    slug = problem.meta.slug
    service = service_project(problem)
    command, lock = service.commands.install, service.requires.lock
    if command is None or lock is None:
        return None
    workspace = environment.workspace
    lock_path = f"{folder}/{lock}"
    if not workspace.exists(lock_path):
        raise SandboxError(f"{lock} is missing. Run: cstudy start --restore {lock}")
    with workspace.locked(project_lock(slug)):
        before = workspace.content_hash(lock_path)
        staged(notify, StackStage.INSTALLING)(f"installing dependencies: {' '.join(command)}")
        notify(INSTALL_REACHES)
        outcome = _run_install(environment, problem, folder, notify)
        if outcome.exit_code != 0:
            raise SandboxError(_install_failure(command, outcome, slug, service))
        if workspace.content_hash(lock_path) != before:
            raise SandboxError(
                f"the install changed its lock file {lock}: it must use the lock exactly. "
                f"Run: cstudy start --restore {lock}"
            )
        return before


def _run_install(
    environment: Environment, problem: Problem, folder: str, notify: ProgressNotice
) -> CommandOutcome:
    plan = install_plan(environment, problem, folder)
    return run_install_plan(environment, plan, service_project(problem).timeouts.install, notify)


def run_install_plan(
    environment: Environment,
    plan: InstallPlan,
    limit_s: float,
    on_output: Callable[[str], None] | None,
) -> CommandOutcome:
    """`plan`'s command, with its stack gone after it however it ends; a stack that does not come
    down is said, not raised."""
    engine = environment.sandbox
    with engine.guard(plan.identity):
        try:
            return engine.install(plan, limit_s, on_output)
        finally:
            problem_stopping = engine.stop_install(plan)
            if problem_stopping is not None and on_output is not None:
                on_output(problem_stopping)


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
    recorded = _record(environment, slug).get(RECORD_LOCK_KEY)
    return recorded if isinstance(recorded, str) else None


def _record(environment: Environment, slug: str) -> dict[str, object]:
    """What the last install recorded; empty without a record, or for one that is not JSON."""
    path = _record_path(slug)
    if not environment.workspace.exists(path):
        return {}
    try:
        document: object = json.loads(environment.workspace.read_text(path))
    except json.JSONDecodeError:
        return {}
    return cast(dict[str, object], document) if isinstance(document, dict) else {}


def environment_of_test_command(plan: StackPlan) -> dict[str, str]:
    """Only a test stack hands its control interface to `commands.test`; it holds visible scenarios
    only, and a graded stack never does this."""
    if plan.mocks is None:
        return {}
    return {
        "CSTUDY_MOCK_CONTROL_URL": f"http://{MOCK_SERVICE}:{CONTROL_PORT}",
        "CSTUDY_MOCK_CONTROL_TOKEN": plan.mocks.control_token,
    }


class TestCommandListener(Protocol):
    """Told when `commands.test` starts in the ready stack, and how it ended."""

    def test_started(self) -> None: ...

    def test_ended(self, outcome: CommandOutcome, seconds: float) -> None:
        """`seconds` on the second clock, from the moment the stack was ready."""
        ...


@dataclass(frozen=True, slots=True)
class ServiceTestRequest:
    slug: str | None = None
    language: Language | None = None
    on_output: Callable[[str], None] | None = None
    """Hears each line `commands.test` prints."""
    listener: HttpCaseListener | None = None
    """Hears each visible case as it starts and as it is judged."""
    on_test: TestCommandListener | None = None


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
    cases: Judgement = field(default_factory=lambda: Judgement(0))
    """The visible HTTP cases of the unlocked levels, as feedback; nothing keeps it."""
    cases_seconds: float = 0.0
    """The second clock: those cases."""
    case_levels: Mapping[str, int | None] = field(default_factory=dict[str, int | None])
    """Each case's level, by its id."""

    @property
    def command_passed(self) -> bool:
        return self.outcome is not None and self.outcome.exit_code == 0

    @property
    def passed(self) -> bool:
        return self.command_passed and self.cases.passed

    @property
    def total_seconds(self) -> float:
        return self.startup_seconds + self.test_seconds + self.cases_seconds


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
    """`cstudy test` on a service project: a fresh stack, `commands.test` in its running app, the
    visible HTTP cases of the unlocked levels as feedback, and the stack gone again. It stores
    nothing and opens nothing.

    Raises SandboxError or StackStartError when the sandbox failed and your code is not to blame:
    the exit code 4 of `Failure reporting`.
    """
    attempt = find_attempt(environment.progress, request.slug, request.language)
    problem = environment.problems.load(attempt.slug)
    if problem.meta.kind is not ProblemKind.PROJECT:
        raise UsageError(f"{problem.meta.slug} is not a service project")
    service = service_project(problem)
    prepare_service_run(environment, problem, notify)
    plan = practice_stack_plan(environment, problem)
    try:
        return _tests_in(environment, attempt, problem, plan, request, notify)
    except StackStartError as failure:
        if not failure.failure.is_your_code:
            raise
        return ServiceTestResult(
            problem.meta,
            attempt,
            failure=failure,
            limit_s=service.timeouts.test,
            case_levels=_case_levels(problem),
        )


def prepare_service_run(environment: Environment, problem: Problem, notify: ProgressNotice) -> None:
    """What a stack needs before it starts: the engine and its images, and the dependencies
    installed for the lock file as it stands."""
    prepare_engine(environment, problem, notify)
    if needs_install(environment, problem):
        install_dependencies(environment, problem, notify)


def prepare_engine(environment: Environment, problem: Problem, notify: ProgressNotice) -> None:
    """The engine up, no leftovers of this workspace, and the problem's images here."""
    engine = environment.sandbox
    ensure_engine(engine, notify)
    sweep_leftovers(engine, workspace_id(environment), notify)
    pull_images(engine, images(problem), notify)


def _tests_in(
    environment: Environment,
    attempt: Attempt,
    problem: Problem,
    plan: StackPlan,
    request: ServiceTestRequest,
    notify: ProgressNotice,
) -> ServiceTestResult:
    service = service_project(problem)
    limit = service.timeouts.test
    engine = environment.sandbox
    clock = environment.clock
    on_test = request.on_test
    with reported_stack(engine, plan, service.startup_budget, notify) as ready:
        run_began = clock.monotonic()
        if on_test is not None:
            on_test.test_started()
        outcome = engine.exec_app(
            plan,
            ContainerCommand(
                service.commands.test, environment_of_test_command(plan), limit, request.on_output
            ),
        )
        test_seconds = clock.monotonic() - run_began
        if on_test is not None:
            on_test.test_ended(outcome, test_seconds)
        cases_began = clock.monotonic()
        cases = _visible_cases(
            environment,
            (attempt, problem),
            SandboxGradedStack(engine, RunningStack(plan, ready), service),
            request.listener,
        )
        cases_seconds = clock.monotonic() - cases_began
    return ServiceTestResult(
        problem.meta,
        attempt,
        outcome=outcome,
        startup_seconds=ready.startup_seconds,
        test_seconds=test_seconds,
        limit_s=limit,
        cases=cases,
        cases_seconds=cases_seconds,
        case_levels=_case_levels(problem),
    )


def _case_levels(problem: Problem) -> dict[str, int | None]:
    return {case.id: case.level for case in problem.cases}


def _visible_cases(
    environment: Environment,
    subject: tuple[Attempt, Problem],
    stack: SandboxGradedStack,
    listener: HttpCaseListener | None,
) -> Judgement:
    attempt, problem = subject
    visible = tuple(case for case in problem.cases if case.visible)
    run = HttpGradingRun(
        replace(problem, cases=visible),
        attempt.level_unlocked or FIRST_LEVEL,
        environment.config,
        listener,
    )
    return run_http_grading(run, stack, environment.stack_clients)
