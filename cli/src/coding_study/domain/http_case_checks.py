"""S23 for a multi-step case (docs/specs/service-projects.md#multi-step-cases): each `{{name}}` is
captured by an earlier step, each `{{` opens a name, each absolute URL written out names an origin
the problem declares, and each output pattern compiles. A URL that is itself a capture is checked
when it is sent. A flow its case uses is already written out into the case's steps, and one
tests.json lacks fails loading."""

import re
from collections.abc import Iterable, Iterator

from coding_study.domain.http_case import (
    HttpCaseInput,
    HttpStep,
    LogAssertion,
    OutputCheck,
    OutputPattern,
    RequestTemplate,
)
from coding_study.domain.http_origins import is_absolute, split_url
from coding_study.domain.http_templates import (
    OPENING,
    assertion_texts,
    expected_texts,
    malformed_placeholder,
    placeholder_names,
    request_texts,
)


def step_issues(http: HttpCaseInput, origins: frozenset[str]) -> Iterator[str]:
    """`origins` are those the problem declares, `http://<name>:<port>`."""
    captured: set[str] = set()
    for step in (*http.steps, *http.cleanup):
        yield from _issues_of(step, captured, origins)
        captured |= set(step.captures)
    for assertion in http.log:
        yield from _log_issues(assertion, captured)
    if http.app_output is not None:
        yield from _output_issues(http.app_output, captured)


def _issues_of(step: HttpStep, captured: set[str], origins: frozenset[str]) -> Iterator[str]:
    template = step.request
    if not isinstance(template, RequestTemplate):
        return
    texts = (*request_texts(template), *expected_texts(step.expected))
    for problem in _text_issues(texts, captured, "is captured by no earlier step"):
        yield f"{step.label}: {problem}"
    origin_problem = _origin_issue(template.target, origins)
    if origin_problem is not None:
        yield f"{step.label}: {origin_problem}"


def _log_issues(assertion: LogAssertion, captured: set[str]) -> Iterator[str]:
    texts = assertion_texts(assertion)
    for problem in _text_issues(texts, captured, "is captured by no step"):
        yield f"log {assertion.mock}: {problem}"


def _output_issues(check: OutputCheck, captured: set[str]) -> Iterator[str]:
    texts = [absent for absent in check.absent if isinstance(absent, str)]
    for problem in _text_issues(texts, captured, "is captured by no step"):
        yield f"app_output: {problem}"
    for absent in check.absent:
        if isinstance(absent, OutputPattern):
            try:
                re.compile(absent.regex)
            except re.error as error:
                yield f"app_output: {absent.regex} is no regular expression: {error}"


def _text_issues(texts: Iterable[str], captured: set[str], unknown: str) -> Iterator[str]:
    for text in texts:
        malformed = malformed_placeholder(text)
        if malformed is not None:
            yield f"{OPENING} opens no {OPENING}name}}}} at {malformed}"
        for name in placeholder_names(text):
            if name not in captured:
                yield f"{OPENING}{name}}}}} {unknown}"


def _origin_issue(target: str, origins: frozenset[str]) -> str | None:
    """A URL that starts with a capture names its origin only when it is sent."""
    if not is_absolute(target):
        return None
    split = split_url(target)
    if split is None:
        return f"{target} is no URL the grader can send: use http://<name>:<port>"
    origin = split[0]
    if OPENING in origin or origin in origins:
        return None
    return f"{origin} is no origin the problem declares; it declares {', '.join(sorted(origins))}"
