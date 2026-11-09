"""Which route a request matches and what it answers: pure, with no sockets and no state."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import parse_qs

from .config import Body, ResponseFields, Route, Scenario
from .replies import Reply

DEFAULT_STATUS = 200
NO_BODY = Body(b"")
NO_HEADERS: Mapping[str, str] = {}
PARAMETER_PREFIX = "{"
CONTENT_TYPE = "content-type"


@dataclass(frozen=True)
class MockRequest:
    method: str
    path: str
    query: Mapping[str, tuple[str, ...]]
    headers: Mapping[str, str]
    body: bytes


def parse_target(target: str) -> tuple[str, dict[str, tuple[str, ...]]]:
    """The path and query of a request line's target. A blank value counts as a value."""
    path, _, query = target.partition("?")
    parsed = parse_qs(query, keep_blank_values=True)
    return path, {name: tuple(values) for name, values in parsed.items()}


def find_route(routes: Sequence[Route], request: MockRequest) -> Route | None:
    """The first route that matches, in the order the config lists them."""
    return next((route for route in routes if _matches(route, request)), None)


def scenario_applies(scenario: Scenario, route: Route) -> bool:
    return scenario.route_id is None or scenario.route_id == route.id


def scenario_entry(scenario: Scenario, position: int) -> ResponseFields:
    """The entry for the request at `position`; the last entry repeats."""
    return scenario.entries[min(position, len(scenario.entries) - 1)]


def reply_for(route: Route, overrides: ResponseFields | None) -> Reply:
    """The route's response with `overrides` applied: a field given replaces the route's whole. A
    route that passes through has no response of its own, so what a scenario leaves out is empty."""
    given = overrides or ResponseFields()
    own = route.response or ResponseFields()
    body = _first_given((given.body, own.body), NO_BODY)
    headers = _first_given((given.headers, own.headers), NO_HEADERS)
    return Reply(
        status=_first_given((given.status, own.status), DEFAULT_STATUS),
        headers=_with_content_type(headers, body),
        body=body.content,
        delay_ms=_first_given((given.delay_ms, own.delay_ms), 0),
    )


def passes_through(route: Route, overrides: ResponseFields | None) -> bool:
    """A route without a response asks its upstream, unless a scenario gives a status, which
    answers by itself: an outage on a token route must not spend the code at the provider."""
    return route.response is None and (overrides is None or overrides.status is None)


def over_upstream(answer: Reply, overrides: ResponseFields | None) -> Reply:
    """The upstream's answer, with each field a scenario gives in place of the upstream's."""
    if overrides is None:
        return answer
    body = overrides.body
    if overrides.headers is None:
        headers, lines = answer.headers, answer.header_lines
    else:
        headers, lines = _with_content_type(overrides.headers, body or NO_BODY), ()
    return Reply(
        status=answer.status,
        headers=headers,
        body=answer.body if body is None else body.content,
        delay_ms=answer.delay_ms,
        header_lines=lines,
    )


def _matches(route: Route, request: MockRequest) -> bool:
    return (
        route.method == request.method
        and _path_matches(route.path, request.path)
        and _query_matches(route.query, request.query)
    )


def _path_matches(pattern: str, path: str) -> bool:
    pattern_segments = pattern.split("/")
    path_segments = path.split("/")
    return len(pattern_segments) == len(path_segments) and all(
        map(_segment_matches, pattern_segments, path_segments)
    )


def _segment_matches(pattern: str, segment: str) -> bool:
    if pattern.startswith(PARAMETER_PREFIX):
        return segment != ""
    return pattern == segment


def _query_matches(expected: Mapping[str, str], actual: Mapping[str, tuple[str, ...]]) -> bool:
    return all(value in actual.get(name, ()) for name, value in expected.items())


def _first_given[T](candidates: tuple[T | None, T | None], default: T) -> T:
    return next((value for value in candidates if value is not None), default)


def _with_content_type(headers: Mapping[str, str], body: Body) -> Mapping[str, str]:
    if body.content_type is None or any(name.lower() == CONTENT_TYPE for name in headers):
        return headers
    return {**headers, "Content-Type": body.content_type}
