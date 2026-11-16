"""Anthropic's Messages API (docs/specs/ai.md#providers)."""

import time
from urllib.parse import quote

from coding_study.adapters.ai.http_json import JsonClient, JsonObject
from coding_study.adapters.ai.reply_json import (
    count,
    invalid_reply,
    items,
    mapping,
    structured,
    text_of,
)
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)

ORIGIN = "https://api.anthropic.com"
VERSION = "2026-10-21"
"""The `anthropic-version` every request pins."""
PAGE_SIZE = 1000
MAX_PAGES = 10


class AnthropicModels:
    def __init__(self, client: JsonClient) -> None:
        self._client = client

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        """Raises ProviderError."""
        reply = self._client.post(
            Provider.ANTHROPIC,
            ORIGIN,
            "/v1/messages",
            _body(request),
            headers=_headers(key),
            key=key,
            deadline_s=request.deadline_s,
            model_id=request.model.model_id,
        )
        return _reply(reply, structured_output=request.schema is not None)

    def list_models(self, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        """The model ids, newest first. Raises ProviderError."""
        end = time.monotonic() + deadline_s
        ids: list[str] = []
        path = f"/v1/models?limit={PAGE_SIZE}"
        for _ in range(MAX_PAGES):
            page = self._client.get(
                Provider.ANTHROPIC,
                ORIGIN,
                path,
                headers=_headers(key),
                key=key,
                deadline_s=_left(end, deadline_s),
            )
            ids.extend(text_of(mapping(entry).get("id")) for entry in items(page.get("data")))
            last = page.get("last_id")
            if page.get("has_more") is not True or not isinstance(last, str):
                break
            path = f"/v1/models?limit={PAGE_SIZE}&after_id={quote(last, safe='')}"
        return tuple(model_id for model_id in ids if model_id)


def _left(end: float, deadline_s: float) -> float:
    left = end - time.monotonic()
    if left <= 0:
        raise ProviderError(
            ProviderErrorKind.TIMEOUT, f"anthropic did not answer within {deadline_s:g} s"
        )
    return left


def _headers(key: ApiKey) -> dict[str, str]:
    return {"x-api-key": key.reveal(), "anthropic-version": VERSION}


def _body(request: ModelRequest) -> dict[str, object]:
    body: dict[str, object] = {
        "model": request.model.model_id,
        "max_tokens": request.max_output_tokens,
        "system": request.instructions,
        "messages": [{"role": "user", "content": request.message}],
    }
    if request.schema is not None:
        body["output_config"] = {"format": {"type": "json_schema", "schema": request.schema}}
    return body


def _reply(reply: JsonObject, *, structured_output: bool) -> ModelReply:
    usage = _usage(reply.get("usage"))
    stop = reply.get("stop_reason")
    if stop == "refusal":
        return ModelReply(Ending.REFUSED, usage=usage)
    blocks = [mapping(block) for block in items(reply.get("content"))]
    text = "".join(text_of(block.get("text")) for block in blocks if block.get("type") == "text")
    if stop == "max_tokens":
        return ModelReply(Ending.LENGTH, text=text, usage=usage)
    if not structured_output:
        return ModelReply(Ending.COMPLETE, text=text, usage=usage)
    if not text:
        raise invalid_reply(Provider.ANTHROPIC, "sent a reply with no text", usage)
    data = structured(Provider.ANTHROPIC, text, usage)
    return ModelReply(Ending.COMPLETE, text=text, data=data, usage=usage)


def _usage(value: object) -> Usage | None:
    """Input tokens with the cache's, and output tokens (thinking included)."""
    reported = mapping(value)
    if not reported:
        return None
    cached = count(reported.get("cache_creation_input_tokens")) + count(
        reported.get("cache_read_input_tokens")
    )
    return Usage(count(reported.get("input_tokens")) + cached, count(reported.get("output_tokens")))
