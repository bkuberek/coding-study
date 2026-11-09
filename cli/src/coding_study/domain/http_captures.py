"""Reading a value out of an answer, for a later step
(docs/specs/service-projects.md#multi-step-cases): its status, a header, a query parameter of a
header that holds a URL, a field of a JSON body, or an attribute of an HTML form or input, which the
standard library's parser reads with its entities unescaped."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from coding_study.domain.cases import JsonValue
from coding_study.domain.http_case import CaptureKind, CaptureSource
from coding_study.domain.http_grading import HttpResponse

QUERY = "query"
FORM_TAG = "form"
INPUT_TAG = "input"
FORM_KEY = "id"
INPUT_KEY = "name"
HEADER_PARTS = 1
HEADER_QUERY_PARTS = 3
ELEMENT_PARTS = 2


class CaptureSyntaxError(ValueError):
    """A capture source that names no place in an answer."""


@dataclass(frozen=True, slots=True)
class Captured:
    value: str | None
    """None when the answer holds nothing there."""
    missing: str = ""
    """Why nothing was found, for a reason that names the place."""


def capture_source(text: str) -> CaptureSource:
    """`status`, `header.<name>`, `header.<name>.query.<parameter>`, `body.<dotted path>`,
    `form.<id>.<attribute>` or `input.<name>.<attribute>`."""
    kind_text, _, rest = text.partition(".")
    try:
        kind = CaptureKind(kind_text)
    except ValueError:
        raise CaptureSyntaxError(f"{text}: starts with none of {', '.join(CaptureKind)}") from None
    path = tuple(rest.split(".")) if rest else ()
    if "" in path or not _well_shaped(kind, path):
        raise CaptureSyntaxError(f"{text}: not a place {kind} can name")
    return CaptureSource(kind, path)


def _well_shaped(kind: CaptureKind, path: tuple[str, ...]) -> bool:
    match kind:
        case CaptureKind.STATUS:
            return not path
        case CaptureKind.HEADER:
            return len(path) == HEADER_PARTS or (
                len(path) == HEADER_QUERY_PARTS and path[1] == QUERY
            )
        case CaptureKind.BODY:
            return bool(path)
        case CaptureKind.FORM | CaptureKind.INPUT:
            return len(path) == ELEMENT_PARTS


def captured(source: CaptureSource, response: HttpResponse) -> Captured:
    match source.kind:
        case CaptureKind.STATUS:
            return Captured(str(response.status))
        case CaptureKind.HEADER:
            return _header(source.path, response.headers)
        case CaptureKind.BODY:
            return _body_field(source.path, response.body)
        case CaptureKind.FORM:
            return _attribute(
                _Element(FORM_TAG, FORM_KEY, source.path[0]), source.path[1], response
            )
        case CaptureKind.INPUT:
            element = _Element(INPUT_TAG, INPUT_KEY, source.path[0])
            return _attribute(element, source.path[1], response)


def _header(path: tuple[str, ...], headers: Mapping[str, str]) -> Captured:
    name = path[0]
    value = headers.get(name.lower())
    if value is None:
        return Captured(None, f"no header {name}")
    if len(path) == HEADER_PARTS:
        return Captured(value)
    parameter = path[2]
    found = parse_qs(urlsplit(value).query, keep_blank_values=True).get(parameter)
    if not found:
        return Captured(None, f"header {name} has no query parameter {parameter}")
    return Captured(found[0])


def _body_field(path: tuple[str, ...], body: bytes) -> Captured:
    try:
        found: JsonValue = json.loads(body)
    except (ValueError, RecursionError):
        return Captured(None, "the body is not JSON")
    for depth, name in enumerate(path):
        step = _child(found, name)
        if step is None:
            where = ".".join(("body", *path[: depth + 1]))
            return Captured(None, f"the body has no {where}")
        found = step[0]
    return Captured(found if isinstance(found, str) else json.dumps(found))


def _child(value: JsonValue, name: str) -> tuple[JsonValue] | None:
    """The member or element `name` names, in a tuple so that a JSON null is found too."""
    if isinstance(value, dict) and name in value:
        return (value[name],)
    if isinstance(value, list) and name.isdigit() and int(name) < len(value):
        return (value[int(name)],)
    return None


@dataclass(frozen=True, slots=True)
class _Element:
    tag: str
    key: str
    """The attribute that names the element: a form's `id`, an input's `name`."""
    wanted: str


def _attribute(element: _Element, attribute: str, response: HttpResponse) -> Captured:
    finder = _ElementFinder(element)
    finder.feed(response.body.decode(errors="replace"))
    finder.close()
    described = f'<{element.tag} {element.key}="{element.wanted}">'
    if finder.found is None:
        return Captured(None, f"the body has no {described}")
    value = finder.found.get(attribute)
    if value is None:
        return Captured(None, f"{described} has no attribute {attribute}")
    return Captured(value)


class _ElementFinder(HTMLParser):
    """The attributes of the first element that matches, with entities unescaped."""

    def __init__(self, element: _Element) -> None:
        super().__init__(convert_charrefs=True)
        self._element = element
        self.found: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.found is not None or tag != self._element.tag:
            return
        attributes = dict(attrs)
        if attributes.get(self._element.key) == self._element.wanted:
            self.found = attributes

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
