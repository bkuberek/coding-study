"""`cstudy dev`: the dev stack of a service project, in the foreground, until you stop it
(docs/specs/service-projects.md#how-you-reach-them).

It holds visible scenarios only and keeps its data. One runs per project, because its compose
project has one name: a second would adopt the first's containers, and stopping either would stop
both.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.graded_stack import RunningStack, SandboxGradedStack
from coding_study.application.ports import ProgressNotice
from coding_study.application.sandbox import running_stack
from coding_study.application.service_lifecycle import prepare_service_run
from coding_study.application.service_stacks import dev_stack_plan
from coding_study.domain.errors import LockBusyError, RunnerStartError, UsageError
from coding_study.domain.mock_configs import visible_scenario_names
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project import NO_PROJECT_FILES
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY
from coding_study.domain.sandbox import CommandOutcome, StackPlan
from coding_study.domain.service_project import service_of

DEV_LOCK_SUFFIX = ".dev.lock"
LOGS_ENDED_GRACE_MS = 2_000
"""How long to wait for an app's exit to show once its log has ended."""
NO_WAIT_S = 0.0


@dataclass(frozen=True, slots=True)
class DevRequest:
    slug: str | None = None
    language: Language | None = None
    scenarios: Mapping[str, str] = field(default_factory=dict[str, str])
    """`--scenario`: the visible scenario each named mock server starts with."""


@dataclass(frozen=True, slots=True)
class DevStack:
    """What there is to reach, once the stack is ready."""

    app_url: str
    mocks: tuple[str, ...]
    scenarios: Mapping[str, str]
    startup_seconds: float


class DevListener(Protocol):
    def stack_ready(self, stack: DevStack) -> None: ...

    def app_line(self, line: str) -> None: ...


def run_dev_stack(
    environment: Environment,
    request: DevRequest,
    listener: DevListener,
    notify: ProgressNotice,
) -> CommandOutcome:
    """Runs until your app ends, which it returns, or until Ctrl-C raises through it; the stack is
    gone either way and its data stays.

    Raises UsageError without an attempt, for another kind of problem, for a scenario this stack
    does not hold and while another `cstudy dev` holds the project; StackStartError and SandboxError
    as a stack's start does.
    """
    attempt = find_attempt(environment.progress, request.slug, request.language)
    problem = environment.problems.load(attempt.slug)
    if service_of(problem.meta) is None:
        raise UsageError(f"cstudy dev is for service projects; {problem.meta.slug} is not one")
    _require_visible(problem, request.scenarios)
    plan = dev_stack_plan(environment, problem)
    try:
        with environment.workspace.locked_with_deadline(_dev_lock(problem), NO_WAIT_S):
            prepare_service_run(environment, problem, notify)
            return _in_stack(environment, (problem, plan), request, listener, notify)
    except LockBusyError:
        raise UsageError(_held_by(environment, problem, plan)) from None


def _dev_lock(problem: Problem) -> str:
    return f"{MANIFESTS_DIRECTORY}/{problem.meta.slug}{DEV_LOCK_SUFFIX}"


def _require_visible(problem: Problem, scenarios: Mapping[str, str]) -> None:
    mocks = (problem.project_files or NO_PROJECT_FILES).mocks
    for mock, scenario in scenarios.items():
        if mock not in mocks:
            raise UsageError(f"no mock server named {mock}; this problem has: {_names(mocks)}")
        visible = visible_scenario_names(mocks[mock])
        if scenario not in visible:
            raise UsageError(
                f"{mock} has no visible scenario {scenario}; it has: {_names(visible)}"
            )


def _names(names: Iterable[str]) -> str:
    return ", ".join(sorted(names)) or "none"


def _in_stack(
    environment: Environment,
    subject: tuple[Problem, StackPlan],
    request: DevRequest,
    listener: DevListener,
    notify: ProgressNotice,
) -> CommandOutcome:
    problem, plan = subject
    service = service_of(problem.meta)
    assert service is not None
    engine = environment.sandbox
    with running_stack(engine, plan, service.startup_budget, notify) as ready:
        stack = SandboxGradedStack(engine, RunningStack(plan, ready), service)
        endpoints = stack.endpoints
        if request.scenarios:
            _set_scenarios(environment, stack, request.scenarios)
        listener.stack_ready(
            DevStack(endpoints.app_url, endpoints.mocks, request.scenarios, ready.startup_seconds)
        )
        while True:
            engine.follow_app(plan, listener.app_line)
            ended = engine.app_exit(plan, LOGS_ENDED_GRACE_MS)
            if ended is not None:
                return ended


def _set_scenarios(
    environment: Environment, stack: SandboxGradedStack, scenarios: Mapping[str, str]
) -> None:
    control = environment.stack_clients(stack.endpoints).mocks
    for mock, scenario in scenarios.items():
        if not control.set_scenario(mock, scenario):
            raise RunnerStartError(f"the mock server {mock} refused the scenario {scenario}")


def _held_by(environment: Environment, problem: Problem, plan: StackPlan) -> str:
    """The holder's process id, as the stack's containers carry it."""
    owner = next(
        (
            found.owner_pid
            for found in environment.sandbox.inventory().containers
            if found.stack == plan.identity.name and found.owner_pid is not None
        ),
        None,
    )
    holder = f"process {owner}" if owner is not None else "another process"
    return f"cstudy dev {problem.meta.slug} is already running in {holder}; stop it first"
