"""What each stack of a service project holds (docs/specs/service-projects.md#lifecycle-commands):
a dev stack and a test stack see visible scenarios only, a graded stack sees them all, and only a
graded stack runs `grade_setup`. Every stack holds the problem's backing services, and only a test
or a graded stack publishes what the grader may reach.
"""

import posixpath
import secrets
from collections.abc import Mapping
from dataclasses import replace

from coding_study.application.environment import Environment
from coding_study.domain.errors import SandboxError
from coding_study.domain.layout import RUNS_DIRECTORY
from coding_study.domain.mock_configs import ScenarioReach, rendered_mock_config
from coding_study.domain.problem import Problem
from coding_study.domain.project import NO_PROJECT_FILES
from coding_study.domain.sandbox import (
    APP_MEMORY,
    PROBLEM_DIRECTORY,
    PYTHON_IMAGE,
    AppContainer,
    BackingServices,
    GradeSetup,
    InstallPlan,
    MockServerInput,
    OneShot,
    SandboxPaths,
    StackIdentity,
    StackKind,
    StackPlan,
    backing_images,
    cache_volume_of,
    dev_stack_name,
    install_stack_name,
    run_stack_name,
    workspace_digest,
)
from coding_study.domain.service_content_checks import compose_issues
from coding_study.domain.service_project import (
    PROBLEM_PLACEHOLDER,
    ServiceProject,
    service_of,
)
from coding_study.domain.workspace_projects import project_folder

RUN_ID_BYTES = 4
CONTROL_TOKEN_BYTES = 24
GRADING_DIRECTORY = "grading"


def service_project(problem: Problem) -> ServiceProject:
    service = service_of(problem.meta)
    if service is None:
        raise ValueError(f"{problem.meta.slug} is not a service project")
    return service


def workspace_id(environment: Environment) -> str:
    return workspace_digest(str(environment.root.resolve()))


def images(problem: Problem) -> tuple[str, ...]:
    """The toolchain, the image of `cstudy`'s own helpers, and each backing service's."""
    service = service_project(problem)
    return (service.image, PYTHON_IMAGE, *backing_images(_compose_document(problem)))


def dev_stack_plan(environment: Environment, problem: Problem) -> StackPlan:
    """The one dev stack of a project: a stable name, and data that outlives it."""
    engine = environment.sandbox
    slug = problem.meta.slug
    digest = workspace_id(environment)
    name = dev_stack_name(slug, digest)
    identity = StackIdentity(name, StackKind.DEV, digest, slug, engine.owner_pid())
    return _plan(environment, problem, identity, project_folder(slug))


def practice_stack_plan(environment: Environment, problem: Problem, folder: str = "") -> StackPlan:
    """The stack of one `cstudy test`: a fresh name, and data that goes with it."""
    identity = _run_identity(environment, problem, StackKind.TEST)
    plan = _plan(environment, problem, identity, folder or project_folder(problem.meta.slug))
    return _with_reset_prepared(plan, service_project(problem))


def graded_stack_plan(
    environment: Environment, problem: Problem, level: int, folder: str = ""
) -> StackPlan:
    """The stack of one graded run, holding every scenario and, for this stack alone,
    `grade_setup`. Its control token is given to no command."""
    identity = _run_identity(environment, problem, StackKind.GRADED)
    target = folder or project_folder(problem.meta.slug)
    plan = _plan(environment, problem, identity, target, ScenarioReach.EVERY)
    graded = replace(plan, grade_setup=_grade_setup(environment, problem, level))
    return _with_reset_prepared(graded, service_project(problem))


def from_empty_stack_plan(
    environment: Environment, problem: Problem, graded: StackPlan
) -> StackPlan:
    """What a graded run with `grade_setup` checks first: the graded stack's services and
    `bootstrap` alone, on empty data, with the app idle and no `grade_setup`, under a fresh name
    whose data goes with it (docs/specs/service-projects.md#graded-run)."""
    identity = _run_identity(environment, problem, StackKind.GRADED)
    return replace(
        graded,
        identity=identity,
        paths=replace(graded.paths, run=_run_path(environment, identity.name)),
        app=replace(graded.app, command=None),
        grade_setup=None,
        reset_prepare=None,
        reach=(),
    )


def install_plan(environment: Environment, problem: Problem, folder: str) -> InstallPlan:
    """`commands.install`, in a stack of its own whose cache outlives it. Raises ValueError for a
    problem with no install."""
    command = service_project(problem).commands.install
    if command is None:
        raise ValueError(f"{problem.meta.slug} has no install")
    return _install_stack(environment, problem, folder, command)


def network_command_plan(
    environment: Environment, problem: Problem, command: tuple[str, ...]
) -> InstallPlan:
    """`cstudy dev --exec --network`: `command` where the install runs, in the project folder,
    with the internet, the install's cache and nothing else of the stack."""
    return _install_stack(environment, problem, project_folder(problem.meta.slug), command)


