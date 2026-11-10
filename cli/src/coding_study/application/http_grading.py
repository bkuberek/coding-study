"""Grading a service project over HTTP (docs/specs/service-projects.md#http-grading).

Given a stack that is ready, runs each case of the graded levels in tests.json order: resets the
mock servers, restarts the app with fresh data, or keeping its data, if the case asks, sets its
scenarios, sends its requests or steps within its limit, puts back any backing service a step left
paused or stopped, then judges the answer and the mock servers' logs, and runs its cleanup steps.
A parallel case sends its burst all at once, and one that repeats runs again from its reset.
Nothing before the first request counts toward the limit. An app that dies leaves the remaining
cases not run, as does one that hangs too often. The result is a `Judgement` like a runner's, so
levels, tallies, submissions and events need no code of their own.
"""

import time
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Protocol

from coding_study.application.http_grading_parallel import BurstAnswered, BurstEnd, run_burst
from coding_study.application.http_grading_ports import (
    AppExit,
    GradedStack,
    OpenStackClients,
    StackClients,
    StackStepError,
)
from coding_study.application.http_grading_steps import (
    StepRules,
    StepRunner,
    StepsEnd,
    StepsStopped,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case
from coding_study.domain.comparators import Mismatch
from coding_study.domain.config import Config
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.http_case import HttpCaseInput, LogAssertion
from coding_study.domain.http_grading import (
    FAILURE_SEPARATOR,
    HTTP_COMPARATORS,
    ExchangeFailed,
    ExchangeFailure,
    MockLog,
    answer_outcome,
    answered_verdict,
    log_failures,
)
from coding_study.domain.http_parallel import burst_verdict
from coding_study.domain.http_steps import output_failures
from coding_study.domain.http_templates import MissingValueError, rendered_assertion
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase, concrete_case
from coding_study.domain.levels import cases_up_to
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import ComparatorSpec, Problem
from coding_study.domain.runs import InvalidOutput, NotRun, Raised, Returned, TimedOut, UserError

MAX_HUNG_CASES = 3
"""After this many cases past their limit, the rest are not run, as after a runner's restarts."""
APP_EXIT_GRACE_MS = 2_000
"""How long a failed connection waits for a dying app's exit to show."""
JUDGED_STATUSES = frozenset({CaseStatus.PASS, CaseStatus.FAIL})
"""The verdicts a failed cleanup step or a forbidden output turns into a failure; any other
already says what went wrong."""
TESTS_FILE = "tests.json"
APP_EXITED = "AppExited"


@dataclass(frozen=True, slots=True)
class _StackStep:
    """What the stack failed to do for a case, as its error and the run's reason to stop."""

    error: str
    stops_the_run: str


RESET_FAILED = _StackStep("ResetFailed", "the app's data could not be reset for an earlier case")
RESTART_FAILED = _StackStep("RestartFailed", "the app could not be restarted for an earlier case")
SERVICE_FAILED = _StackStep(
    "ServiceFailed", "a backing service could not be changed or put back for an earlier case"
)
CONNECTION_ERRORS = {
    ExchangeFailure.REFUSED: "ConnectionRefused",
    ExchangeFailure.DROPPED: "ConnectionDropped",
}


class HttpCaseListener(Protocol):
    """Told of each case as it starts and of its verdict; `CaseVerdictListener` is one."""

    def case_started(self, case: RunnableCase) -> None: ...

    def case_judged(self, verdict: CaseVerdict) -> None: ...


@dataclass(frozen=True, slots=True)
class HttpGradingRun:
    problem: Problem
    level: int
    """Cases of levels 1 to `level` run, in tests.json order."""
    config: Config
    listener: HttpCaseListener | None = None


def run_http_grading(
    run: HttpGradingRun, stack: GradedStack, open_clients: OpenStackClients
) -> Judgement:
    """Raises ContentError for a case the stack cannot run, before any request unless only a mock
    server can tell, as of an unknown scenario; RunnerStartError when the mock control interface
    stops answering."""
    endpoints = stack.endpoints
    cases = _checked_cases(run, endpoints.mocks)
    grader = _Grader(stack, open_clients(endpoints), run.listener)
    return Judgement(len(cases), tuple(grader.judged(case) for case in cases))


@dataclass(frozen=True, slots=True)
class _CheckedCase:
    case: RunnableCase
    http: HttpCaseInput
    comparator: ComparatorSpec
    limit_ms: int
    source: str


def _checked_cases(run: HttpGradingRun, known_mocks: tuple[str, ...]) -> tuple[_CheckedCase, ...]:
    checker = _CaseChecker(run, known_mocks)
    return tuple(checker.checked(case) for case in cases_up_to(run.problem.cases, run.level))


@dataclass(frozen=True, slots=True)
class _CaseChecker:
    run: HttpGradingRun
    known_mocks: tuple[str, ...]

    def checked(self, case: Case) -> _CheckedCase:
        meta = self.run.problem.meta
        source = f"{meta.slug}/{TESTS_FILE}"
        http = case.input
        if not isinstance(http, HttpCaseInput):
            raise _content_error(source, case.id, "a service project's case needs a request")
        comparator = http.comparator or meta.comparator
        problem = self._problem_with(http, comparator)
        if problem is not None:
            raise _content_error(source, case.id, problem)
        limit_ms = resolve_hang_guard_ms(self.run.config, case.hang_guard_ms, meta.hang_guard_ms)
        return _CheckedCase(concrete_case(case), http, comparator, limit_ms, source)

    def _problem_with(self, http: HttpCaseInput, comparator: ComparatorSpec) -> str | None:
        if comparator.type not in HTTP_COMPARATORS:
            return f"the comparator {comparator.type} cannot judge a response body"
        if not http.exchange_steps() and http.parallel is None:
            return "a service project's case needs a request, steps or a parallel burst"
        named = (*http.mocks, *_logged_mocks(http.log))
        unknown = [mock for mock in named if mock not in self.known_mocks]
        return f"no mock server named {unknown[0]}" if unknown else None


def _content_error(source: str, case_id: str, message: str) -> ContentError:
    return ContentError([ContentIssue(source, case_id, message)])


class _Grader:
    """The run so far: whether it has stopped, and how many cases have hung the app."""

    def __init__(
        self, stack: GradedStack, clients: StackClients, listener: HttpCaseListener | None
    ) -> None:
        self._stack = stack
        self._app = clients.app
        self._mocks = clients.mocks
        self._listener = listener
        self._hung_cases = 0
        self._stopped: str | None = None
        """Why the remaining cases are not run, in words that name no hidden case."""

    def judged(self, checked: _CheckedCase) -> CaseVerdict:
        if self._stopped is None:
            if self._listener is not None:
                self._listener.case_started(checked.case)
            verdict = self._graded(checked)
        else:
            verdict = CaseVerdict(checked.case, CaseStatus.NOT_RUN, NotRun(self._stopped))
        if self._listener is not None:
            self._listener.case_judged(verdict)
        return verdict

    def _graded(self, checked: _CheckedCase) -> CaseVerdict:
        """A case that repeats runs again, from its reset, after each run that passed; the first
        run that did not pass is the verdict, and says which run it was."""
        runs = checked.http.runs
        run = 1
        verdict = self._graded_once(checked)
        while verdict.status is CaseStatus.PASS and run < runs:
            run += 1
            verdict = self._graded_once(checked)
        return _in_run(verdict, run, runs)

    def _graded_once(self, checked: _CheckedCase) -> CaseVerdict:
        # The clock the engine stamps the app's output with, read before a fresh start, so that
        # the output check also covers what the app prints while it starts.
        started_s = time.time()
        try:
            self._prepare(checked)
        except StackStepError as failed:
            stack_step = RESET_FAILED if checked.http.fresh else RESTART_FAILED
            return self._stack_failed(checked, failed, stack_step)
        try:
            return self._exchanged(checked, started_s)
        except StackStepError as failed:
            return self._stack_failed(checked, failed, SERVICE_FAILED)

    def _stack_failed(
        self, checked: _CheckedCase, failed: StackStepError, step: _StackStep
    ) -> CaseVerdict:
        """A stack that could not do what a case asks: the case is an error, and the rest are not
        run, since the stack is no longer as the problem made it."""
        self._stopped = step.stops_the_run
        error = UserError(step.error, str(failed), failed.output_tail)
        return CaseVerdict(checked.case, CaseStatus.ERROR, Raised(error, 0))

    def _prepare(self, checked: _CheckedCase) -> None:
        """A restart, fresh or keeping the app's data, comes between two resets: the first so that
        the app's startup meets no scenario left by the last case, the second so that its log and
        counters hold this case's requests alone."""
        self._mocks.reset()
        http = checked.http
        if http.fresh or http.restart_app:
            if http.fresh:
                self._stack.restart_app_with_fresh_data()
            else:
                self._stack.restart_app()
            self._mocks.reset()
        for mock, scenario in checked.http.mocks.items():
            if not self._mocks.set_scenario(mock, scenario):
                message = f"the mock server {mock} has no scenario this case names"
                raise _content_error(checked.source, checked.case.id, message)

    def _exchanged(self, checked: _CheckedCase, started_s: float) -> CaseVerdict:
        """The steps, then the backing services they changed put back, then the cleanup, then
        what the app printed meanwhile. Raises StackStepError when a service cannot be changed."""
        http = checked.http
        self._app.clear_cookies()
        rules = StepRules(checked.comparator, checked.limit_ms)
        runner = StepRunner(self._app, self._stack, rules)
        try:
            ended = (
                run_burst(runner, http, http.parallel)
                if http.parallel is not None
                else runner.run(http.exchange_steps())
            )
        finally:
            runner.put_services_back()
        verdict = self._judged(checked, ended, runner)
        if self._stopped is not None:
            return verdict
        if http.cleanup:
            verdict = _with_failures(verdict, runner.cleaned_up(http.cleanup))
        if http.app_output is not None and verdict.status in JUDGED_STATUSES:
            printed = self._stack.app_output(started_s)
            found = output_failures(http.app_output, printed, runner.values)
            verdict = _with_failures(verdict, found)
        return verdict

    def _judged(
        self, checked: _CheckedCase, ended: StepsEnd | BurstEnd, runner: StepRunner
    ) -> CaseVerdict:
        if isinstance(ended, ExchangeFailed):
            return self._failed(checked, ended)
        if isinstance(ended, StepsStopped):
            return _stopped(checked.case, ended)
        logs = self._logs(checked.http.log)
        log_problems = tuple(_log_problems(checked.http.log, logs, runner.values))
        failures = (*ended.failures, *log_problems)
        if isinstance(ended, BurstAnswered):
            return burst_verdict(checked.case, ended.answer, failures)
        return answered_verdict(checked.case, ended.answer, failures)

    def _logs(self, assertions: tuple[LogAssertion, ...]) -> dict[str, MockLog]:
        """Each mock server's log once, read after the last answer."""
        asserted = dict.fromkeys(_logged_mocks(assertions))
        return {mock: self._mocks.log(mock) for mock in asserted}

    def _failed(self, checked: _CheckedCase, failed: ExchangeFailed) -> CaseVerdict:
        match failed.failure:
            case ExchangeFailure.TIMED_OUT:
                return self._timed_out(checked, failed)
            case ExchangeFailure.REFUSED | ExchangeFailure.DROPPED:
                return self._unreachable(checked, failed)
            case ExchangeFailure.NOT_HTTP | ExchangeFailure.TOO_LARGE:
                outcome = InvalidOutput(failed.detail, failed.duration_ns)
                return CaseVerdict(checked.case, CaseStatus.INVALID, outcome)

    def _timed_out(self, checked: _CheckedCase, failed: ExchangeFailed) -> CaseVerdict:
        ended = self._stack.app_exit(0)
        if ended is not None:
            return self._died(checked, ended, failed)
        self._hung_cases += 1
        if self._hung_cases >= MAX_HUNG_CASES:
            self._stopped = f"the app hung on {MAX_HUNG_CASES} earlier cases"
        else:
            self._restart_hung_app()
        return CaseVerdict(checked.case, CaseStatus.TIMEOUT, TimedOut(checked.limit_ms))

    def _restart_hung_app(self) -> None:
        try:
            self._stack.restart_app()
        except StackStepError as failed:
            self._stopped = f"the app could not be restarted after an earlier case: {failed}"

    def _unreachable(self, checked: _CheckedCase, failed: ExchangeFailed) -> CaseVerdict:
        ended = self._stack.app_exit(APP_EXIT_GRACE_MS)
        if ended is not None:
            return self._died(checked, ended, failed)
        error = UserError(CONNECTION_ERRORS[failed.failure], failed.detail)
        return CaseVerdict(checked.case, CaseStatus.ERROR, Raised(error, failed.duration_ns))

    def _died(self, checked: _CheckedCase, ended: AppExit, failed: ExchangeFailed) -> CaseVerdict:
        self._stopped = f"the app exited with code {ended.exit_code} during an earlier case"
        message = f"the app exited with code {ended.exit_code} during this case"
        error = UserError(APP_EXITED, message, ended.stderr_tail)
        return CaseVerdict(checked.case, CaseStatus.ERROR, Raised(error, failed.duration_ns))


def _log_problems(
    assertions: tuple[LogAssertion, ...], logs: dict[str, MockLog], values: dict[str, str]
) -> Iterator[str]:
    """An assertion that names a value the case never captured is passed over: the step that
    should have captured it has already failed the case."""
    for assertion in assertions:
        try:
            filled = rendered_assertion(assertion, values)
        except MissingValueError:
            continue
        same = assertion.body_same_as
        reference = logs[same.mock] if same is not None else None
        yield from log_failures(filled, logs[assertion.mock], reference)


def _logged_mocks(assertions: tuple[LogAssertion, ...]) -> Iterator[str]:
    """Each mock server whose log an assertion reads, its own or the one its `body_same_as`
    compares with."""
    for assertion in assertions:
        yield assertion.mock
        if assertion.body_same_as is not None:
            yield assertion.body_same_as.mock


def _stopped(case: RunnableCase, stopped: StepsStopped) -> CaseVerdict:
    answer = stopped.answer
    outcome = (
        answer_outcome(answer.response, answer.expected)
        if answer is not None
        else Returned(None, 0)
    )
    return CaseVerdict(
        case, CaseStatus.FAIL, outcome, Mismatch(FAILURE_SEPARATOR.join(stopped.failures))
    )


def _in_run(verdict: CaseVerdict, run: int, runs: int) -> CaseVerdict:
    """A failure of a case that repeats names its run."""
    mismatch = verdict.mismatch
    if runs == 1 or mismatch is None:
        return verdict
    return replace(verdict, mismatch=Mismatch(f"run {run} of {runs}: {mismatch.detail}"))


def _with_failures(verdict: CaseVerdict, failures: tuple[str, ...]) -> CaseVerdict:
    """A judged case with these failures too: a cleanup step that went wrong, since the cases
    after it may meet what it should have undone, or output the case forbids."""
    if not failures or verdict.status not in JUDGED_STATUSES:
        return verdict
    mismatch = verdict.mismatch
    found = [mismatch.detail] if mismatch is not None and mismatch.detail else []
    reasons = FAILURE_SEPARATOR.join([*found, *failures])
    return replace(verdict, status=CaseStatus.FAIL, mismatch=Mismatch(reasons))
