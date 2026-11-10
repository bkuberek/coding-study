"""Which route a request matches and what it answers: pure, with no sockets and no state."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from urllib.parse import parse_qs

from .config import (
    Body,
    ResponseFields,
    Route,
    Scenario,
    StreamChunk,
    StreamCut,
    StreamCutKind,
)
from .json_values import contains, parsed
from .replies import Frame, Reply
from .templates import RequestValues, compact_json, rendered_json, rendered_text

DEFAULT_STATUS = 200
NO_BODY = Body(b"")
NO_HEADERS: Mapping[str, str] = {}
PARAMETER_PREFIX = "{"
CONTENT_TYPE = "content-type"
STREAM_CONTENT_TYPE = "text/event-stream"


@dataclass(frozen=True)
class MockRequest:
    method: str
    path: str
    query: Mapping[str, tuple[str, ...]]
    headers: Mapping[str, str]
    body: bytes

    @cached_property
    def json_body(self) -> object:
        """The body as JSON, read once for every route that asks; MISSING when it is not."""
        return parsed(self.body)


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


def reply_for(route: Route, overrides: ResponseFields | None, values: RequestValues) -> Reply:
    """The route's response with `overrides` applied: a field given replaces the route's whole. A
    route that passes through has no response of its own, so what a scenario leaves out is empty.
    A body that names run-time values takes them from `values`."""
    given = overrides or ResponseFields()
    own = route.response or ResponseFields()
    content = given if _gives_content(given) else own
    body = content.body or NO_BODY
    headers = _first_given((given.headers, own.headers), NO_HEADERS)
    stream = None if content.stream is None else _streamed(content.stream, given.cut, values)
    content_type = body.content_type if stream is None else STREAM_CONTENT_TYPE
    return Reply(
        status=_first_given((given.status, own.status), DEFAULT_STATUS),
        headers=_with_content_type(headers, content_type),
        body=_content(body, values),
        delay_ms=_first_given((given.delay_ms, own.delay_ms), 0),
        stream=stream,
        holds_open=stream is not None and _stalls(given.cut),
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
        headers, lines = _with_content_type(overrides.headers, (body or NO_BODY).content_type), ()
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
        and _body_matches(route, request)
    )


def _body_matches(route: Route, request: MockRequest) -> bool:
    subset, text = route.match_body, route.match_body_contains
    if text is not None and text.encode() not in request.body:
        return False
    return subset is None or contains(request.json_body, subset)


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


def _gives_content(fields: ResponseFields) -> bool:
    """A body and a stream are one field: an override that gives either replaces the route's."""
    return fields.body is not None or fields.stream is not None


def _streamed(
    chunks: tuple[StreamChunk, ...], cut: StreamCut | None, values: RequestValues
) -> tuple[Frame, ...]:
    kept = chunks if cut is None else chunks[: cut.after_chunks]
    return tuple(_frame(chunk, values) for chunk in kept)


def _frame(chunk: StreamChunk, values: RequestValues) -> Frame:
    """A server-sent event: its name, then a `data` line per line of its data, then a blank line."""
    if chunk.raw is not None:
        return Frame(rendered_text(chunk.raw, values).encode(), chunk.after_ms)
    named = [f"event: {chunk.event}"] if chunk.event is not None else []
    data = rendered_text(chunk.data or "", values).split("\n")
    lines = [*named, *(f"data: {line}" for line in data)]
    return Frame(("\n".join(lines) + "\n\n").encode(), chunk.after_ms)


def _stalls(cut: StreamCut | None) -> bool:
    return cut is not None and cut.kind is StreamCutKind.STALL


def _content(body: Body, values: RequestValues) -> bytes:
    template = body.template
    if template is None:
        return body.content
    if isinstance(template, str):
        return rendered_text(template, values).encode()
    return compact_json(rendered_json(template, values)).encode()


def _first_given[T](candidates: tuple[T | None, T | None], default: T) -> T:
    return next((value for value in candidates if value is not None), default)


def _with_content_type(headers: Mapping[str, str], content_type: str | None) -> Mapping[str, str]:
    if content_type is None or any(name.lower() == CONTENT_TYPE for name in headers):
        return headers
    return {**headers, "Content-Type": content_type}
