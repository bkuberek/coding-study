"""Judging what an app answered over HTTP (docs/specs/service-projects.md#hidden-http-case).

A failure's reason names what differs, by its path in the body, so that it stays useful where a
report cuts the expected and actual values short.
"""

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import islice, pairwise
from typing import NoReturn, cast
from urllib.parse import parse_qs

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Expected, FunctionInput, JsonValue
from coding_study.domain.comparators import Comparator, Mismatch, comparator_for
from coding_study.domain.http_bodies import (
    MISSING,
    canonical_text,
    is_number,
    json_contains,
    parsed_body,
    prefix_break,
    value_at,
)
from coding_study.domain.http_case import ExpectedStatus, HttpExpected, LogAssertion, SameBody
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
OVERFLOWED = (
    "the mock server's log overflowed, so this cannot be judged: "
    "send fewer or smaller requests in one case"
)
CUT_BODY = "a logged body was cut at the log's limit, so its form cannot be judged"
CUT_JSON_BODY = "a logged body was cut at the log's limit, so its JSON cannot be judged"
FILTER_VALUE_LIMIT = 40
"""How much of a value a log assertion's label shows: a token is long, and its start names it."""
NANOSECONDS_PER_MILLISECOND = 1_000_000

_MULTISET_COMPARATORS = frozenset({ComparatorType.UNORDERED, ComparatorType.UNORDERED_NESTED})
HTTP_COMPARATORS = frozenset({ComparatorType.EXACT, ComparatorType.FLOAT, *_MULTISET_COMPARATORS})
"""What can judge a response body: `checker` and `ops` need a runner's output."""
_NO_INPUT = FunctionInput({})


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    """By lowercase name; a repeated header is joined with `, `."""
    body: bytes
    duration_ns: int = 0
    """From sending the request to the end of the response."""
    first_byte_ns: int = 0
    """From writing the request to the first byte of the body, or to the end of an empty one: what
    tells a stream from an answer held back until it is whole. With redirects followed, the last
    request's."""


class ExchangeFailure(StrEnum):
    """Why a request brought back no HTTP answer to judge."""

    TIMED_OUT = "timed out"
    REFUSED = "connection refused"
    DROPPED = "connection dropped"
    NOT_HTTP = "not HTTP"
    TOO_LARGE = "too large"


@dataclass(frozen=True, slots=True)
class ExchangeFailed:
    failure: ExchangeFailure
    detail: str
    """A sentence for a learner: what was asked of whom, and what happened."""
    duration_ns: int = 0


@dataclass(frozen=True, slots=True)
class LoggedRequest:
    """One entry of a mock server's request log (docs/specs/service-projects.md#request-log)."""

    route: str | None
    received_ms: int
    responded_ms: int | None
    """None while the request is still being answered."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    """By lowercase name."""
    body: str | None = None
    """As text; None when it was empty or not UTF-8."""
    truncated: bool = False
    """The body was cut at the log's limit."""


@dataclass(frozen=True, slots=True)
class MockLog:
    entries: tuple[LoggedRequest, ...] = ()
    dropped: int = 0
    """Requests past the log's limit: answered, counted and not kept."""


@dataclass(frozen=True, slots=True)
class Answer:
    """The last answer a case judged, with what it expected, as a report shows them."""

    response: HttpResponse
    expected: HttpExpected | None = None


def answered_verdict(case: RunnableCase, answer: Answer, failures: Sequence[str]) -> CaseVerdict:
    """PASS, or FAIL with every reason found."""
    outcome = answer_outcome(answer.response, answer.expected)
    if failures:
        return CaseVerdict(
            case, CaseStatus.FAIL, outcome, Mismatch(FAILURE_SEPARATOR.join(failures))
        )
    return CaseVerdict(case, CaseStatus.PASS, outcome)


def answer_outcome(response: HttpResponse, expected: HttpExpected | None) -> Returned:
    """The answer as a report shows it: its status, its body, and the headers the case lists."""
    output: dict[str, JsonValue] = {
        "status": response.status,
        BODY: _shown_body(response.body, expected.body if expected is not None else None),
    }
    if expected is not None and expected.headers:
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
    if not status_matches(expected.status, response.status):
        return (_status_failure(expected.status, response.status),)
    return (
        *_header_failures(response.headers, expected.headers),
        *_body_failures(response.body, expected.body, comparator),
        *_first_byte_failure(response.first_byte_ns, expected.first_byte_ms_max),
    )


def status_matches(expected: ExpectedStatus, actual: int) -> bool:
    """A class such as `"4xx"` holds every status of its hundred."""
    if isinstance(expected, int):
        return actual == expected
    return str(actual)[:1] == expected[:1]


