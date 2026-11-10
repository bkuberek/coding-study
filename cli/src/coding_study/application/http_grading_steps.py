"""Sending a case's steps in order, as a browser would
(docs/specs/service-projects.md#multi-step-cases).

Each step's texts are filled in with the values earlier steps captured, then sent within what is
left of the case's limit. The first step that fails ends the case. Cleanup steps come after, with
the case's limit afresh: each runs whatever the others did, and one that names a value no step
captured is passed over, since what it would undo never happened.

A sleep step waits, and counts toward the case's limit as a request does. A service step pauses,
unpauses, stops or starts a backing service on the stack's own clock, and whatever a case left
paused or stopped is put back after it, whatever happened.
"""

import time
from dataclasses import dataclass

from coding_study.application.http_grading_ports import AppClient, GradedStack
from coding_study.domain.http_case import (
    CaseStep,
    HttpExpected,
    HttpRequest,
    HttpStep,
    ServiceStep,
    SleepStep,
)
from coding_study.domain.http_grading import Answer, ExchangeFailed, ExchangeFailure, HttpResponse
from coding_study.domain.http_steps import StepAnswer, judged_step, step_failure
from coding_study.domain.http_templates import (
    MissingValueError,
    UnreachableUrlError,
    rendered_expected,
    rendered_request,
)
from coding_study.domain.problem import ComparatorSpec
from coding_study.domain.sandbox import ServiceChange

NANOSECONDS_PER_MILLISECOND = 1_000_000
MILLISECONDS_PER_SECOND = 1_000


@dataclass(frozen=True, slots=True)
class StepsAnswered:
    """Every step was sent; the last one's answer, with what was wrong with it, if anything, is
    judged together with the case's logs."""

    answer: Answer
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StepsStopped:
    """A step before the last went wrong, or could not be sent, so the case ends there."""

    answer: Answer | None
    """The last answer the case got; None when its first step could not be sent."""
    failures: tuple[str, ...]


type StepsEnd = StepsAnswered | StepsStopped | ExchangeFailed


@dataclass(frozen=True, slots=True)
class StepRules:
    comparator: ComparatorSpec
    limit_ms: int


@dataclass(frozen=True, slots=True)
class _Prepared:
    request: HttpRequest
    expected: HttpExpected | None


@dataclass(frozen=True, slots=True)
class _Unsendable:
    failure: str
    missing_value: bool
    """It names a value no step captured."""


