"""Judging what an app answered over HTTP (docs/specs/service-projects.md#hidden-http-case).

A failure's reason names what differs, by its path in the body, so that it stays useful where a
report cuts the expected and actual values short.
"""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from itertools import islice, pairwise
from typing import NoReturn

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Expected, FunctionInput, JsonValue
from coding_study.domain.comparators import Comparator, Mismatch, comparator_for
from coding_study.domain.http_case import HttpCaseInput, HttpExpected, HttpRequest, LogAssertion
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import Returned
from coding_study.domain.value_text import ELLIPSIS, json_text, value_text

MAX_DIFFERENCES = 5
MORE_DIFFERENCES = "and more differences in the body"
FAILURE_SEPARATOR = "; "
DIFFERENCE_VALUE_LIMIT = 120
"""How much of one differing value a reason shows; the path says where it is."""
TEXT_CONTEXT = 40
"""The characters a reason shows on each side of where two long texts first differ."""
BODY = "body"
CONTENT_TYPE_HEADER = "content-type"
SUCCESS_STATUSES = range(200, 300)

_MULTISET_COMPARATORS = frozenset({ComparatorType.UNORDERED, ComparatorType.UNORDERED_NESTED})
_NO_INPUT = FunctionInput({})


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    """By lowercase name; a repeated header is joined with `, `."""
    body: bytes
    duration_ns: int = 0
    """From sending the request to the end of the response."""


@dataclass(frozen=True, slots=True)
class LoggedRequest:
    """One entry of a mock server's request log (docs/specs/service-projects.md#request-log)."""

    route: str | None
    received_ms: int
    responded_ms: int | None
    """None while the request is still being answered."""


@dataclass(frozen=True, slots=True)
class MockLog:
    entries: tuple[LoggedRequest, ...] = ()
    dropped: int = 0
    """Requests past the log's limit: answered, counted and not kept."""


@dataclass(frozen=True, slots=True)
class Answer:
    """What a case got back."""

    response: HttpResponse
    comparator: ComparatorSpec
    logs: Mapping[str, MockLog] = field(default_factory=dict[str, MockLog])
    """The log of each mock server the case asserts on, read after the response."""


def answered_verdict(case: RunnableCase, http: HttpCaseInput, answer: Answer) -> CaseVerdict:
    """PASS, or FAIL with every reason found."""
    response_problems = response_failures(answer.response, http.expected, answer.comparator)
    log_problems = (
        failure
        for assertion in http.log
        for failure in log_failures(assertion, answer.logs[assertion.mock])
    )
    failures = (*response_problems, *log_problems)
    outcome = answer_outcome(answer.response, http.expected)
    if failures:
        return CaseVerdict(
            case, CaseStatus.FAIL, outcome, Mismatch(FAILURE_SEPARATOR.join(failures))
        )
    return CaseVerdict(case, CaseStatus.PASS, outcome)


def answer_outcome(response: HttpResponse, expected: HttpExpected) -> Returned:
    """The answer as a report shows it: its status, its body, and the headers the case lists."""
    output: dict[str, JsonValue] = {
        "status": response.status,
        BODY: _shown_body(response.body, expected.body),
    }
    if expected.headers:
        output["headers"] = {
            name: response.headers[name.lower()]
            for name in expected.headers
            if name.lower() in response.headers
        }
    return Returned(output, response.duration_ns)


def response_failures(
    response: HttpResponse, expected: HttpExpected, comparator: ComparatorSpec
) -> tuple[str, ...]:
    """Why `response` is wrong. A wrong status says only that: an error's body differs from the
    expected one anyway, and the report shows it as the actual value."""
    if response.status != expected.status:
        return (f"status: expected {expected.status}, got {response.status}",)
    return (
        *_header_failures(response.headers, expected.headers),
        *_body_failures(response.body, expected.body, comparator),
    )


def before_failure(index: int, request: HttpRequest, response: HttpResponse) -> str | None:
    """Why a case's `before` request stops the case; None when it answered 2xx."""
    if response.status in SUCCESS_STATUSES:
        return None
    where = f"before[{index}] {request.method} {request.target}"
    return f"{where}: expected a 2xx status, got {response.status}"


