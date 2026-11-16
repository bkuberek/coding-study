"""OpenAI's Responses API (docs/specs/ai.md#providers)."""

from coding_study.adapters.ai.http_json import MESSAGE_CHARACTERS, JsonClient, JsonObject
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

ORIGIN = "https://api.openai.com"


class OpenAiModels:
    def __init__(self, client: JsonClient) -> None:
        self._client = client

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        """Raises ProviderError."""
        reply = self._client.post(
            Provider.OPENAI,
            ORIGIN,
            "/v1/responses",
            _body(request),
            headers=_headers(key),
            key=key,
            deadline_s=request.deadline_s,
            model_id=request.model.model_id,
        )
        return _reply(reply, key, structured_output=request.schema is not None)

    def list_models(self, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        """The model ids, in alphabetical order. Raises ProviderError."""
        page = self._client.get(
            Provider.OPENAI,
            ORIGIN,
            "/v1/models",
            headers=_headers(key),
            key=key,
            deadline_s=deadline_s,
        )
        ids = (text_of(mapping(entry).get("id")) for entry in items(page.get("data")))
        return tuple(sorted(model_id for model_id in ids if model_id))


def _headers(key: ApiKey) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.reveal()}"}


def _body(request: ModelRequest) -> dict[str, object]:
    body: dict[str, object] = {
        "model": request.model.model_id,
        "instructions": request.instructions,
        "input": [{"role": "user", "content": request.message}],
        "max_output_tokens": request.max_output_tokens,
    }
    if request.schema is not None:
        body["text"] = {
            "format": {
                "type": "json_schema",
                "name": request.schema_name,
                "schema": request.schema,
                "strict": True,
            }
        }
    return body


def _reply(reply: JsonObject, key: ApiKey, *, structured_output: bool) -> ModelReply:
    usage = _usage(reply.get("usage"))
    status = reply.get("status")
    if status == "failed":
        raise _failure(reply, key, usage)
    texts: list[str] = []
    for item in (mapping(item) for item in items(reply.get("output"))):
        if item.get("type") != "message":
            continue
        for part in (mapping(part) for part in items(item.get("content"))):
            if part.get("type") == "refusal":
                return ModelReply(Ending.REFUSED, usage=usage)
            if part.get("type") == "output_text":
                texts.append(text_of(part.get("text")))
    text = "".join(texts)
    if status == "incomplete":
        reason = mapping(reply.get("incomplete_details")).get("reason")
        if reason == "content_filter":
            return ModelReply(Ending.REFUSED, usage=usage)
        return ModelReply(Ending.LENGTH, text=text, usage=usage)
    if not structured_output:
        return ModelReply(Ending.COMPLETE, text=text, usage=usage)
    if not text:
        raise invalid_reply(Provider.OPENAI, "sent a reply with no text", usage)
    data = structured(Provider.OPENAI, text, usage)
    return ModelReply(Ending.COMPLETE, text=text, data=data, usage=usage)


def _failure(reply: JsonObject, key: ApiKey, usage: Usage | None) -> ProviderError:
    """A response whose own status is `failed`, which came back with a 200."""
    message = text_of(mapping(reply.get("error")).get("message"))
    shown = " ".join(key.scrub(message).split())[:MESSAGE_CHARACTERS]
    return ProviderError(ProviderErrorKind.PROVIDER, f"openai failed: {shown}", usage)


def _usage(value: object) -> Usage | None:
    """Input tokens, cached ones included, and output tokens, reasoning ones included."""
    reported = mapping(value)
    if not reported:
        return None
    return Usage(count(reported.get("input_tokens")), count(reported.get("output_tokens")))
