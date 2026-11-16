"""The OpenRouter adapter (docs/specs/ai.md#providers and #errors): its request and reply shapes
over `tests/fake_ai_provider.py`, answering with the hand-written replies of
`tests/fixtures/ai/openrouter/`."""

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

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ai" / "openrouter"
SECRET = "sk-or-secret-0123456789"
KEY = ApiKey(SECRET)
MODEL_ID = "test/model"
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
        model=ModelRef(Provider.OPENROUTER, MODEL_ID),
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
    provider.script(Provider.OPENROUTER, Route.COMPLETE, *answers)


def failure(models: ProviderModels) -> ProviderError:
    with pytest.raises(ProviderError) as raised:
        models.complete(request(), KEY)
    assert SECRET not in str(raised.value)
    return raised.value


def test_a_structured_request_names_the_schema_and_requires_the_parameters(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(), KEY)
    (received,) = provider.received
    assert (received.method, received.path) == ("POST", "/api/v1/chat/completions")
    assert received.json == {
        "model": "test/model",
        "messages": [
            {"role": "system", "content": "Review the work."},
            {"role": "user", "content": "Here is the work."},
        ],
        "max_tokens": 16000,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "review", "strict": True, "schema": SCHEMA},
        },
        "provider": {"require_parameters": True},
    }


def test_a_request_without_a_schema_asks_for_text(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(None), KEY)
    assert provider.received[0].json == {
        "model": "test/model",
        "messages": [
            {"role": "system", "content": "Review the work."},
            {"role": "user", "content": "Here is the work."},
        ],
        "max_tokens": 16000,
    }


def test_the_headers_are_the_bearer_key_the_content_type_and_the_agent(provider, models):
    script(provider, fixture("structured"))
    models.complete(request(), KEY)
    headers = provider.received[0].headers
    assert headers["authorization"] == f"Bearer {SECRET}"
    assert headers["content-type"] == "application/json"
    assert headers["user-agent"] == "cstudy/1.2.3"
    assert set(headers) == {
        "authorization",
        "content-type",
        "user-agent",
        "host",
        "content-length",
        "accept-encoding",
        "connection",
    }


def test_a_structured_reply_is_parsed_with_its_tokens_and_cost(provider, models):
    script(provider, fixture("structured"))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.COMPLETE
    assert reply.data == {"summary": "Retries are bounded.", "ok": True}
    assert reply.usage == Usage(input_tokens=1200, output_tokens=350, cost_usd=0.00231)


def test_a_reply_without_a_schema_is_its_text(provider, models):
    script(provider, fixture("structured"))
    reply = models.complete(request(None), KEY)
    assert reply.data is None
    assert json.loads(reply.text) == {"summary": "Retries are bounded.", "ok": True}


def test_a_reply_without_usage_reports_none(provider, models):
    body = json.loads((FIXTURES / "structured.json").read_text())
    del body["usage"]
    script(provider, Answer(json=body))
    assert models.complete(request(), KEY).usage is None


def test_a_reply_without_a_cost_reports_the_tokens_alone(provider, models):
    body = json.loads((FIXTURES / "structured.json").read_text())
    del body["usage"]["cost"]
    script(provider, Answer(json=body))
    assert models.complete(request(), KEY).usage == Usage(1200, 350, None)


def test_a_reply_cut_by_the_output_limit_ends_as_length(provider, models):
    script(provider, fixture("cut"))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.LENGTH
    assert reply.data is None
    assert reply.usage == Usage(input_tokens=1200, output_tokens=500, cost_usd=0.0031)


@pytest.mark.parametrize("name", ["content_filter", "refusal"])
def test_a_content_filter_or_a_refusal_ends_as_refused(provider, models, name):
    script(provider, fixture(name))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.REFUSED
    assert (reply.text, reply.data) == ("", None)
    assert reply.usage is not None
    assert reply.usage.cost_usd is not None


@pytest.mark.parametrize(
    "answer",
    [
        {"choices": []},
        {"choices": [{"finish_reason": "tool_calls", "message": {"content": None}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "plain words"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "[1, 2]"}}]},
    ],
)
def test_a_reply_that_is_not_the_requested_object_is_invalid(provider, models, answer):
    script(provider, Answer(json=answer))
    assert failure(models).kind is ProviderErrorKind.INVALID_REPLY


def test_a_failure_inside_a_choice_is_a_provider_failure_that_keeps_its_tokens(provider, models):
    script(provider, fixture("choice_error"))
    error = failure(models)
    assert error.kind is ProviderErrorKind.PROVIDER
    assert str(error) == "openrouter failed (502): Upstream provider returned an invalid response"
    assert error.usage == Usage(1200, 0, 0.0004)


def test_an_error_document_in_an_answer_with_status_200_is_a_failure(provider, models):
    script(provider, fixture("error_in_200"))
    error = failure(models)
    assert (error.kind, str(error)) == (
        ProviderErrorKind.PROVIDER,
        "openrouter failed (502): Provider returned error",
    )


@pytest.mark.parametrize(
    ("name", "status", "kind", "message"),
    [
        (
            "error_401",
            401,
            ProviderErrorKind.AUTH,
            "openrouter refused the key (401): set it again with cstudy ai key openrouter",
        ),
        (
            "error_402",
            402,
            ProviderErrorKind.PROVIDER,
            "openrouter failed (402): Insufficient credits. "
            "Add more using https://openrouter.ai/credits",
        ),
        (
            "error_404",
            404,
            ProviderErrorKind.MODEL,
            "openrouter has no model test/model, or it cannot answer in a JSON schema: "
            "see cstudy ai models openrouter",
        ),
        (
            "error_400_model",
            400,
            ProviderErrorKind.MODEL,
            "openrouter has no model test/model, or it cannot answer in a JSON schema: "
            "see cstudy ai models openrouter",
        ),
        (
            "error_429",
            429,
            ProviderErrorKind.RATE_LIMIT,
            "openrouter is limiting this key's requests (429): try again later",
        ),
        (
            "error_503",
            503,
            ProviderErrorKind.PROVIDER,
            "openrouter failed (503): No available provider meets your routing requirements",
        ),
    ],
)
def test_a_failed_request_is_reported_by_its_kind(provider, models, name, status, kind, message):
    script(provider, fixture(name, status))
    error = failure(models)
    assert (error.kind, str(error)) == (kind, message)
    assert len(provider.received) == 1


def test_a_provider_that_echoes_the_key_has_it_replaced(provider, models):
    script(provider, Answer(500, json={"error": {"code": 500, "message": f"bad key {SECRET}"}}))
    assert str(failure(models)) == "openrouter failed (500): bad key <key>"


def test_the_models_are_listed_sorted(provider, models):
    provider.script(Provider.OPENROUTER, Route.MODELS, fixture("models"))
    assert models.list_models(Provider.OPENROUTER, KEY, 5.0) == ("test/model-a", "test/model-b")
    (received,) = provider.received
    assert (received.method, received.path) == ("GET", "/api/v1/models")
    assert received.headers["authorization"] == f"Bearer {SECRET}"
    assert "content-type" not in received.headers
    assert received.body == b""


def test_a_failed_listing_is_reported_without_the_key(provider, models):
    provider.script(Provider.OPENROUTER, Route.MODELS, fixture("error_401", 401))
    with pytest.raises(ProviderError) as raised:
        models.list_models(Provider.OPENROUTER, KEY, 5.0)
    assert raised.value.kind is ProviderErrorKind.AUTH
    assert SECRET not in str(raised.value)
