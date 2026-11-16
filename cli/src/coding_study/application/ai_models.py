"""Listing a provider's model ids (docs/specs/ai.md#routing and docs/specs/cli.md#cstudy-ai-models).
It sends only the request for the list: no consent, no tokens and no usage row."""

from coding_study.application.ai_ports import Credentials, LanguageModels
from coding_study.domain.ai import AI_OFF, ApiKey, Provider
from coding_study.domain.config import AiSettings
from coding_study.domain.errors import UsageError

LIST_DEADLINE_S = 30.0


def list_provider_models(
    settings: AiSettings,
    credentials: Credentials,
    models: LanguageModels,
    provider: Provider,
) -> tuple[str, ...]:
    """The provider's model ids, sorted. Raises UsageError with AI off or without the provider's
    key, ConfigError for a `credentials.toml` that does not load, and ProviderError when the
    provider fails."""
    key = listing_key(settings, credentials, provider)
    return tuple(sorted(models.list_models(provider, key, LIST_DEADLINE_S)))


def listing_key(settings: AiSettings, credentials: Credentials, provider: Provider) -> ApiKey:
    """The key a listing from `provider` is sent with, which is every refusal before the request:
    UsageError with AI off or without the key, ConfigError for a `credentials.toml` that does
    not load."""
    if not settings.enabled:
        raise UsageError(AI_OFF)
    key = credentials.key(provider)
    if key is None:
        raise UsageError(f"no key for {provider}: cstudy ai key {provider}, or Settings")
    return key
