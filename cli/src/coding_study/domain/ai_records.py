"""What the AI preview stores in `progress.db` (docs/specs/ai.md#records-and-progress)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from coding_study.domain.ai import AiTask, Provider, Tier
from coding_study.domain.ai_models import ProviderErrorKind

REVIEW_FORMAT = 1
"""The AI review record's format; a later format is a new value (docs/specs/ai.md#the-record)."""


@dataclass(frozen=True, slots=True)
class Consent:
    """Agreement to send to a provider's model for a purpose; one `ai_consents` row, this
    workspace's (docs/specs/ai.md#consent)."""

    provider: Provider
    model: str
    purpose: AiTask
    granted_at: datetime


class CallOutcome(StrEnum):
    OK = "ok"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class ModelCall:
    """One `ai_calls` row: a request once its reply ended or failed
    (docs/specs/ai.md#usage-and-the-daily-token-cap)."""

    purpose: AiTask
    provider: Provider
    model: str
    tier: Tier | None
    """None under fixed routing."""
    attempt_id: int | None
    """The attempt an AI review reviewed."""
    local_day: date
    """On this machine's clock: the day the cap counts it in."""
    started_at: datetime
    ended_at: datetime
    outcome: CallOutcome
    error: ProviderErrorKind | None
    input_tokens: int | None
    """As the provider reported them; None without a usage report."""
    output_tokens: int | None
    counted_tokens: int
    """What the cap counts: the reported tokens, else the request's estimate."""
    cost_usd: float | None


class Verdict(StrEnum):
    """A criterion's verdict in an AI review."""

    MET = "met"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """One criterion of a review, with its text as it was reviewed, so the record reads the same
    after the rubric changes."""

    number: int
    """n of `Cn`, counted across the areas in order."""
    area: str
    criterion: str
    verdict: Verdict
    evidence: tuple[str, ...]
    """Up to three quotes the notes hold."""
    gaps: str


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """One `ai_reviews` row: a public record (docs/specs/ai.md#the-record)."""

    attempt_id: int
    created_at: datetime
    provider: Provider
    model: str
    prompt_version: str
    rubric_sha256: str
    notes_sha256: str
    items: tuple[ReviewItem, ...]
    """In rubric order."""
    summary: str
    quotes_dropped: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    id: int | None = None
    """None until the store has it."""
    format: int = REVIEW_FORMAT
    dismissed_at: datetime | None = None
