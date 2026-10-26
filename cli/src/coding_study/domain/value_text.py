"""Canonical JSON values as text in reports (docs/specs/problem-format.md#comparators)."""

import json

from coding_study.domain.cases import JsonValue

MAX_VALUE_TEXT = 200
"""Failure reports truncate input, expected and actual values to this many characters."""
ELLIPSIS = "..."


def json_text(value: JsonValue) -> str:
    """`value` as compact JSON: `[1, 2]`, `null`, `"a"`."""
    return json.dumps(value, ensure_ascii=False)


def value_text(value: JsonValue, limit: int = MAX_VALUE_TEXT) -> str:
    """`json_text(value)` truncated to `limit` characters."""
    return truncate(json_text(value), limit)


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - len(ELLIPSIS)] + ELLIPSIS
