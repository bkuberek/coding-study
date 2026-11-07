"""Grading a service project over HTTP (docs/specs/service-projects.md#http-grading).

Given a stack that is ready, runs each case of the graded levels in tests.json order: resets the
mock servers, restarts the app with fresh data if the case asks, sets its scenarios, sends its
requests within its limit, then judges the answer and the mock servers' logs. Nothing before the
first request counts toward the limit. An app that dies leaves the remaining cases not run, as
does one that hangs too often. The result is a `Judgement` like a runner's, so levels, tallies,
submissions and events need no code of their own.
"""

from dataclasses import dataclass
from typing import Protocol

from coding_study.application.http_grading_ports import (
    AppExit,
    GradedStack,
    OpenStackClients,
    StackClients,
    StackStepError,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case
from coding_study.domain.comparators import Mismatch
from coding_study.domain.config import Config
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.http_case import HttpCaseInput, HttpRequest
from coding_study.domain.http_grading import (
    HTTP_COMPARATORS,
    Answer,
    ExchangeFailed,
    ExchangeFailure,
    HttpResponse,
    answer_outcome,
    answered_verdict,
    before_failure,
)
from coding_study.domain.judging import CaseVerdict, Judgement, RunnableCase, concrete_case
from coding_study.domain.levels import cases_up_to
from coding_study.domain.precedence import resolve_hang_guard_ms
from coding_study.domain.problem import ComparatorSpec, Problem
from coding_study.domain.runs import InvalidOutput, NotRun, Raised, TimedOut, UserError

MAX_HUNG_CASES = 3
"""After this many cases past their limit, the rest are not run, as after a runner's restarts."""
APP_EXIT_GRACE_MS = 2_000
"""How long a failed connection waits for a dying app's exit to show."""
NANOSECONDS_PER_MILLISECOND = 1_000_000
TESTS_FILE = "tests.json"
APP_EXITED = "AppExited"
RESET_FAILED = "ResetFailed"
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
        named = (*http.mocks, *(assertion.mock for assertion in http.log))
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
        try:
            self._prepare(checked)
        except StackStepError as failed:
            self._stopped = "the app's data could not be reset for an earlier case"
            error = UserError(RESET_FAILED, str(failed), failed.output_tail)
            return CaseVerdict(checked.case, CaseStatus.ERROR, Raised(error, 0))
        return self._exchanged(checked)

    def _prepare(self, checked: _CheckedCase) -> None:
        """A fresh start comes between two resets: the first so that the app's startup meets no
        scenario left by the last case, the second so that its log and counters hold this case's
        requests alone."""
        self._mocks.reset()
        if checked.http.fresh:
            self._stack.restart_app_with_fresh_data()
            self._mocks.reset()
        for mock, scenario in checked.http.mocks.items():
            if not self._mocks.set_scenario(mock, scenario):
                message = f"the mock server {mock} has no scenario this case names"
                raise _content_error(checked.source, checked.case.id, message)

    def _exchanged(self, checked: _CheckedCase) -> CaseVerdict:
        http = checked.http
        spent_ns = 0
        for index, request in enumerate(http.before):
            sent = self._send(request, checked.limit_ms, spent_ns)
            if isinstance(sent, ExchangeFailed):
                return self._failed(checked, sent)
            failure = before_failure(index, request, sent)
            if failure is not None:
                outcome = answer_outcome(sent, http.expected)
                return CaseVerdict(checked.case, CaseStatus.FAIL, outcome, Mismatch(failure))
            spent_ns += sent.duration_ns
        sent = self._send(http.request, checked.limit_ms, spent_ns)
        if isinstance(sent, ExchangeFailed):
            return self._failed(checked, sent)
        asserted = dict.fromkeys(assertion.mock for assertion in http.log)
        logs = {mock: self._mocks.log(mock) for mock in asserted}
        return answered_verdict(checked.case, http, Answer(sent, checked.comparator, logs))

    def _send(
        self, request: HttpRequest, limit_ms: int, spent_ns: int
    ) -> HttpResponse | ExchangeFailed:
        return self._app.send(request, max(limit_ms - spent_ns // NANOSECONDS_PER_MILLISECOND, 0))

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
