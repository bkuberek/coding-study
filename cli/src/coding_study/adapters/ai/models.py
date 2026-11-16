"""The model port, by provider (docs/specs/ai.md#architecture).

`ProviderModels` sends each request to the adapter of the request's provider. An adapter is a
class that takes the `JsonClient` and provides a `ProviderAdapter`; `ADAPTERS` names them.
"""

from collections.abc import Callable, Mapping
from typing import Protocol

from coding_study.adapters.ai.anthropic import AnthropicModels
from coding_study.adapters.ai.http_json import JsonClient
from coding_study.adapters.ai.openai import OpenAiModels
from coding_study.adapters.workspace_marker import tool_version
from coding_study.application.ai_ports import LanguageModels
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.ai_models import (
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
)


class ProviderAdapter(Protocol):
    """One provider's API: its request and reply shapes, over a `JsonClient`."""

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply: ...

    def list_models(self, key: ApiKey, deadline_s: float) -> tuple[str, ...]: ...


type AdapterFactory = Callable[[JsonClient], ProviderAdapter]

ADAPTERS: dict[Provider, AdapterFactory] = {
    Provider.ANTHROPIC: AnthropicModels,
    Provider.OPENAI: OpenAiModels,
}
"""The provider adapters of this build."""


class ProviderModels:
    """`LanguageModels` over the adapters in `factories`."""

    def __init__(self, client: JsonClient, factories: Mapping[Provider, AdapterFactory]) -> None:
        self._client = client
        self._factories = factories
        self._opened: dict[Provider, ProviderAdapter] = {}

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        return self._adapter(request.model.provider).complete(request, key)

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        return self._adapter(provider).list_models(key, deadline_s)

    def _adapter(self, provider: Provider) -> ProviderAdapter:
        if provider not in self._opened:
            factory = self._factories.get(provider)
            if factory is None:
                raise ProviderError(
                    ProviderErrorKind.PROVIDER, f"this cstudy has no adapter for {provider}"
                )
            self._opened[provider] = factory(self._client)
        return self._opened[provider]


def open_language_models(environ: Mapping[str, str]) -> LanguageModels:
    """The port over the real providers. Raises ConfigError for a `CSTUDY_AI_ENDPOINT` that is
    not a loopback address, before anything is sent."""
    return ProviderModels(JsonClient(environ, tool_version()), ADAPTERS)