class StepRunner:
    """Sends steps through one client, keeping the values they capture, the time they spend and
    the backing services they change."""

    def __init__(self, app: AppClient, stack: GradedStack, rules: StepRules) -> None:
        self._app = app
        self._stack = stack
        self._endpoints = stack.endpoints
        self._rules = rules
        self._spent_ns = 0
        self._changed: dict[str, ServiceChange] = {}
        """The last change of each backing service a step changed."""
        self.values: dict[str, str] = {}

    def run(self, steps: tuple[CaseStep, ...]) -> StepsEnd:
        """The last request's answer is the one judged, even when steps that send nothing follow
        it, such as a sleep before the logs are read."""
        last = _last_request(steps)
        answer: Answer | None = None
        failures: tuple[str, ...] = ()
        for position, step in enumerate(steps, start=1):
            if not isinstance(step, HttpStep):
                cut = self._took(step)
                if cut is not None:
                    return cut
                continue
            prepared = self._prepared(step)
            if isinstance(prepared, _Unsendable):
                return StepsStopped(answer, (prepared.failure,))
            sent = self._send(prepared.request)
            if isinstance(sent, ExchangeFailed):
                return sent
            answer = Answer(sent, prepared.expected)
            judged = judged_step(step, StepAnswer(sent, prepared.expected, self._rules.comparator))
            self.values.update(judged.captured)
            if judged.failures and position < last:
                return StepsStopped(answer, judged.failures)
            failures = judged.failures
        return StepsAnswered(answer, failures) if answer is not None else StepsStopped(None, ())

    def cleaned_up(self, steps: tuple[HttpStep, ...]) -> tuple[str, ...]:
        """What went wrong with the cleanup steps, each sent within the case's limit afresh."""
        self._spent_ns = 0
        failures: list[str] = []
        for step in steps:
            prepared = self._prepared(step)
            if isinstance(prepared, _Unsendable):
                if not prepared.missing_value:
                    failures.append(prepared.failure)
                continue
            sent = self._send(prepared.request)
            if isinstance(sent, ExchangeFailed):
                failures.append(step_failure(step, sent.detail))
                continue
            judged = judged_step(step, StepAnswer(sent, prepared.expected, self._rules.comparator))
            failures.extend(judged.failures)
        return tuple(failures)

    def send_together(
        self, requests: tuple[HttpRequest, ...]
    ) -> tuple[HttpResponse | ExchangeFailed, ...]:
        """A parallel case's burst, within what is left of the case's limit. The requests run
        side by side, so the burst spends what its slowest one took."""
        sent = self._app.send_together(requests, self._left_ms())
        self._spent_ns += max((answer.duration_ns for answer in sent), default=0)
        return sent

    @property
    def spent_ns(self) -> int:
        return self._spent_ns

    def put_services_back(self) -> None:
        """Unpauses or starts each backing service the case left paused or stopped, so that its
        cleanup and the next case meet the stack as it started. Raises StackStepError when it
        cannot."""
        changed, self._changed = self._changed, {}
        for change in changed.values():
            undoing = change.undoing()
            if undoing is not None:
                self._stack.change_service(undoing)

    def _took(self, step: SleepStep | ServiceStep) -> ExchangeFailed | None:
        """A step that sends nothing; a sleep may run out the case's limit."""
        if isinstance(step, SleepStep):
            return self._slept(step)
        self._stack.change_service(step.change)
        self._changed[step.change.service] = step.change
        return None

    def _slept(self, step: SleepStep) -> ExchangeFailed | None:
        """A sleep longer than what is left of the case's limit waits that long and ends the case
        as timed out, as an answer that came too late would."""
        left_ms = self._left_ms()
        waited_ms = min(step.ms, left_ms)
        time.sleep(waited_ms / MILLISECONDS_PER_SECOND)
        self._spent_ns += waited_ms * NANOSECONDS_PER_MILLISECOND
        if step.ms <= left_ms:
            return None
        detail = f"{step.label}: the case's limit ran out during the sleep"
        return ExchangeFailed(ExchangeFailure.TIMED_OUT, detail, self._spent_ns)

    def _send(self, request: HttpRequest) -> HttpResponse | ExchangeFailed:
        sent = self._app.send(request, self._left_ms())
        self._spent_ns += sent.duration_ns
        return sent

    def _left_ms(self) -> int:
        return max(self._rules.limit_ms - self._spent_ns // NANOSECONDS_PER_MILLISECOND, 0)

    def _prepared(self, step: HttpStep) -> _Prepared | _Unsendable:
        """The request as it goes out. A single-request case's goes as it was written."""
        template = step.request
        if isinstance(template, HttpRequest):
            return _Prepared(template, step.expected)
        try:
            request = rendered_request(template, self.values)
            expected = (
                rendered_expected(step.expected, self.values) if step.expected is not None else None
            )
        except MissingValueError as missing:
            failure = step_failure(step, f"{{{{{missing.name}}}}} was never captured")
            return _Unsendable(failure, missing_value=True)
        except UnreachableUrlError as error:
            failure = step_failure(step, f"{error.url} is no URL the grader can send")
            return _Unsendable(failure, missing_value=False)
        if self._endpoints.address_of(request.origin) is None:
            failure = step_failure(step, f"the stack lets the grader reach no {request.origin}")
            return _Unsendable(failure, missing_value=False)
        return _Prepared(request, expected)


def _last_request(steps: tuple[CaseStep, ...]) -> int:
    """The position, from 1, of the last step that sends a request; 0 when none does."""
    sent = [position for position, step in enumerate(steps, start=1) if isinstance(step, HttpStep)]
    return sent[-1] if sent else 0