def log_failures(assertion: LogAssertion, log: MockLog) -> tuple[str, ...]:
    label = f"{assertion.mock} {assertion.route}" if assertion.route else assertion.mock
    matching = tuple(
        entry for entry in log.entries if assertion.route is None or entry.route == assertion.route
    )
    problems = (
        *_count_failures(assertion, len(matching) + log.dropped),
        *_gap_failure(assertion, matching),
    )
    return tuple(f"{label}: {problem}" for problem in problems)


def _count_failures(assertion: LogAssertion, seen: int) -> Iterator[str]:
    if assertion.count is not None and seen != assertion.count:
        yield f"expected {_requests(assertion.count)}, saw {seen}"
    if assertion.min_count is not None and seen < assertion.min_count:
        yield f"expected at least {_requests(assertion.min_count)}, saw {seen}"
    if assertion.max_count is not None and seen > assertion.max_count:
        yield f"expected at most {_requests(assertion.max_count)}, saw {seen}"


def _requests(count: int) -> str:
    return "1 request" if count == 1 else f"{count} requests"


def _gap_failure(assertion: LogAssertion, entries: tuple[LoggedRequest, ...]) -> tuple[str, ...]:
    """The first gap too short; only the first, since one early retry usually explains the rest."""
    minimum = assertion.min_gap_ms
    if minimum is None:
        return ()
    for number, (earlier, later) in enumerate(pairwise(entries), start=1):
        wanted = f"expected at least {minimum} ms from response {number} to request {number + 1}"
        if earlier.responded_ms is None:
            return (f"{wanted}, but request {number + 1} came before response {number}",)
        gap = later.received_ms - earlier.responded_ms
        if gap < minimum:
            return (f"{wanted}, saw {max(gap, 0)} ms",)
    return ()


def _header_failures(actual: Mapping[str, str], expected: Mapping[str, str]) -> Iterator[str]:
    for name, wanted in expected.items():
        found = actual.get(name.lower())
        if found is None:
            yield f"header {name}: expected {json_text(wanted)}, and it is missing"
        elif not _header_matches(name, wanted, found):
            yield f"header {name}: expected {json_text(wanted)}, got {json_text(found)}"


def _header_matches(name: str, wanted: str, found: str) -> bool:
    """A framework may add a charset to a content type, so one that names none compares without."""
    if name.lower() == CONTENT_TYPE_HEADER and ";" not in wanted:
        return found.partition(";")[0].strip().lower() == wanted.strip().lower()
    return found == wanted


def _body_failures(
    body: bytes, expected: Expected | None, comparator: ComparatorSpec
) -> tuple[str, ...]:
    if expected is None:
        return ()
    wanted = expected.value
    text = _text(body)
    if isinstance(wanted, str):
        return () if text == wanted else (_value_difference(BODY, wanted, text),)
    if not text:
        return (f"{BODY}: expected JSON, got an empty body",)
    try:
        actual = _parsed(text)
    except (ValueError, RecursionError) as error:
        shown = value_text(text, DIFFERENCE_VALUE_LIMIT)
        return (f"{BODY}: expected JSON, and this does not parse ({error}): {shown}",)
    return _json_differences(wanted, actual, comparator)


def _text(body: bytes) -> str:
    return body.decode(errors="replace")


def _parsed(text: str) -> JsonValue:
    """Raises ValueError for anything that is not JSON, as `NaN` is not, though Python writes it."""
    return json.loads(text, parse_constant=_refused_constant)


def _refused_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not JSON")


def _shown_body(body: bytes, expected: Expected | None) -> JsonValue:
    text = _text(body)
    if expected is not None and isinstance(expected.value, str):
        return text
    try:
        return _parsed(text)
    except (ValueError, RecursionError):
        return text


def _json_differences(
    expected: JsonValue, actual: JsonValue, spec: ComparatorSpec
) -> tuple[str, ...]:
    comparator = comparator_for(spec)
    if comparator.compare(Expected(expected), actual, _NO_INPUT) is None:
        return ()
    if spec.type in _MULTISET_COMPARATORS:
        return _limited(_multiset_differences(expected, actual, comparator))
    return _limited(_structural_differences(expected, actual, _Walk(comparator, BODY)))