def _first_byte_failure(first_byte_ns: int, limit_ms: int | None) -> tuple[str, ...]:
    """Whole milliseconds, rounded up, so that a byte a fraction past the limit reads as past it."""
    if limit_ms is None:
        return ()
    waited_ms = -(-first_byte_ns // NANOSECONDS_PER_MILLISECOND)
    if waited_ms <= limit_ms:
        return ()
    return (f"first body byte after {waited_ms} ms, expected within {limit_ms} ms",)


def _status_failure(expected: ExpectedStatus, actual: int) -> str:
    if isinstance(expected, int):
        return f"status: expected {expected}, got {actual}"
    return f"expected a {expected} status, got {actual}"


def log_failures(
    assertion: LogAssertion, log: MockLog, reference: MockLog | None = None
) -> tuple[str, ...]:
    """Why the log breaks `assertion`; `reference` is the log its `body_same_as` names. What a full
    log dropped is counted but not kept: it says how many came and nothing of which route they
    took, what they carried or when, so only a count of the whole mock server can be judged then."""
    label = _log_label(assertion)
    if log.dropped > 0 and _narrows(assertion):
        return (f"{label}: {OVERFLOWED}",)
    on_route = tuple(
        entry for entry in log.entries if assertion.route is None or entry.route == assertion.route
    )
    try:
        _refuse_cut_bodies(assertion, on_route)
        same = _reference_texts(assertion.body_same_as, reference or MockLog())
    except _UnjudgedError as unjudged:
        return (f"{label}: {unjudged}",)
    matching = tuple(entry for entry in on_route if _carries(entry, assertion, same))
    problems = (
        *_count_failures(assertion, len(matching) + log.dropped),
        *_gap_failure(assertion, matching),
        *_prefix_failure(assertion.body_prefix_stable, matching),
    )
    return tuple(f"{label}: {problem}" for problem in problems)


class _UnjudgedError(Exception):
    """An assertion the log cannot judge; the message says why."""


def _narrows(assertion: LogAssertion) -> bool:
    """Whether the assertion needs to know which requests came, not only how many."""
    return (
        assertion.route is not None
        or assertion.min_gap_ms is not None
        or bool(assertion.headers or assertion.form)
        or _reads_json(assertion)
    )


def _reads_json(assertion: LogAssertion) -> bool:
    return (
        assertion.body is not None
        or bool(assertion.body_max)
        or assertion.body_same_as is not None
        or assertion.body_prefix_stable is not None
    )


def _refuse_cut_bodies(assertion: LogAssertion, entries: tuple[LoggedRequest, ...]) -> None:
    if not any(entry.truncated for entry in entries):
        return
    if assertion.form:
        raise _UnjudgedError(CUT_BODY)
    if _reads_json(assertion):
        raise _UnjudgedError(CUT_JSON_BODY)


def _reference_texts(same: SameBody | None, reference: MockLog) -> Mapping[str, str]:
    """The canonical JSON text of each field `same` names, in the first request its route logged."""
    if same is None:
        return {}
    named = f"{same.mock} {same.route}" if same.route else same.mock
    first = next(
        (entry for entry in reference.entries if same.route is None or entry.route == same.route),
        None,
    )
    if first is None:
        raise _UnjudgedError(f"{named} logged no request to compare with")
    if first.truncated:
        raise _UnjudgedError(f"{named}: {CUT_JSON_BODY}")
    body = parsed_body(first.body)
    texts: dict[str, str] = {}
    for path in same.fields:
        value = value_at(body, path)
        if value is MISSING:
            raise _UnjudgedError(f"{named} logged a first request with no body {path}")
        texts[path] = canonical_text(value)
    return texts


def _log_label(assertion: LogAssertion) -> str:
    label = f"{assertion.mock} {assertion.route}" if assertion.route else assertion.mock
    carried = [
        *(f"header {name}={_short(value)}" for name, value in assertion.headers.items()),
        *(f"form {name}={_short(value)}" for name, value in assertion.form.items()),
        *_body_labels(assertion),
    ]
    return f"{label} with {', '.join(carried)}" if carried else label


def _body_labels(assertion: LogAssertion) -> Iterator[str]:
    if assertion.body is not None:
        yield f"body {_short(dict(assertion.body))}"
    for path, maximum in assertion.body_max.items():
        yield f"body {path} at most {maximum:g}"
    same = assertion.body_same_as
    if same is not None:
        named = f"{same.mock} {same.route}" if same.route else same.mock
        yield f"body {', '.join(same.fields)} the same as {named}"


def _short(value: JsonValue) -> str:
    return value_text(value, FILTER_VALUE_LIMIT)


def _carries(entry: LoggedRequest, assertion: LogAssertion, same: Mapping[str, str]) -> bool:
    """Whether the request carried every header, form field and JSON body field the assertion
    names; `same` holds what `body_same_as` asks for, as canonical JSON text."""
    headers_match = all(
        entry.headers.get(name.lower()) == value for name, value in assertion.headers.items()
    )
    if not headers_match:
        return False
    if assertion.form:
        fields = parse_qs(entry.body or "", keep_blank_values=True)
        if not all(value in fields.get(name, ()) for name, value in assertion.form.items()):
            return False
    return not _reads_json(assertion) or _carries_json(parsed_body(entry.body), assertion, same)


def _carries_json(body: object, assertion: LogAssertion, same: Mapping[str, str]) -> bool:
    if assertion.body is not None and not json_contains(body, dict(assertion.body)):
        return False
    for path, maximum in assertion.body_max.items():
        value = value_at(body, path)
        if not is_number(value) or cast(float, value) > maximum:
            return False
    return all(_holds_the_same(body, path, text) for path, text in same.items())


def _holds_the_same(body: object, path: str, text: str) -> bool:
    value = value_at(body, path)
    return value is not MISSING and canonical_text(value) == text


def _prefix_failure(path: str | None, entries: tuple[LoggedRequest, ...]) -> tuple[str, ...]:
    """The first request whose value at `path` does not start with the previous one's whole."""
    if path is None:
        return ()
    values = [value_at(parsed_body(entry.body), path) for entry in entries]
    for number, value in enumerate(values, start=1):
        if value is MISSING:
            return (f"body {path} of request {number} is missing",)
        if not isinstance(value, str | list):
            return (f"body {path} of request {number} is neither a text nor a list",)
    for number, (earlier, later) in enumerate(pairwise(values), start=1):
        broken = prefix_break(earlier, later)
        if broken is not None:
            wanted = f"body {path} of request {number + 1} does not start with request {number}'s"
            return (f"{wanted}: {broken}",)
    return ()


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
