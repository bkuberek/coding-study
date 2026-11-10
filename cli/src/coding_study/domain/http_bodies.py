"""A logged request body read as JSON, for the log assertions on what it carried
(docs/specs/service-projects.md#logged-bodies).

The mock server matches a route on a body by the same subset rules, in
`adapters/mock_server/json_values.py`. That folder runs alone, on the standard library, and cannot
import this module; `tests/json_subset_table.py` holds the two to one table.
"""

import json
from typing import NoReturn, cast

PATH_SEPARATOR = "."


class _Missing:
    """A value that is not there: a field the body lacks, or a body that is not JSON."""

    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()


def parsed_body(text: str | None) -> object:
    """The body as JSON, or MISSING when it is empty or not JSON."""
    if not text:
        return MISSING
    try:
        return json.loads(text, parse_constant=_refused_constant)
    except (ValueError, RecursionError):
        return MISSING


def json_contains(actual: object, subset: object) -> bool:
    """A mapping holds each field of the subset's, at any depth; a list holds as many elements as
    the subset's, each holding its own; anything else is equal, where `true` is not `1`."""
    if isinstance(subset, dict):
        if not isinstance(actual, dict):
            return False
        held = cast(dict[str, object], actual)
        fields = cast(dict[str, object], subset)
        return all(
            name in held and json_contains(held[name], value) for name, value in fields.items()
        )
    if isinstance(subset, list):
        elements = cast(list[object], subset)
        return (
            isinstance(actual, list)
            and len(cast(list[object], actual)) == len(elements)
            and all(map(json_contains, cast(list[object], actual), elements))
        )
    return _same_kind(actual, subset) and actual == subset


def value_at(value: object, dotted: str) -> object:
    """The value a dotted path names, a number naming a list element; MISSING when there is none."""
    found = value
    for step in dotted.split(PATH_SEPARATOR):
        if isinstance(found, dict):
            found = cast(dict[str, object], found).get(step, MISSING)
        elif isinstance(found, list) and step.isdigit():
            elements = cast(list[object], found)
            found = elements[int(step)] if int(step) < len(elements) else MISSING
        else:
            return MISSING
    return found


def is_number(value: object) -> bool:
    """A JSON number; a boolean is none."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def canonical_text(value: object) -> str:
    """A value's JSON text with sorted keys and no spaces, so two values compare by what they hold,
    whatever their key order, and `1` is not `1.0` or `true`."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prefix_break(earlier: object, later: object) -> str | None:
    """Why `later` does not start with the whole of `earlier`, both a text or both a list, or None
    when it does. List elements compare by their canonical JSON text."""
    if isinstance(earlier, str) and isinstance(later, str):
        return _text_break(earlier, later)
    if isinstance(earlier, list) and isinstance(later, list):
        return _list_break(cast(list[object], earlier), cast(list[object], later))
    return "it is not the same kind of value"


def _text_break(earlier: str, later: str) -> str | None:
    if later.startswith(earlier):
        return None
    shared = zip(earlier, later, strict=False)
    position = next((index for index, (a, b) in enumerate(shared) if a != b), None)
    return "it is shorter" if position is None else f"it differs at character {position}"


def _list_break(earlier: list[object], later: list[object]) -> str | None:
    for index, element in enumerate(earlier):
        if index >= len(later):
            return "it has fewer elements"
        if canonical_text(element) != canonical_text(later[index]):
            return f"element {index} differs"
    return None


def _same_kind(left: object, right: object) -> bool:
    """`1` and `1.0` are one number; a boolean is no number."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool)
    if is_number(left) and is_number(right):
        return True
    return type(left) is type(right)


def _refused_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not JSON")
