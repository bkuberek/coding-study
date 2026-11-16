"""The AI preview's vocabulary (docs/specs/ai.md): providers, models, routing and keys."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from coding_study.domain.errors import UsageError


class Provider(StrEnum):
    """In the order `credentials.toml` and the messages list them (docs/specs/ai.md#keys)."""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"
    OPENROUTER = "openrouter"


class Routing(StrEnum):
    """`ai.routing` (docs/specs/ai.md#settings)."""

    FIXED = "fixed"
    """Every task uses `ai.model`."""
    AUTO = "auto"
    """Each task uses its tier."""


class Tier(StrEnum):
    """Auto routing's two tiers: `ai.fast` and `ai.strong`."""

    FAST = "fast"
    STRONG = "strong"


class AiTask(StrEnum):
    """What a request is for; its value is the purpose that consents and requests record
    (docs/specs/ai.md#routing). Later milestones add theirs."""

    REVIEW = "review"
    CHECK = "check"


AI_OFF = "AI is off: turn it on with ai.enabled = true (cstudy config edit) or in Settings"
"""What a task refused because `ai.enabled` is false says (docs/specs/ai.md#routing)."""

MODEL_SHAPE = "expected provider:model, such as anthropic:<model id>"


@dataclass(frozen=True, slots=True)
class ModelRef:
    """`<provider>:<model id>` (docs/specs/ai.md#settings). `cstudy` names no model of its own."""

    provider: Provider
    model_id: str
    """What the provider calls the model; it may hold more colons and slashes."""

    @classmethod
    def parse(cls, text: str) -> Self:
        """Splits at the first colon. Raises ValueError with the config key's issue, without the
        key's name."""
        provider_name, colon, model_id = text.partition(":")
        if not colon:
            raise ValueError(MODEL_SHAPE)
        if provider_name not in Provider:
            known = ", ".join(Provider)
            raise ValueError(f'unknown provider "{provider_name}"; use one of {known}')
        if not model_id:
            raise ValueError(f'no model id after "{provider_name}:"')
        if any(character.isspace() or not character.isprintable() for character in model_id):
            raise ValueError("a model id has no spaces")
        return cls(Provider(provider_name), model_id)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model_id}"


KEY_SHAPE = "a key is one line of text with no spaces"
KEY_TEXT = "<key>"
"""What a key prints as: its value reaches only a provider's request header."""


class ApiKey:
    """A provider key (docs/specs/ai.md#keys). Its text is `<key>` in `repr`, `str`, `format`,
    errors and logs, in any container; only an adapter calls `reveal` to put it in a header."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        """Raises UsageError for an empty value or one with whitespace or control characters."""
        if not value or any(c.isspace() or not c.isprintable() for c in value):
            raise UsageError(KEY_SHAPE)
        self._value = value

    def reveal(self) -> str:
        return self._value

    def scrub(self, text: str) -> str:
        """`text` with the key replaced by `<key>`, for text a provider sent back."""
        return text.replace(self._value, KEY_TEXT)

    def __repr__(self) -> str:
        return KEY_TEXT

    def __str__(self) -> str:
        return KEY_TEXT

    def __format__(self, format_spec: str) -> str:
        return KEY_TEXT

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ApiKey) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
