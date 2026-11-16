"""Ports of the AI preview (docs/specs/ai.md#architecture); adapters implement them."""

from datetime import date, datetime
from typing import Protocol

from coding_study.domain.ai import AiTask, ApiKey, Provider
from coding_study.domain.ai_models import ModelReply, ModelRequest
from coding_study.domain.ai_records import Consent, ModelCall, ReviewRecord


class LanguageModels(Protocol):
    """Every request to a provider goes through this port, and only an adapter reveals a key."""

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        """Answers the request whole, in the request's schema when it names one. Raises
        ProviderError, whose text never holds the key; a reply that ended `length` or `refused` is
        returned, not raised."""
        ...

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        """The model ids the provider lists, in its order. Raises ProviderError."""
        ...


class Credentials(Protocol):
    """`credentials.toml`, beside `config.toml` (docs/specs/ai.md#keys). Every method but `issue`
    raises UsageError for a file that would be inside the workspace, and ConfigError for one that
    does not load (`save_key` and `remove_key`: or cannot be written, which stays as it was)."""

    @property
    def location(self) -> str: ...

    def issue(self) -> str | None:
        """What keeps the file from loading, or from being read or written at all (it would be
        inside the workspace); None when it is fine or missing."""
        ...

    def keys_set(self) -> frozenset[Provider]:
        """The providers that have a key; empty when the file is missing."""
        ...

    def key(self, provider: Provider) -> ApiKey | None:
        """The provider's key, or None when it has none."""
        ...

    def save_key(self, provider: Provider, key: ApiKey) -> None:
        """Rewrites the file whole, atomically, with mode 0600."""
        ...

    def remove_key(self, provider: Provider) -> bool:
        """False when the provider had no key; the file goes with its last key."""
        ...


class AiStore(Protocol):
    """The AI tables of `progress.db`: consents, requests and reviews."""

    def consent(self, provider: Provider, model: str, purpose: AiTask) -> Consent | None: ...

    def consents(self) -> tuple[Consent, ...]:
        """Every consent, by provider, model and purpose."""
        ...

    def grant_consent(self, consent: Consent) -> None:
        """Records it; granting again keeps the first time."""
        ...

    def revoke_consent(self, provider: Provider, model: str, purpose: AiTask) -> bool:
        """False when there was none."""
        ...

    def record_call(self, call: ModelCall) -> None: ...

    def calls_between(self, first: date, last: date) -> tuple[ModelCall, ...]:
        """The requests of the local days `first` to `last`, both included, oldest first."""
        ...

    def add_review(self, record: ReviewRecord) -> int:
        """Stores it and returns its id."""
        ...

    def review(self, review_id: int) -> ReviewRecord | None: ...

    def reviews_of_problem(self, slug: str) -> tuple[ReviewRecord, ...]:
        """The reviews of the problem's attempts, newest first, dismissed ones included."""
        ...

    def reviews_of_attempt(self, attempt_id: int) -> tuple[ReviewRecord, ...]:
        """Newest first, dismissed ones included."""
        ...

    def dismiss_review(self, review_id: int, at: datetime) -> bool:
        """False when it was dismissed already, which changes nothing."""
        ...
