"""Reading a provider's reply (docs/specs/ai.md#providers and #errors).

A reply is JSON a provider wrote, so every field is checked before it is used: a field of the wrong
shape reads as absent, and a reply that cannot be used is an `invalid_reply` error.
"""

import json
from collections.abc import Sequence
from typing import cast

from coding_study.adapters.ai.http_json import JsonObject
from coding_study.domain.ai import Provider
from coding_study.domain.ai_models import ProviderError, ProviderErrorKind, Usage


def mapping(value: object) -> JsonObject:
    """`value` when it is a JSON object, else an empty one."""
    return cast("JsonObject", value) if isinstance(value, dict) else {}


def items(value: object) -> Sequence[object]:
    """`value` when it is a JSON array, else an empty one."""
    return cast("Sequence[object]", value) if isinstance(value, list) else ()


def count(value: object) -> int:
    """A token count: `value` when it is a non-negative integer, else 0."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def text_of(value: object) -> str:
    return value if isinstance(value, str) else ""


def invalid_reply(provider: Provider, reason: str, usage: Usage | None) -> ProviderError:
    """The error for a reply that cannot be used, which still counts its tokens."""
    return ProviderError(ProviderErrorKind.INVALID_REPLY, f"{provider} {reason}", usage)


def structured(provider: Provider, text: str, usage: Usage | None) -> JsonObject:
    """The JSON object a structured reply holds. Raises ProviderError when the text is not one."""
    try:
        parsed: object = json.loads(text)
    except ValueError:
        raise invalid_reply(provider, "sent a reply that is not JSON", usage) from None
    if not isinstance(parsed, dict):
        raise invalid_reply(provider, "sent a reply that is not a JSON object", usage)
    return cast("JsonObject", parsed)