def _install_stack(
    environment: Environment, problem: Problem, folder: str, command: tuple[str, ...]
) -> InstallPlan:
    engine = environment.sandbox
    service = service_project(problem)
    slug = problem.meta.slug
    digest = workspace_id(environment)
    name = install_stack_name(slug, digest)
    return InstallPlan(
        identity=StackIdentity(name, StackKind.INSTALL, digest, slug, engine.owner_pid()),
        user=engine.host_user(),
        paths=_paths(environment, folder, name),
        image=service.image,
        command=command,
        environment=service.install_env,
    )


def _run_identity(environment: Environment, problem: Problem, kind: StackKind) -> StackIdentity:
    owner = environment.sandbox.owner_pid()
    name = run_stack_name(kind, owner, secrets.token_hex(RUN_ID_BYTES))
    return StackIdentity(name, kind, workspace_id(environment), problem.meta.slug, owner)


def _paths(environment: Environment, folder: str, stack: str) -> SandboxPaths:
    project = str(environment.workspace.absolute(folder).resolve())
    return SandboxPaths(project=project, run=_run_path(environment, stack))


def _run_path(environment: Environment, stack: str) -> str:
    return str(environment.workspace.absolute(f"{RUNS_DIRECTORY}/{stack}").resolve())


def _plan(
    environment: Environment,
    problem: Problem,
    identity: StackIdentity,
    folder: str,
    reach: ScenarioReach = ScenarioReach.VISIBLE,
) -> StackPlan:
    service = service_project(problem)
    commands = service.commands
    return StackPlan(
        identity=identity,
        user=environment.sandbox.host_user(),
        paths=_paths(environment, folder, identity.name),
        app=AppContainer(
            image=service.image,
            command=commands.run,
            port=service.app.port,
            environment=service.env,
            mem_limit=service.app.mem_limit or APP_MEMORY,
            health=service.app.health,
            port_env=service.app.port_env,
            install_cache=_install_cache(identity, service),
        ),
        mocks=_mock_server(problem, service, reach),
        bootstrap=OneShot(commands.bootstrap) if commands.bootstrap is not None else None,
        backing=_backing(environment, problem, service),
        reach=service.grader_reach if identity.kind.serves_the_grader else (),
    )


def _install_cache(identity: StackIdentity, service: ServiceProject) -> str | None:
    """The project's install cache, for an app that keeps its dependencies there."""
    if not service.app.install_cache:
        return None
    return cache_volume_of(install_stack_name(identity.slug, identity.workspace))


def _backing(
    environment: Environment, problem: Problem, service: ServiceProject
) -> BackingServices | None:
    """The problem's compose file, held to S21 first: a problem among your own may never have been
    verified, and nothing that file asks for may leave the sandbox."""
    if service.services is None:
        return None
    document = _compose_document(problem)
    issues = [
        f"{where}: {message}" if where else message
        for where, message in compose_issues(service, document)
    ]
    if issues:
        raise SandboxError(f"{service.services} cannot run: {'; '.join(issues)}")
    folder = environment.files.path(problem.meta.slug, posixpath.dirname(service.services))
    return BackingServices(document, str(folder))


def _compose_document(problem: Problem) -> Mapping[str, object]:
    return (problem.project_files or NO_PROJECT_FILES).backing_services or {}


def _with_reset_prepared(plan: StackPlan, service: ServiceProject) -> StackPlan:
    """`commands.reset` runs once with `prepare` in a stack whose cases may ask for a fresh run."""
    reset = service.commands.reset
    return plan if reset is None else replace(plan, reset_prepare=OneShot(reset))


def _grade_setup(environment: Environment, problem: Problem, level: int) -> GradeSetup | None:
    command = service_project(problem).commands.grade_setup
    if command is None:
        return None
    return GradeSetup(
        command=tuple(word.replace(PROBLEM_PLACEHOLDER, PROBLEM_DIRECTORY) for word in command),
        grading_directory=str(environment.files.path(problem.meta.slug, GRADING_DIRECTORY)),
        graded_level=level,
    )


def _mock_server(
    problem: Problem, service: ServiceProject, reach: ScenarioReach
) -> MockServerInput | None:
    """The configs rendered to one document for this stack alone, with a token of its own."""
    if not service.mocks:
        return None
    files = (problem.project_files or NO_PROJECT_FILES).mocks
    token = secrets.token_urlsafe(CONTROL_TOKEN_BYTES)
    declared = {mock.name: files[mock.name] for mock in service.mocks}
    return MockServerInput(
        aliases=tuple(declared),
        control_token=token,
        rendered_config=rendered_mock_config(declared, token, reach),
    )
