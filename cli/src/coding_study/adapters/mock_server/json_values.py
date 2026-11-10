"""A request body read as JSON: whether it holds a subset, and the value at a dotted path.

The grader judges a logged body by the same rules, in `domain/http_bodies.py`. This folder runs
alone, on the standard library, so it cannot import that module; `tests/json_subset_table.py` holds
the two to one table.
"""

import json
from typing import NoReturn, cast


class _Missing:
    """A value that is not there: a field the body lacks, or a body that is not JSON."""

    def __repr__(self) -> str:
        return "MISSING"


MISSING = _Missing()


def parsed(body: bytes) -> object:
    """The body as JSON, or MISSING when it is empty, not UTF-8 or not JSON."""
    try:
        return json.loads(body.decode("utf-8"), parse_constant=_refused_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return MISSING


def contains(actual: object, subset: object) -> bool:
    """A mapping holds each field of the subset's, at any depth; a list holds as many elements as
    the subset's, each holding its own; anything else is equal, where `true` is not `1`."""
    if isinstance(subset, dict):
        if not isinstance(actual, dict):
            return False
        held = cast(dict[str, object], actual)
        fields = cast(dict[str, object], subset)
        return all(name in held and contains(held[name], value) for name, value in fields.items())
    if isinstance(subset, list):
        elements = cast(list[object], subset)
        return (
            isinstance(actual, list)
            and len(cast(list[object], actual)) == len(elements)
            and all(map(contains, cast(list[object], actual), elements))
        )
    return _same_kind(actual, subset) and actual == subset


def value_at(value: object, path: tuple[str, ...]) -> object:
    """The value a dotted path names, a number naming a list element; MISSING when there is none."""
    found = value
    for step in path:
        if isinstance(found, dict):
            found = cast(dict[str, object], found).get(step, MISSING)
        elif isinstance(found, list) and step.isdigit():
            elements = cast(list[object], found)
            found = elements[int(step)] if int(step) < len(elements) else MISSING
        else:
            return MISSING
    return found


def _same_kind(left: object, right: object) -> bool:
    """`1` and `1.0` are one number; a boolean is no number."""
    numbers = (int, float)
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool)
    if isinstance(left, numbers) and isinstance(right, numbers):
        return True
    return type(left) is type(right)


def _refused_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not JSON")
