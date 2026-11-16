"""What the model port carries (docs/specs/ai.md#providers, #http and #errors)."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.ai import ModelRef


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """One request to a provider's model: the task's instructions as the system prompt and the rest
    as one user message."""

    model: ModelRef
    instructions: str
    message: str
    max_output_tokens: int
    """The task's output limit (docs/specs/ai.md#routing)."""
    deadline_s: float
    """The whole request, past which it fails as `timeout`."""
    schema: Mapping[str, object] | None = None
    """A JSON schema of the portable subset the reply must follow; None for free text."""
    schema_name: str = "reply"
    """The name the providers that want one give the schema."""

    def __post_init__(self) -> None:
        if self.max_output_tokens < 1 or self.deadline_s <= 0:
            raise ValueError("a request needs an output limit and a deadline")


@dataclass(frozen=True, slots=True)
class Usage:
    """The tokens a provider reported: input tokens, cached ones included, and output tokens,
    reasoning ones included."""

    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None
    """Only what the provider reported, in US dollars; `cstudy` holds no prices."""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Ending(StrEnum):
    """How a reply ended."""

    COMPLETE = "complete"
    LENGTH = "length"
    """The output limit cut the reply."""
    REFUSED = "refused"
    """The provider declined to answer: a refusal, or a safety stop."""


@dataclass(frozen=True, slots=True)
class ModelReply:
    ending: Ending
    text: str = ""
    """What the model wrote; empty when it refused."""
    data: Mapping[str, object] | None = None
    """The parsed JSON object when the request named a schema and the reply is complete."""
    usage: Usage | None = None
    """None when the provider reported none."""


class ProviderErrorKind(StrEnum):
    """docs/specs/ai.md#errors; `ai_calls.error` stores the value."""

    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    MODEL = "model"
    REFUSED = "refused"
    LENGTH = "length"
    NETWORK = "network"
    TIMEOUT = "timeout"
    PROVIDER = "provider"
    INVALID_REPLY = "invalid_reply"


class ProviderError(Exception):
    """A request that failed (exit code 4). The text names the provider and never holds the key."""

    def __init__(self, kind: ProviderErrorKind, message: str, usage: Usage | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.usage = usage
        """The tokens the provider reported before it failed, if any: the request still counts."""
