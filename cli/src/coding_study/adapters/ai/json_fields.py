"""Reading a provider's JSON reply field by field, for the adapters (docs/specs/ai.md#providers)."""

import json
from collections.abc import Mapping
from typing import cast

from coding_study.domain.ai import Provider
from coding_study.domain.ai_models import ProviderError, ProviderErrorKind, Usage

type JsonObject = Mapping[str, object]


def mapping(value: object) -> JsonObject:
    """`value` when it is a JSON object, else an empty one."""
    return cast("JsonObject", value) if isinstance(value, dict) else {}


def items(value: object) -> list[object]:
    """`value` when it is a JSON array, else an empty list."""
    return cast("list[object]", value) if isinstance(value, list) else []


def text(value: object) -> str:
    """`value` when it is a string, else an empty string."""
    return value if isinstance(value, str) else ""


def count(value: object) -> int:
    """A token count: `value` when it is a whole number, else 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def amount(value: object) -> float | None:
    """A number of dollars, or None when `value` is no number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def parse_object(reply_text: str) -> JsonObject | None:
    """The JSON object a model wrote, or None when the text is not one."""
    try:
        parsed: object = json.loads(reply_text)
    except ValueError:
        return None
    return cast("JsonObject", parsed) if isinstance(parsed, dict) else None


def invalid_reply(provider: Provider, reason: str, usage: Usage | None = None) -> ProviderError:
    """A reply that cannot be read, which still counts the tokens it reported."""
    message = f"{provider} sent a reply that cstudy cannot read: {reason}"
    return ProviderError(ProviderErrorKind.INVALID_REPLY, message, usage)
