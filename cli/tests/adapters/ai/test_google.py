"""The Google adapter (docs/specs/ai.md#providers and #errors): its request and reply shapes over
`tests/fake_ai_provider.py`, answering with the hand-written replies of
`tests/fixtures/ai/google/`."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE, JsonClient
from coding_study.adapters.ai.models import ADAPTERS, ProviderModels
from coding_study.domain.ai import ApiKey, ModelRef, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from tests.fake_ai_provider import Answer, FakeAiProvider, Route

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ai" / "google"
SECRET = "AIza-secret-0123456789"
KEY = ApiKey(SECRET)
MODEL_ID = "gemini-test-pro"
SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "ok": {"type": "boolean"}},
    "required": ["summary", "ok"],
    "additionalProperties": False,
}


def fixture(name: str, status: int = 200) -> Answer:
    return Answer(status, json=json.loads((FIXTURES / f"{name}.json").read_text()))


def request(schema: dict[str, object] | None = SCHEMA) -> ModelRequest:
    return ModelRequest(
        model=ModelRef(Provider.GOOGLE, MODEL_ID),
        instructions="Review the work.",
        message="Here is the work.",
        max_output_tokens=16000,
        deadline_s=5.0,
        schema=schema,
        schema_name="review",
    )


@pytest.fixture
def provider() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as fake:
        yield fake
    assert fake.unanswered == []


@pytest.fixture
def models(provider: FakeAiProvider) -> ProviderModels:
    client = JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1.2.3")
    return ProviderModels(client, ADAPTERS)


def script(provider: FakeAiProvider, *answers: Answer) -> None:
    provider.script(Provider.GOOGLE, Route.COMPLETE, *answers, model_id=MODEL_ID)


def test_a_structured_request_sends_the_system_prompt_the_message_and_the_schema(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(), KEY)
    (received,) = provider.requests_to(Provider.GOOGLE, Route.COMPLETE, MODEL_ID)
    assert (received.method, received.path) == (
        "POST",
        "/v1beta/models/gemini-test-pro:generateContent",
    )
    assert received.json == {
        "systemInstruction": {"parts": [{"text": "Review the work."}]},
        "contents": [{"role": "user", "parts": [{"text": "Here is the work."}]}],
        "generationConfig": {
            "maxOutputTokens": 16000,
            "responseMimeType": "application/json",
            "responseJsonSchema": SCHEMA,
        },
    }


def test_the_headers_are_the_key_the_content_type_and_the_agent(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(), KEY)
    headers = provider.received[0].headers
    assert headers["x-goog-api-key"] == SECRET
    assert headers["content-type"] == "application/json"
    assert headers["user-agent"] == "cstudy/1.2.3"
    assert set(headers) == {
        "x-goog-api-key",
        "content-type",
        "user-agent",
        "host",
        "content-length",
        "accept-encoding",
        "connection",
    }


def test_the_key_is_in_no_url_and_no_body(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(), KEY)
    received = provider.received[0]
    assert SECRET not in received.path
    assert SECRET.encode() not in received.body


def test_a_request_without_a_schema_asks_for_text(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(None), KEY)
    assert provider.received[0].json["generationConfig"] == {"maxOutputTokens": 16000}


def test_a_structured_reply_is_parsed_and_its_tokens_counted(provider, models):
    script(provider, fixture("structured"))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.COMPLETE
    assert reply.data == {"summary": "Retries are bounded.", "ok": True}
    assert json.loads(reply.text) == reply.data
    assert reply.usage == Usage(input_tokens=1200, output_tokens=350)
    assert reply.usage.cost_usd is None


def test_a_reply_without_a_schema_is_its_text(provider, models):
    script(provider, fixture("structured"))
    reply = models.complete(request(None), KEY)
    assert reply.ending is Ending.COMPLETE
    assert reply.data is None
    assert json.loads(reply.text) == {"summary": "Retries are bounded.", "ok": True}


def test_a_thought_part_is_not_part_of_the_text(provider, models):
    body = json.loads((FIXTURES / "structured.json").read_text())
    parts = body["candidates"][0]["content"]["parts"]
    body["candidates"][0]["content"]["parts"] = [{"text": "thinking...", "thought": True}, *parts]
    script(provider, Answer(json=body))
    assert models.complete(request(), KEY).data == {"summary": "Retries are bounded.", "ok": True}


def test_a_reply_cut_by_the_output_limit_ends_as_length(provider, models):
    script(provider, fixture("cut"))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.LENGTH
    assert reply.data is None
    assert reply.usage == Usage(input_tokens=1200, output_tokens=500)


@pytest.mark.parametrize("name", ["safety", "blocked_prompt"])
def test_a_safety_stop_or_a_blocked_prompt_ends_as_refused(provider, models, name):
    script(provider, fixture(name))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.REFUSED
    assert (reply.text, reply.data) == ("", None)
    assert reply.usage == Usage(input_tokens=1200, output_tokens=0)


def test_a_reply_without_text_is_invalid_and_keeps_its_tokens(provider, models):
    script(provider, fixture("no_text"))
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert raised.value.kind is ProviderErrorKind.INVALID_REPLY
    assert "finish reason OTHER" in str(raised.value)
    assert raised.value.usage == Usage(input_tokens=1200, output_tokens=0)


@pytest.mark.parametrize(
    "answer",
    [
        {"candidates": []},
        {"candidates": [{"content": {"parts": [{"text": "plain words"}]}, "finishReason": "STOP"}]},
        {"candidates": [{"content": {"parts": [{"text": "[1, 2]"}]}, "finishReason": "STOP"}]},
    ],
)
def test_a_reply_that_is_not_the_requested_object_is_invalid(provider, models, answer):
    script(provider, Answer(json=answer))
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert raised.value.kind is ProviderErrorKind.INVALID_REPLY


def test_a_reply_without_usage_reports_none(provider, models):
    body = json.loads((FIXTURES / "structured.json").read_text())
    del body["usageMetadata"]
    script(provider, Answer(json=body))
    assert models.complete(request(), KEY).usage is None


@pytest.mark.parametrize(
    ("name", "status", "kind", "message"),
    [
        (
            "error_403",
            403,
            ProviderErrorKind.AUTH,
            "google refused the key (403): set it again with cstudy ai key google",
        ),
        (
            "error_400_api_key_invalid",
            400,
            ProviderErrorKind.AUTH,
            "google refused the key (400): set it again with cstudy ai key google",
        ),
        (
            "error_404",
            404,
            ProviderErrorKind.MODEL,
            "google has no model gemini-test-pro, or it cannot answer in a JSON schema: "
            "see cstudy ai models google",
        ),
        (
            "error_400_schema",
            400,
            ProviderErrorKind.MODEL,
            "google has no model gemini-test-pro, or it cannot answer in a JSON schema: "
            "see cstudy ai models google",
        ),
        (
            "error_429",
            429,
            ProviderErrorKind.RATE_LIMIT,
            "google is limiting this key's requests (429): try again later",
        ),
        (
            "error_503",
            503,
            ProviderErrorKind.PROVIDER,
            "google failed (503): The model is overloaded. Please try again later.",
        ),
    ],
)
def test_a_failed_request_is_reported_by_its_kind(provider, models, name, status, kind, message):
    script(provider, fixture(name, status))
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert (raised.value.kind, str(raised.value)) == (kind, message)
    assert SECRET not in str(raised.value)
    assert len(provider.received) == 1


def test_a_provider_that_echoes_the_key_has_it_replaced(provider, models):
    echo = {
        "error": {"code": 500, "message": f"bad request for key {SECRET}", "status": "INTERNAL"}
    }
    script(provider, Answer(500, json=echo))
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert str(raised.value) == "google failed (500): bad request for key <key>"


def test_the_models_that_generate_content_are_listed_over_every_page_sorted(provider, models):
    provider.script(Provider.GOOGLE, Route.MODELS, fixture("models"), fixture("models_page_2"))
    assert models.list_models(Provider.GOOGLE, KEY, 5.0) == (
        "gemini-test-flash",
        "gemini-test-lite",
        "gemini-test-pro",
    )
    first, second = provider.requests_to(Provider.GOOGLE, Route.MODELS)
    assert (first.method, first.route_path, first.query) == (
        "GET",
        "/v1beta/models",
        "pageSize=1000",
    )
    assert second.query == "pageSize=1000&pageToken=page%202%2Ftoken"
    for received in (first, second):
        assert received.headers["x-goog-api-key"] == SECRET
        assert "content-type" not in received.headers
        assert received.body == b""


def test_a_failed_listing_is_reported_without_the_key(provider, models):
    provider.script(Provider.GOOGLE, Route.MODELS, fixture("error_403", 403))
    with pytest.raises(ProviderError) as raised:
        models.list_models(Provider.GOOGLE, KEY, 5.0)
    assert raised.value.kind is ProviderErrorKind.AUTH
    assert SECRET not in str(raised.value)
