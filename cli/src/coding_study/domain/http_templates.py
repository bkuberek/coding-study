"""`{{name}}` in a step's texts: the one template syntax of a multi-step case
(docs/specs/service-projects.md#multi-step-cases).

A name is a value an earlier step captured, or one a flow's `with` gives. Nothing else is
evaluated: no expressions, no filters, no escapes. A value goes in as it is, so a path or a header
holds exactly what was captured, and a query value is encoded as any query value is.
"""

import json
import re
from collections.abc import Iterator, Mapping
from urllib.parse import urlencode

from coding_study.domain.cases import Expected, JsonValue
from coding_study.domain.http_case import (
    FormBody,
    HttpExpected,
    HttpRequest,
    JsonBody,
    LogAssertion,
    QueryValue,
    RequestTemplate,
    TemplateBody,
    TextBody,
)
from coding_study.domain.http_origins import is_absolute, split_url

PLACEHOLDER = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")
OPENING = "{{"
CONTENT_TYPE = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


class MissingValueError(Exception):
    """A text names a value that no step captured."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class UnreachableUrlError(Exception):
    """An absolute URL the grader cannot send: not plain `http`, or with no name."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


def placeholder_names(text: str) -> tuple[str, ...]:
    return tuple(PLACEHOLDER.findall(text))


def malformed_placeholder(text: str) -> str | None:
    """The first `{{` that opens no `{{name}}`, from there to the end of the text, or None."""
    position = text.find(OPENING)
    while position != -1:
        placeholder = PLACEHOLDER.match(text, position)
        if placeholder is None:
            return text[position:]
        position = text.find(OPENING, placeholder.end())
    return None


def filled(text: str, values: Mapping[str, str]) -> str:
    """Raises MissingValueError for a name `values` lacks."""

    def value_of(found: re.Match[str]) -> str:
        name = found[1]
        if name not in values:
            raise MissingValueError(name)
        return values[name]

    return PLACEHOLDER.sub(value_of, text)


def bound(text: str, bindings: Mapping[str, str]) -> str:
    """`text` with the names `bindings` gives replaced, and every other name left for later."""
    return PLACEHOLDER.sub(lambda found: bindings.get(found[1], found[0]), text)


def filled_json(value: JsonValue, values: Mapping[str, str]) -> JsonValue:
    """Fills the strings of a JSON value; its keys and structure stay as they are."""
    if isinstance(value, str):
        return filled(value, values)
    if isinstance(value, list):
        return [filled_json(item, values) for item in value]
    if isinstance(value, dict):
        return {key: filled_json(item, values) for key, item in value.items()}
    return value


def json_texts(value: JsonValue) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from json_texts(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from json_texts(item)


def request_texts(template: RequestTemplate) -> Iterator[str]:
    """Every text of a request that may name a value."""
    yield template.target
    for value in template.query.values():
        yield from (value,) if isinstance(value, str) else value
    yield from template.headers.values()
    match template.body:
        case JsonBody(value):
            yield from json_texts(value)
        case FormBody(fields):
            yield from fields.values()
        case TextBody(text):
            yield text
        case None:
            return


def expected_texts(expected: HttpExpected | None) -> Iterator[str]:
    if expected is None:
        return
    yield from expected.headers.values()
    if expected.body is not None:
        yield from json_texts(expected.body.value)


def rendered_request(template: RequestTemplate, values: Mapping[str, str]) -> HttpRequest:
    """Raises MissingValueError, or UnreachableUrlError for an absolute URL the grader cannot
    send."""
    target = filled(template.target, values)
    origin, path = _origin_and_path(target)
    headers = {name: filled(value, values) for name, value in template.headers.items()}
    body, content_type = _body(template.body, values)
    if content_type is not None and not _names(headers, CONTENT_TYPE):
        headers[CONTENT_TYPE] = content_type
    return HttpRequest(
        method=template.method,
        path=path,
        query={name: _filled_query(value, values) for name, value in template.query.items()},
        headers=headers,
        body=body,
        origin=origin,
        jar=template.jar,
        follow_redirects=template.follow_redirects,
    )


def rendered_expected(expected: HttpExpected, values: Mapping[str, str]) -> HttpExpected:
    body = expected.body
    return HttpExpected(
        status=expected.status,
        body=Expected(filled_json(body.value, values)) if body is not None else None,
        headers={name: filled(value, values) for name, value in expected.headers.items()},
    )


def rendered_assertion(assertion: LogAssertion, values: Mapping[str, str]) -> LogAssertion:
    return LogAssertion(
        mock=assertion.mock,
        route=assertion.route,
        count=assertion.count,
        min_count=assertion.min_count,
        max_count=assertion.max_count,
        min_gap_ms=assertion.min_gap_ms,
        headers={name: filled(value, values) for name, value in assertion.headers.items()},
        form={name: filled(value, values) for name, value in assertion.form.items()},
    )


def _origin_and_path(target: str) -> tuple[str | None, str]:
    if not is_absolute(target):
        return None, target
    split = split_url(target)
    if split is None:
        raise UnreachableUrlError(target)
    return split


def _filled_query(value: QueryValue, values: Mapping[str, str]) -> QueryValue:
    if isinstance(value, str):
        return filled(value, values)
    return tuple(filled(item, values) for item in value)


def _body(body: TemplateBody | None, values: Mapping[str, str]) -> tuple[bytes | None, str | None]:
    match body:
        case JsonBody(value):
            return json.dumps(filled_json(value, values)).encode(), JSON_CONTENT_TYPE
        case FormBody(fields):
            encoded = urlencode({name: filled(text, values) for name, text in fields.items()})
            return encoded.encode(), FORM_CONTENT_TYPE
        case TextBody(text):
            return filled(text, values).encode(), None
        case None:
            return None, None


def _names(headers: Mapping[str, str], wanted: str) -> bool:
    return any(name.lower() == wanted.lower() for name in headers)
