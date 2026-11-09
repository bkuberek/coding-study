"""Judging one step of a case (docs/specs/service-projects.md#multi-step-cases)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from coding_study.domain.http_captures import captured
from coding_study.domain.http_case import HttpExpected, HttpStep
from coding_study.domain.http_grading import HttpResponse, response_failures
from coding_study.domain.problem import ComparatorSpec


@dataclass(frozen=True, slots=True)
class StepAnswer:
    response: HttpResponse
    expected: HttpExpected | None
    """With its `{{captures}}` filled in."""
    comparator: ComparatorSpec


@dataclass(frozen=True, slots=True)
class JudgedStep:
    failures: tuple[str, ...]
    """Each names the step."""
    captured: Mapping[str, str] = field(default_factory=dict[str, str])
    """Only when the answer was right: a wrong answer's values would mislead later steps."""


def judged_step(step: HttpStep, answer: StepAnswer) -> JudgedStep:
    expected = answer.expected
    wrong = (
        response_failures(answer.response, expected, answer.comparator)
        if expected is not None
        else ()
    )
    if wrong:
        return JudgedStep(_named(step, wrong))
    values: dict[str, str] = {}
    missing: list[str] = []
    for name, source in step.captures.items():
        found = captured(source, answer.response)
        if found.value is None:
            missing.append(f"capture {name} from {source.written}: {found.missing}")
        else:
            values[name] = found.value
    return JudgedStep(_named(step, tuple(missing)), values if not missing else {})


def step_failure(step: HttpStep, failure: str) -> str:
    """A failure of `step` that no answer shows, as a URL it could not send."""
    return _named(step, (failure,))[0]


def _named(step: HttpStep, failures: tuple[str, ...]) -> tuple[str, ...]:
    if not step.label:
        return failures
    return tuple(f"{step.label}: {failure}" for failure in failures)
