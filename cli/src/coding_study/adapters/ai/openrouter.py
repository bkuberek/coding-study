"""OpenRouter's chat completions (docs/specs/ai.md#providers) and its model list."""

from coding_study.adapters.ai.http_json import JsonClient, status_error
from coding_study.adapters.ai.json_fields import (
    JsonObject,
    amount,
    count,
    invalid_reply,
    items,
    mapping,
    parse_object,
    text,
)
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    Usage,
)

ORIGIN = "https://openrouter.ai"
COMPLETIONS_PATH = "/api/v1/chat/completions"
MODELS_PATH = "/api/v1/models"
LENGTH_FINISH = "length"
REFUSED_FINISH = "content_filter"
ERROR_FINISH = "error"
UNKNOWN_FAILURE_STATUS = 502


def open_adapter(client: JsonClient) -> "OpenRouterAdapter":
    return OpenRouterAdapter(client)


class OpenRouterAdapter:
    def __init__(self, client: JsonClient) -> None:
        self._client = client

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        reply = self._client.post(
            Provider.OPENROUTER,
            ORIGIN,
            COMPLETIONS_PATH,
            _body(request),
            headers=_headers(key),
            key=key,
            deadline_s=request.deadline_s,
            model_id=request.model.model_id,
        )
        return _reply(reply, request, key)

    def list_models(self, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        """The ids of the models OpenRouter routes to, sorted."""
        page = self._client.get(
            Provider.OPENROUTER,
            ORIGIN,
            MODELS_PATH,
            headers=_headers(key),
            key=key,
            deadline_s=deadline_s,
        )
        ids = {text(mapping(model).get("id")) for model in items(page.get("data"))}
        return tuple(sorted(ids - {""}))


def _headers(key: ApiKey) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.reveal()}"}


def _body(request: ModelRequest) -> JsonObject:
    body: dict[str, object] = {
        "model": request.model.model_id,
        "messages": [
            {"role": "system", "content": request.instructions},
            {"role": "user", "content": request.message},
        ],
        "max_tokens": request.max_output_tokens,
    }
    if request.schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": request.schema_name, "strict": True, "schema": request.schema},
        }
        body["provider"] = {"require_parameters": True}
    return body


def _usage(reply: JsonObject) -> Usage | None:
    usage = mapping(reply.get("usage"))
    if not usage:
        return None
    return Usage(
        count(usage.get("prompt_tokens")),
        count(usage.get("completion_tokens")),
        amount(usage.get("cost")),
    )


def _reply(reply: JsonObject, request: ModelRequest, key: ApiKey) -> ModelReply:
    usage = _usage(reply)
    failure = mapping(reply.get("error"))
    if failure:
        raise _failure(failure, request, key, usage)
    choices = items(reply.get("choices"))
    if not choices:
        raise invalid_reply(Provider.OPENROUTER, "it holds no choice", usage)
    choice = mapping(choices[0])
    finish = text(choice.get("finish_reason"))
    if finish == ERROR_FINISH:
        raise _failure(mapping(choice.get("error")), request, key, usage)
    message = mapping(choice.get("message"))
    if finish == REFUSED_FINISH or text(message.get("refusal")):
        return ModelReply(Ending.REFUSED, usage=usage)
    written = text(message.get("content"))
    if finish == LENGTH_FINISH:
        return ModelReply(Ending.LENGTH, written, usage=usage)
    if not written:
        reason = f"it holds no text (finish reason {finish})" if finish else "it holds no text"
        raise invalid_reply(Provider.OPENROUTER, reason, usage)
    if request.schema is None:
        return ModelReply(Ending.COMPLETE, written, usage=usage)
    data = parse_object(written)
    if data is None:
        raise invalid_reply(Provider.OPENROUTER, "the text is not a JSON object", usage)
    return ModelReply(Ending.COMPLETE, written, data, usage)


def _failure(
    error: JsonObject, request: ModelRequest, key: ApiKey, usage: Usage | None
) -> ProviderError:
    """A failure OpenRouter reports in an answer with status 200: its `error.code` is the HTTP
    status the failure would have had."""
    code = error.get("code")
    status = (
        code if isinstance(code, int) and not isinstance(code, bool) else UNKNOWN_FAILURE_STATUS
    )
    raised = status_error(
        Provider.OPENROUTER, status, text(error.get("message")), key, request.model.model_id
    )
    return ProviderError(raised.kind, str(raised), usage)
