"""Keeping an AI provider's key in `credentials.toml` (docs/specs/ai.md#keys)."""

from coding_study.application.ai_ports import Credentials
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.errors import UsageError


def parse_provider(name: str) -> Provider:
    """Raises UsageError for a name that is no provider, without quoting it: it may be a key."""
    try:
        return Provider(name)
    except ValueError:
        known = ", ".join(Provider)
        raise UsageError(f"unknown provider; use one of {known}") from None


def save_key(credentials: Credentials, provider: Provider, text: str) -> str:
    """Keeps `text` as the provider's key and returns where the file is.

    Raises UsageError for a key that is not one line of text with no spaces, or a file that would
    be inside the workspace, and ConfigError for a file that does not load or cannot be written,
    which stays as it was. Nothing it raises holds the key.
    """
    credentials.save_key(provider, ApiKey(text))
    return credentials.location


def remove_key(credentials: Credentials, provider: Provider) -> bool:
    """False when the provider had no key. Raises as `save_key` does."""
    return credentials.remove_key(provider)