def _limited(differences: Iterator[str]) -> tuple[str, ...]:
    kept = tuple(islice(differences, MAX_DIFFERENCES + 1))
    if len(kept) > MAX_DIFFERENCES:
        return (*kept[:MAX_DIFFERENCES], MORE_DIFFERENCES)
    return kept


def _multiset_differences(
    expected: JsonValue, actual: JsonValue, comparator: Comparator
) -> Iterator[str]:
    if not isinstance(expected, list) or not isinstance(actual, list):
        yield f"{BODY}: expected an array, got {_shown(actual)}"
        return
    unmatched = list(actual)
    for element in expected:
        index = _matching_index(element, unmatched, comparator)
        if index is None:
            yield f"{BODY}: missing element {_shown(element)}"
        else:
            del unmatched[index]
    for element in unmatched:
        yield f"{BODY}: unexpected element {_shown(element)}"


def _matching_index(
    element: JsonValue, candidates: list[JsonValue], comparator: Comparator
) -> int | None:
    wanted = Expected([element])
    for index, candidate in enumerate(candidates):
        if comparator.compare(wanted, [candidate], _NO_INPUT) is None:
            return index
    return None


@dataclass(frozen=True, slots=True)
class _Walk:
    """Where a walk through two JSON values is, and how it compares single values."""

    comparator: Comparator
    path: str

    def into(self, step: str) -> "_Walk":
        return _Walk(self.comparator, self.path + step)


def _structural_differences(expected: JsonValue, actual: JsonValue, walk: _Walk) -> Iterator[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        yield from _object_differences(expected, actual, walk)
    elif isinstance(expected, list) and isinstance(actual, list):
        yield from _array_differences(expected, actual, walk)
    elif walk.comparator.compare(Expected(expected), actual, _NO_INPUT) is not None:
        yield _value_difference(walk.path, expected, actual)


def _object_differences(
    expected: dict[str, JsonValue], actual: dict[str, JsonValue], walk: _Walk
) -> Iterator[str]:
    for name, value in expected.items():
        field_walk = walk.into(f".{name}")
        if name in actual:
            yield from _structural_differences(value, actual[name], field_walk)
        else:
            yield f"{field_walk.path}: missing, expected {_shown(value)}"
    for name, value in actual.items():
        if name not in expected:
            yield f"{walk.path}.{name}: unexpected field, with value {_shown(value)}"


def _array_differences(
    expected: list[JsonValue], actual: list[JsonValue], walk: _Walk
) -> Iterator[str]:
    if len(expected) != len(actual):
        yield f"{walk.path}: expected {len(expected)} elements, got {len(actual)}"
    for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=False)):
        yield from _structural_differences(expected_item, actual_item, walk.into(f"[{index}]"))


def _value_difference(path: str, expected: JsonValue, actual: JsonValue) -> str:
    long_enough = any(
        isinstance(value, str) and len(value) > DIFFERENCE_VALUE_LIMIT
        for value in (expected, actual)
    )
    if long_enough and isinstance(expected, str) and isinstance(actual, str):
        return _text_difference(path, expected, actual)
    return f"{path}: expected {_shown(expected)}, got {_shown(actual)}"


def _text_difference(path: str, expected: str, actual: str) -> str:
    """Two long texts, by where they first differ, since what a report cuts is what matters."""
    position = _first_difference(expected, actual)
    wanted, found = _excerpt(expected, position), _excerpt(actual, position)
    return f"{path}: differs at character {position}: expected {wanted}, got {found}"


def _first_difference(left: str, right: str) -> int:
    pairs = enumerate(zip(left, right, strict=False))
    return next((index for index, (a, b) in pairs if a != b), min(len(left), len(right)))


def _excerpt(text: str, position: int) -> str:
    start, end = max(position - TEXT_CONTEXT, 0), position + TEXT_CONTEXT
    prefix = ELLIPSIS if start > 0 else ""
    suffix = ELLIPSIS if end < len(text) else ""
    return json_text(f"{prefix}{text[start:end]}{suffix}")


def _shown(value: JsonValue) -> str:
    return value_text(value, DIFFERENCE_VALUE_LIMIT)
