"""The events of `cstudy test --events` on a service project
(docs/specs/service-projects.md#what-you-see).

The stream names its run, then passes on each progress notice, with the stack's stage where one
names it, and `commands.test` as one test, id `commands.test`: its start, every line it prints as
an `output`, and its result. Each visible case of the unlocked levels follows as it starts and as
it is judged. The command that writes the stream ends it with the outcome and the exit code.
"""

from dataclasses import replace

from coding_study.application.active_attempt import autograded_language, find_attempt
from coding_study.application.environment import Environment
from coding_study.application.project_runs import project_levels
from coding_study.application.run_events import (
    CaseGraded,
    CaseStarted,
    CommandTested,
    EventSink,
    OutputLine,
    RunCommand,
    RunStarted,
    SuiteTestStarted,
    notice_event,
)
from coding_study.application.service_lifecycle import (
    ServiceTestRequest,
    ServiceTestResult,
    run_service_tests,
)
from coding_study.application.service_stacks import service_project
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.problem import Problem
from coding_study.domain.sandbox import CommandOutcome

COMMAND_TEST_ID = "commands.test"


def stream_service_tests(
    environment: Environment, request: ServiceTestRequest, emit: EventSink
) -> ServiceTestResult:
    """Raises as `run_service_tests`, after the start: the stream then ends with the error."""
    attempt = find_attempt(environment.progress, request.slug, request.language)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    levels = project_levels(meta, attempt.level_unlocked, None)
    language = autograded_language(attempt)
    emit(RunStarted(RunCommand.TEST, meta, attempt, language, levels, environment.clock.now()))
    live = _LiveService(emit, problem)
    streamed = replace(request, on_output=live.printed, listener=live, on_test=live)
    return run_service_tests(environment, streamed, lambda line: emit(notice_event(line)))


class _LiveService:
    """Reports `commands.test` and each visible case as the run reaches them."""

    def __init__(self, emit: EventSink, problem: Problem) -> None:
        self._emit = emit
        self._limit_s = service_project(problem).timeouts.test
        self._levels = {case.id: case.level for case in problem.cases}

    def test_started(self) -> None:
        self._emit(SuiteTestStarted(COMMAND_TEST_ID))

    def printed(self, line: str) -> None:
        """A line `commands.test` printed."""
        self._emit(OutputLine(line))

    def test_ended(self, outcome: CommandOutcome, seconds: float) -> None:
        self._emit(CommandTested(outcome, seconds, self._limit_s))

    def case_started(self, case: RunnableCase) -> None:
        self._emit(CaseStarted(case, self._levels.get(case.id)))

    def case_judged(self, verdict: CaseVerdict) -> None:
        self._emit(CaseGraded(verdict, self._levels.get(verdict.case.id)))
