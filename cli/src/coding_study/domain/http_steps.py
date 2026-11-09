"""Judging one step of a case, and what the app printed while the case ran
(docs/specs/service-projects.md#multi-step-cases)."""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from coding_study.domain.http_captures import captured
from coding_study.domain.http_case import HttpExpected, HttpStep, OutputCheck, OutputPattern
from coding_study.domain.http_grading import HttpResponse, response_failures
from coding_study.domain.http_templates import MissingValueError, filled
from coding_study.domain.problem import ComparatorSpec
from coding_study.domain.value_text import value_text

OUTPUT = "app output"
SHOWN_OUTPUT_LIMIT = 60
"""How much of what the app printed a reason shows: enough to recognize it, not a whole token."""


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


def output_failures(check: OutputCheck, output: str, values: Mapping[str, str]) -> tuple[str, ...]:
    """What the app printed that the case forbids. A text that names a value no step captured
    is passed over: what was never captured cannot have been printed."""
    return tuple(_printed(check, output, values))


def _printed(check: OutputCheck, output: str, values: Mapping[str, str]) -> Iterator[str]:
    for absent in check.absent:
        if isinstance(absent, OutputPattern):
            found = re.search(absent.regex, output)
            if found is not None:
                shown = value_text(found[0], SHOWN_OUTPUT_LIMIT)
                yield f"{OUTPUT}: printed {shown}, which matches {absent.regex}"
            continue
        try:
            text = filled(absent, values)
        except MissingValueError:
            continue
        if text and text in output:
            yield f"{OUTPUT}: printed {value_text(text, SHOWN_OUTPUT_LIMIT)}, which it must not"
