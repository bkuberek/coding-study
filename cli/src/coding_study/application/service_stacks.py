"""What each stack of a service project holds (docs/specs/service-projects.md#lifecycle-commands):
a dev stack and a test stack see visible scenarios only, a graded stack sees them all, and only a
graded stack runs `grade_setup`.
"""

import secrets
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
    GradeSetup,
    InstallPlan,
    MockServerInput,
    OneShot,
    SandboxPaths,
    StackIdentity,
    StackKind,
    StackPlan,
    dev_stack_name,
    install_stack_name,
    run_stack_name,
    workspace_digest,
)
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


def images(service: ServiceProject) -> tuple[str, ...]:
    """Backing services' images come with project.services, in P10."""
    return (service.image, PYTHON_IMAGE)


def dev_stack_plan(environment: Environment, problem: Problem) -> StackPlan:
    """The one dev stack of a project: a stable name, and data that outlives it."""
    engine = environment.sandbox
    slug = problem.meta.slug
    digest = workspace_id(environment)
    name = dev_stack_name(slug, digest)
    identity = StackIdentity(name, StackKind.DEV, digest, slug, engine.owner_pid())
    return _plan(environment, problem, identity, project_folder(slug))


def test_stack_plan(
    environment: Environment, problem: Problem, folder: str | None = None
) -> StackPlan:
    """The stack of one `cstudy test`: a fresh name, and data that goes with it."""
    identity = _run_identity(environment, problem, StackKind.TEST)
    plan = _plan(environment, problem, identity, folder or project_folder(problem.meta.slug))
    return _with_reset_prepared(plan, service_project(problem))


def graded_stack_plan(
    environment: Environment, problem: Problem, level: int, folder: str | None = None
) -> StackPlan:
    """The stack of one graded run, holding every scenario and, for this stack alone,
    `grade_setup`. Its control token is given to no command."""
    identity = _run_identity(environment, problem, StackKind.GRADED)
    target = folder or project_folder(problem.meta.slug)
    plan = _plan(environment, problem, identity, target, ScenarioReach.EVERY)
    graded = replace(plan, grade_setup=_grade_setup(environment, problem, level))
    return _with_reset_prepared(graded, service_project(problem))


def install_plan(environment: Environment, problem: Problem, folder: str) -> InstallPlan:
    """`commands.install`, in a stack of its own whose cache outlives it. Raises ValueError for a
    problem with no install."""
    engine = environment.sandbox
    service = service_project(problem)
    slug = problem.meta.slug
    digest = workspace_id(environment)
    name = install_stack_name(slug, digest)
    command = service.commands.install
    if command is None:
        raise ValueError(f"{slug} has no install")
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
    workspace = environment.workspace
    return SandboxPaths(
        project=str(workspace.absolute(folder).resolve()),
        run=str(workspace.absolute(f"{RUNS_DIRECTORY}/{stack}").resolve()),
    )


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
        ),
        mocks=_mock_server(problem, service, reach),
        bootstrap=OneShot(commands.bootstrap) if commands.bootstrap is not None else None,
    )


def _with_reset_prepared(plan: StackPlan, service: ServiceProject) -> StackPlan:
    """`commands.reset` runs once with `prepare` in a stack whose cases may ask for a fresh start."""
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
    """The configs rendered to one document for this stack alone, with a token of its own. A
    problem's backing services come with project.services (P10)."""
    if service.services is not None:
        raise SandboxError("this problem's backing services arrive with project.services (P10)")
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
