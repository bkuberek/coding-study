"""Sending a case's steps in order, as a browser would
(docs/specs/service-projects.md#multi-step-cases).

Each step's texts are filled in with the values earlier steps captured, then sent within what is
left of the case's limit. The first step that fails ends the case. Cleanup steps come after, with
the case's limit afresh: each runs whatever the others did, and one that names a value no step
captured is passed over, since what it would undo never happened.
"""

from dataclasses import dataclass

from coding_study.application.http_grading_ports import AppClient, StackEndpoints
from coding_study.domain.http_case import HttpExpected, HttpRequest, HttpStep
from coding_study.domain.http_grading import Answer, ExchangeFailed, HttpResponse
from coding_study.domain.http_steps import StepAnswer, judged_step, step_failure
from coding_study.domain.http_templates import (
    MissingValueError,
    UnreachableUrlError,
    rendered_expected,
    rendered_request,
)
from coding_study.domain.problem import ComparatorSpec

NANOSECONDS_PER_MILLISECOND = 1_000_000


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
    """Sends steps through one client, keeping the values they capture and the time they spend."""

    def __init__(self, app: AppClient, endpoints: StackEndpoints, rules: StepRules) -> None:
        self._app = app
        self._endpoints = endpoints
        self._rules = rules
        self._spent_ns = 0
        self.values: dict[str, str] = {}

    def run(self, steps: tuple[HttpStep, ...]) -> StepsEnd:
        answer: Answer | None = None
        for position, step in enumerate(steps, start=1):
            prepared = self._prepared(step)
            if isinstance(prepared, _Unsendable):
                return StepsStopped(answer, (prepared.failure,))
            sent = self._send(prepared.request)
            if isinstance(sent, ExchangeFailed):
                return sent
            answer = Answer(sent, prepared.expected)
            judged = judged_step(step, StepAnswer(sent, prepared.expected, self._rules.comparator))
            self.values.update(judged.captured)
            if judged.failures and position < len(steps):
                return StepsStopped(answer, judged.failures)
            if position == len(steps):
                return StepsAnswered(answer, judged.failures)
        return StepsStopped(answer, ())

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

    def _send(self, request: HttpRequest) -> HttpResponse | ExchangeFailed:
        left_ms = self._rules.limit_ms - self._spent_ns // NANOSECONDS_PER_MILLISECOND
        sent = self._app.send(request, max(left_ms, 0))
        self._spent_ns += sent.duration_ns
        return sent

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
