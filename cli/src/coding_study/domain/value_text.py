"""Canonical JSON values as text in reports (docs/specs/problem-format.md#comparators)."""

import json

from coding_study.domain.cases import JsonValue
from coding_study.domain.type_dsl import ArrayType, ListType, Scalar, ScalarType, ValueType

MAX_VALUE_TEXT = 200
"""Failure reports truncate input, expected and actual values to this many characters."""
ELLIPSIS = "..."
UNQUOTED_SCALARS = frozenset({Scalar.DECIMAL, Scalar.DATE})
"""Scalars whose JSON strings `display_text` shows without quotes."""


def json_text(value: JsonValue) -> str:
    """`value` as compact JSON: `[1, 2]`, `null`, `"a"`."""
    return json.dumps(value, ensure_ascii=False)


def display_text(value: JsonValue, declared: ValueType | None) -> str:
    """`json_text(value)`, except that the strings of `decimal` and `date` values lose their
    quotes, as in `[2500.5, 2026-01-01]`. A value that does not fit `declared` is plain JSON.
    """
    match declared:
        case ScalarType(scalar) if scalar in UNQUOTED_SCALARS and isinstance(value, str):
            return value
        case ArrayType(element) | ListType(element) if isinstance(value, list):
            return "[" + ", ".join(display_text(item, element) for item in value) + "]"
        case _:
            return json_text(value)


def value_text(value: JsonValue, limit: int = MAX_VALUE_TEXT) -> str:
    """`json_text(value)` truncated to `limit` characters."""
    return truncate(json_text(value), limit)


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - len(ELLIPSIS)] + ELLIPSIS
