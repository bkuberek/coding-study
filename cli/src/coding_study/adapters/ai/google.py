"""Google's Gemini API (docs/specs/ai.md#providers): `generateContent` and the model list."""

from urllib.parse import quote

from coding_study.adapters.ai.http_json import JsonClient
from coding_study.adapters.ai.json_fields import (
    JsonObject,
    count,
    invalid_reply,
    items,
    mapping,
    parse_object,
    text,
)
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.ai_models import Ending, ModelReply, ModelRequest, Usage

ORIGIN = "https://generativelanguage.googleapis.com"
KEY_HEADER = "x-goog-api-key"
LIST_PAGE_SIZE = 1000
MAX_LIST_PAGES = 20
GENERATE_METHOD = "generateContent"
MODEL_PREFIX = "models/"
REFUSED_FINISHES = frozenset({"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"})
"""The finish reasons of a reply the provider withheld."""
LENGTH_FINISH = "MAX_TOKENS"
UNSPECIFIED_BLOCK = "BLOCK_REASON_UNSPECIFIED"


def open_adapter(client: JsonClient) -> "GoogleAdapter":
    return GoogleAdapter(client)


class GoogleAdapter:
    def __init__(self, client: JsonClient) -> None:
        self._client = client

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        model_id = request.model.model_id
        reply = self._client.post(
            Provider.GOOGLE,
            ORIGIN,
            f"/v1beta/models/{quote(model_id, safe='')}:{GENERATE_METHOD}",
            _body(request),
            headers={KEY_HEADER: key.reveal()},
            key=key,
            deadline_s=request.deadline_s,
            model_id=model_id,
        )
        return _reply(reply, structured=request.schema is not None)

    def list_models(self, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        """The ids of the models that can generate content, sorted."""
        ids: set[str] = set()
        token = ""
        for _page in range(MAX_LIST_PAGES):
            query = f"?pageSize={LIST_PAGE_SIZE}"
            if token:
                query += f"&pageToken={quote(token, safe='')}"
            page = self._client.get(
                Provider.GOOGLE,
                ORIGIN,
                f"/v1beta/models{query}",
                headers={KEY_HEADER: key.reveal()},
                key=key,
                deadline_s=deadline_s,
            )
            ids.update(_generating_ids(page))
            token = text(page.get("nextPageToken"))
            if not token:
                break
        return tuple(sorted(ids))


def _body(request: ModelRequest) -> JsonObject:
    config: dict[str, object] = {"maxOutputTokens": request.max_output_tokens}
    if request.schema is not None:
        config["responseMimeType"] = "application/json"
        config["responseJsonSchema"] = request.schema
    return {
        "systemInstruction": {"parts": [{"text": request.instructions}]},
        "contents": [{"role": "user", "parts": [{"text": request.message}]}],
        "generationConfig": config,
    }


def _generating_ids(page: JsonObject) -> list[str]:
    ids: list[str] = []
    for item in items(page.get("models")):
        model = mapping(item)
        methods = items(model.get("supportedGenerationMethods"))
        name = text(model.get("name"))
        if GENERATE_METHOD in methods and name:
            ids.append(name.removeprefix(MODEL_PREFIX))
    return ids


def _usage(reply: JsonObject) -> Usage | None:
    metadata = mapping(reply.get("usageMetadata"))
    if not metadata:
        return None
    output = count(metadata.get("candidatesTokenCount")) + count(metadata.get("thoughtsTokenCount"))
    return Usage(count(metadata.get("promptTokenCount")), output)


def _reply(reply: JsonObject, *, structured: bool) -> ModelReply:
    usage = _usage(reply)
    candidates = items(reply.get("candidates"))
    if not candidates:
        block = text(mapping(reply.get("promptFeedback")).get("blockReason"))
        if block and block != UNSPECIFIED_BLOCK:
            return ModelReply(Ending.REFUSED, usage=usage)
        raise invalid_reply(Provider.GOOGLE, "it holds no candidate", usage)
    candidate = mapping(candidates[0])
    finish = text(candidate.get("finishReason"))
    if finish in REFUSED_FINISHES:
        return ModelReply(Ending.REFUSED, usage=usage)
    written = "".join(
        text(part.get("text"))
        for part in map(mapping, items(mapping(candidate.get("content")).get("parts")))
        if not part.get("thought")
    )
    if finish == LENGTH_FINISH:
        return ModelReply(Ending.LENGTH, written, usage=usage)
    if not written:
        reason = f"it holds no text (finish reason {finish})" if finish else "it holds no text"
        raise invalid_reply(Provider.GOOGLE, reason, usage)
    if not structured:
        return ModelReply(Ending.COMPLETE, written, usage=usage)
    data = parse_object(written)
    if data is None:
        raise invalid_reply(Provider.GOOGLE, "the text is not a JSON object", usage)
    return ModelReply(Ending.COMPLETE, written, data, usage)
