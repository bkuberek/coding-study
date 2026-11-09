"""A graded run of a service project (docs/specs/service-projects.md#graded-run): a fresh stack
with every scenario, the cases of the graded levels over HTTP, and the stack gone again.

Two clocks stay apart. Up to the moment the stack is ready, the startup budget runs and a failure
says so. Every case's limit starts at its first request, and the time reported starts at ready.
"""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.graded_stack import RunningStack, SandboxGradedStack
from coding_study.application.http_grading import HttpCaseListener, HttpGradingRun, run_http_grading
from coding_study.application.ports import ProgressNotice
from coding_study.application.sandbox import running_stack
from coding_study.application.service_lifecycle import prepare_service_run
from coding_study.application.service_stacks import (
    from_empty_stack_plan,
    graded_stack_plan,
    service_project,
)
from coding_study.domain.attempts import AttemptMode
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import cases_up_to
from coding_study.domain.problem import Problem
from coding_study.domain.runs import UserError
from coding_study.domain.sandbox import StackPlan, StackStartError, StartupFailure

MIGRATION_FAILED = "MigrationFailed"
APP_DID_NOT_START = "AppDidNotStart"
FAILED_ON_EXISTING_DATA = "bootstrap failed on existing data"


@dataclass(frozen=True, slots=True)
class ServiceGrading:
    problem: Problem
    level: int
    """Cases of levels 1 to `level` run."""
    listener: HttpCaseListener | None = None
    mode: AttemptMode = AttemptMode.NEW


@dataclass(frozen=True, slots=True)
class GradedRun:
    judgement: Judgement
    startup_seconds: float = 0.0
    """The first clock: no limit or result counts it."""
    grading_seconds: float = 0.0
    """The second clock, from the moment the stack was ready."""


def grade_service_project(
    environment: Environment, grading: ServiceGrading, notify: ProgressNotice
) -> GradedRun:
    """The project folder's code, graded. Code that keeps the stack from becoming ready is a load
    error, as code that does not compile is, and the submission is stored.

    Raises SandboxError or StackStartError when the sandbox failed and your code is not to blame,
    and ContentError for a case the stack cannot run: nothing is stored then.
    """
    prepare_service_run(environment, grading.problem, notify)
    plan = graded_stack_plan(environment, grading.problem, grading.level)
    return grade_on_stack(environment, grading, plan, notify)


def grade_on_stack(
    environment: Environment,
    grading: ServiceGrading,
    plan: StackPlan,
    notify: ProgressNotice,
) -> GradedRun:
    """`plan` brought up, its cases run, and the stack gone: `grade_service_project` once the
    project is prepared."""
    problem = grading.problem
    service = service_project(problem)
    engine = environment.sandbox
    clock = environment.clock
    run = HttpGradingRun(problem, grading.level, environment.config, grading.listener)
    if plan.grade_setup is not None:
        from_empty = _bootstrap_from_empty(environment, grading, plan, notify)
        if from_empty is not None:
            count = len(cases_up_to(problem.cases, grading.level))
            return GradedRun(Judgement(count, load_error=from_empty))
    try:
        with running_stack(engine, plan, service.startup_budget, notify) as ready:
            stack = SandboxGradedStack(engine, RunningStack(plan, ready), service)
            began = clock.monotonic()
            judgement = run_http_grading(run, stack, environment.stack_clients)
            return GradedRun(judgement, ready.startup_seconds, clock.monotonic() - began)
    except StackStartError as failure:
        if not failure.failure.is_your_code:
            raise
        count = len(cases_up_to(problem.cases, grading.level))
        return GradedRun(Judgement(count, load_error=_load_error(failure, grading.mode)))


def _bootstrap_from_empty(
    environment: Environment, grading: ServiceGrading, graded: StackPlan, notify: ProgressNotice
) -> UserError | None:
    """`grade_setup` loads the baseline before `bootstrap`, so a graded run with it first proves
    that your migrations also run from empty data, on a stack of their own whose data goes with it.
    No hidden data is there, so a failure shows its output even in a mock attempt."""
    plan = from_empty_stack_plan(environment, grading.problem, graded)
    budget = service_project(grading.problem).startup_budget
    notify("bootstrap from empty data")
    try:
        with running_stack(environment.sandbox, plan, budget, notify):
            return None
    except StackStartError as failure:
        if failure.failure is not StartupFailure.BOOTSTRAP:
            raise
        return UserError(MIGRATION_FAILED, f"bootstrap from empty data: {failure}", failure.output)


def _load_error(failure: StackStartError, mode: AttemptMode) -> UserError:
    """A migration in a mock attempt says only that it failed: its output could name hidden data."""
    if failure.failure is StartupFailure.BOOTSTRAP:
        if mode is AttemptMode.MOCK:
            return UserError(MIGRATION_FAILED, FAILED_ON_EXISTING_DATA)
        return UserError(MIGRATION_FAILED, str(failure), failure.output)
    return UserError(APP_DID_NOT_START, str(failure), failure.output)
