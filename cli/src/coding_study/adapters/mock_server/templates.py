"""Run-time values in a response: `{{request.body.model}}`, `{{seq}}`, `{{len(...)}}`
(docs/specs/service-projects.md#run-time-values).

Field references and three functions, and nothing else: no expressions, no scripting. Anything else
in braces is sent as written; S20 refuses it before any stack starts, by the same grammar, in
`domain/mock_configs.py`. `tests/mock_template_table.py` holds the two to one table.
"""

import json
import re
from collections.abc import Callable, Mapping, Sized
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from .json_values import MISSING, value_at

if TYPE_CHECKING:
    from .matching import MockRequest

_REFERENCE = (
    r"(?:request\.(?:method|path|body(?:\.[A-Za-z0-9_-]+)*"
    r"|query\.[A-Za-z0-9_-]+|headers\.[A-Za-z0-9-]+)|seq)"
)
VALUE = re.compile(
    rf"\{{\{{(?:(?P<function>len|words|json)\((?P<argument>{_REFERENCE})\)"
    rf"|(?P<reference>{_REFERENCE}))\}}\}}"
)
_BODY = "request.body"
_QUERY = "request.query."
_HEADERS = "request.headers."


@dataclass(frozen=True)
class RequestValues:
    """What a response can name: the request it answers, and its number since the last reset."""

    request: "MockRequest"
    seq: int


def has_values(value: object) -> bool:
    """Whether a text, or any text in a JSON value, names a run-time value."""
    if isinstance(value, str):
        return VALUE.search(value) is not None
    if isinstance(value, list):
        return any(has_values(item) for item in cast(list[object], value))
    if isinstance(value, dict):
        return any(has_values(item) for item in cast(dict[str, object], value).values())
    return False


def rendered_text(text: str, values: RequestValues) -> str:
    """Each value as text: a string as it is, anything else as compact JSON, a missing field as
    nothing."""
    return VALUE.sub(lambda found: _as_text(_evaluated(found, values)), text)


def rendered_json(value: object, values: RequestValues) -> object:
    """A string that is one value and nothing else takes that value, of its own JSON type, a missing
    field as null; any other string is filled in as text. Keys stay as written."""
    if isinstance(value, str):
        whole = VALUE.fullmatch(value)
        if whole is None:
            return rendered_text(value, values)
        found = _evaluated(whole, values)
        return None if found is MISSING else found
    if isinstance(value, list):
        return [rendered_json(item, values) for item in cast(list[object], value)]
    if isinstance(value, dict):
        fields = cast(dict[str, object], value)
        return {name: rendered_json(item, values) for name, item in fields.items()}
    return value


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _evaluated(found: re.Match[str], values: RequestValues) -> object:
    function = found["function"]
    if function is None:
        return _referenced(found["reference"], values)
    return _FUNCTIONS[function](_referenced(found["argument"], values))


def _referenced(reference: str, values: RequestValues) -> object:
    request = values.request
    if reference == "seq":
        return values.seq
    if reference == "request.method":
        return request.method
    if reference == "request.path":
        return request.path
    if reference.startswith(_QUERY):
        given = request.query.get(reference.removeprefix(_QUERY), ())
        return given[0] if given else MISSING
    if reference.startswith(_HEADERS):
        return request.headers.get(reference.removeprefix(_HEADERS).lower(), MISSING)
    path = reference.removeprefix(_BODY).removeprefix(".")
    return value_at(request.json_body, tuple(path.split(".")) if path else ())


def _as_text(value: object) -> str:
    if value is MISSING:
        return ""
    return value if isinstance(value, str) else compact_json(value)


def _length(value: object) -> int:
    """A text's characters, a list's elements or an object's fields; 0 for anything else."""
    return len(cast(Sized, value)) if isinstance(value, str | list | dict) else 0


def _words(value: object) -> int:
    """The whitespace-separated words of every text in a value, at any depth; keys do not count."""
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, list):
        return sum(_words(item) for item in cast(list[object], value))
    if isinstance(value, dict):
        return sum(_words(item) for item in cast(dict[str, object], value).values())
    return 0


def _json_text(value: object) -> str:
    return compact_json(None if value is MISSING else value)


_FUNCTIONS: Mapping[str, Callable[[object], object]] = {
    "len": _length,
    "words": _words,
    "json": _json_text,
}
