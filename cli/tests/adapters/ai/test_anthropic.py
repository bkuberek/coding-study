"""The Anthropic adapter (docs/specs/ai.md#providers and #errors) against recorded replies, served
by `tests/fake_ai_provider.py` on the loopback."""

from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from coding_study.adapters.ai import anthropic
from coding_study.adapters.ai.anthropic import AnthropicModels
from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE, JsonClient
from coding_study.adapters.ai.models import ADAPTERS, open_language_models
from coding_study.domain.ai import ApiKey, ModelRef, Provider
from coding_study.domain.ai_models import (
    Ending,
    ModelReply,
    ModelRequest,
    ProviderError,
    ProviderErrorKind,
    Usage,
)
from tests.ai_fixtures import SECRET, recorded
from tests.fake_ai_provider import Answer, FakeAiProvider, Route

KEY = ApiKey(SECRET)
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["met", "partial", "missing"]},
        "summary": {"type": "string"},
    },
    "required": ["verdict", "summary"],
    "additionalProperties": False,
}
REQUEST_HEADERS = {
    "content-type",
    "x-api-key",
    "anthropic-version",
    "user-agent",
    "host",
    "content-length",
    "accept-encoding",
    "connection",
}


@pytest.fixture
def provider() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as fake:
        yield fake
    assert fake.unanswered == []


@pytest.fixture
def models(provider: FakeAiProvider) -> AnthropicModels:
    return AnthropicModels(JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1.2.3"))


def request(*, schema: bool = True, model: str = "claude-example") -> ModelRequest:
    return ModelRequest(
        ModelRef.parse(f"anthropic:{model}"),
        "be brief",
        "hello",
        16000,
        300.0,
        schema=SCHEMA if schema else None,
        schema_name="verdict",
    )


def script(provider: FakeAiProvider, *answers: Answer) -> None:
    provider.script(Provider.ANTHROPIC, Route.COMPLETE, *answers)


def failure(models: AnthropicModels, **keywords) -> ProviderError:
    with pytest.raises(ProviderError) as raised:
        models.complete(request(**keywords), KEY)
    assert SECRET not in str(raised.value)
    assert SECRET not in repr(raised.value)
    return raised.value


def test_a_structured_request_sends_the_schema_as_the_output_format(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "structured_reply")))
    models.complete(request(), KEY)
    (received,) = provider.received
    assert (received.method, received.path) == ("POST", "/v1/messages")
    assert received.json == {
        "model": "claude-example",
        "max_tokens": 16000,
        "system": "be brief",
        "messages": [{"role": "user", "content": "hello"}],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }


def test_a_free_text_request_has_no_output_format(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "structured_reply")))
    models.complete(request(schema=False), KEY)
    assert provider.received[0].json == {
        "model": "claude-example",
        "max_tokens": 16000,
        "system": "be brief",
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_the_headers_are_the_key_the_pinned_version_and_the_agent(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "structured_reply")))
    models.complete(request(), KEY)
    headers = provider.received[0].headers
    assert set(headers) == REQUEST_HEADERS
    assert headers["x-api-key"] == SECRET
    assert headers["anthropic-version"] == anthropic.VERSION == "2026-10-21"
    assert headers["content-type"] == "application/json"
    assert headers["user-agent"] == "cstudy/1.2.3"


def test_a_structured_reply_is_parsed_from_its_text_block_and_counts_the_cache(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "structured_reply")))
    reply = models.complete(request(), KEY)
    text = '{"verdict": "met", "summary": "The notes cover the criteria."}'
    assert reply == ModelReply(
        Ending.COMPLETE,
        text=text,
        data={"verdict": "met", "summary": "The notes cover the criteria."},
        usage=Usage(input_tokens=1200 + 300 + 500, output_tokens=340),
    )


def test_a_free_text_reply_is_its_text(provider, models):
    script(
        provider, Answer(json=recorded(Provider.ANTHROPIC, "refusal") | {"stop_reason": "end_turn"})
    )
    reply = models.complete(request(schema=False), KEY)
    assert (reply.ending, reply.text, reply.data) == (
        Ending.COMPLETE,
        "I can't help with that request.",
        None,
    )


def test_a_reply_cut_by_its_limit_ends_as_length_with_its_tokens(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "cut_reply")))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.LENGTH
    assert reply.data is None
    assert reply.usage == Usage(900, 16000)


def test_a_refusal_ends_as_refused_with_no_text(provider, models):
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "refusal")))
    assert models.complete(request(), KEY) == ModelReply(Ending.REFUSED, usage=Usage(850, 12))


def test_a_reply_without_usage_reports_none(provider, models):
    reply = recorded(Provider.ANTHROPIC, "structured_reply")
    del reply["usage"]
    script(provider, Answer(json=reply))
    assert models.complete(request(), KEY).usage is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("not json", "sent a reply that is not JSON"),
        ("[1, 2]", "sent a reply that is not a JSON object"),
        ("", "sent a reply with no text"),
    ],
)
def test_a_structured_reply_that_is_no_object_is_invalid_and_still_counts(
    provider, models, text, reason
):
    reply = recorded(Provider.ANTHROPIC, "structured_reply")
    reply["content"] = [{"type": "text", "text": text}]
    script(provider, Answer(json=reply))
    error = failure(models)
    assert (error.kind, str(error)) == (ProviderErrorKind.INVALID_REPLY, f"anthropic {reason}")
    assert error.usage == Usage(2000, 340)


@pytest.mark.parametrize(
    ("status", "fixture", "kind", "message"),
    [
        (
            401,
            "error_401",
            ProviderErrorKind.AUTH,
            "anthropic refused the key (401): set it again with cstudy ai key anthropic",
        ),
        (
            404,
            "error_404",
            ProviderErrorKind.MODEL,
            "anthropic has no model claude-example, or it cannot answer in a JSON schema: "
            "see cstudy ai models anthropic",
        ),
        (
            429,
            "error_429",
            ProviderErrorKind.RATE_LIMIT,
            "anthropic is limiting this key's requests (429): try again later",
        ),
        (
            529,
            "error_5xx",
            ProviderErrorKind.PROVIDER,
            "anthropic failed (529): Overloaded",
        ),
    ],
)
def test_a_failed_request_maps_to_its_kind_and_message(
    provider, models, status, fixture, kind, message
):
    script(provider, Answer(status, json=recorded(Provider.ANTHROPIC, fixture)))
    error = failure(models)
    assert (error.kind, str(error)) == (kind, message)


def test_a_providers_text_that_echoes_the_key_is_scrubbed(provider, models):
    body = recorded(Provider.ANTHROPIC, "error_401")
    assert SECRET in body["error"]["message"]
    script(provider, Answer(500, json=body))
    assert str(failure(models)) == "anthropic failed (500): invalid x-api-key: <key>"


def test_a_400_about_the_structured_output_is_a_model_error(provider, models):
    body = {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "output_config.format: Schema is too complex for compilation.",
        },
    }
    script(provider, Answer(400, json=body))
    assert failure(models).kind is ProviderErrorKind.MODEL


def test_a_model_list_is_read_with_the_largest_page(provider):
    provider.script(
        Provider.ANTHROPIC, Route.MODELS, Answer(json=recorded(Provider.ANTHROPIC, "models"))
    )
    client = JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1.2.3")
    ids = AnthropicModels(client).list_models(KEY, 30.0)
    assert ids == ("claude-strong-example", "claude-fast-example")
    (received,) = provider.received
    assert (received.method, received.path, received.query) == ("GET", "/v1/models", "limit=1000")
    assert set(received.headers) == REQUEST_HEADERS - {"content-type", "content-length"}
    assert received.headers["x-api-key"] == SECRET
    assert received.headers["anthropic-version"] == anthropic.VERSION


def test_a_model_list_follows_its_pages(provider, models):
    provider.script(
        Provider.ANTHROPIC,
        Route.MODELS,
        Answer(json=recorded(Provider.ANTHROPIC, "models_first_page")),
        Answer(json=recorded(Provider.ANTHROPIC, "models_last_page")),
    )
    assert models.list_models(KEY, 30.0) == ("claude-strong-example", "claude-fast-example")
    queries = [received.query for received in provider.received]
    assert queries == ["limit=1000", "limit=1000&after_id=claude-strong-example"]


def test_a_model_list_stops_after_ten_pages(provider, models):
    page = Answer(json=recorded(Provider.ANTHROPIC, "models_first_page"))
    provider.script(Provider.ANTHROPIC, Route.MODELS, *[page] * 11)
    assert len(models.list_models(KEY, 30.0)) == anthropic.MAX_PAGES
    assert len(provider.received) == anthropic.MAX_PAGES


def test_a_model_list_shares_one_deadline_across_its_pages(provider, models, monkeypatch):
    provider.script(
        Provider.ANTHROPIC,
        Route.MODELS,
        Answer(json=recorded(Provider.ANTHROPIC, "models_first_page")),
    )
    clock = iter([0.0, 0.0, 99.0])
    monkeypatch.setattr(anthropic, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    with pytest.raises(ProviderError) as raised:
        models.list_models(KEY, 30.0)
    assert (raised.value.kind, str(raised.value)) == (
        ProviderErrorKind.TIMEOUT,
        "anthropic did not answer within 30 s",
    )


def test_a_model_list_that_fails_keeps_the_key_out_of_its_error(provider, models):
    provider.script(
        Provider.ANTHROPIC,
        Route.MODELS,
        Answer(401, json=recorded(Provider.ANTHROPIC, "error_401")),
    )
    with pytest.raises(ProviderError) as raised:
        models.list_models(KEY, 30.0)
    assert raised.value.kind is ProviderErrorKind.AUTH
    assert SECRET not in str(raised.value)


def test_the_registry_opens_this_adapter_for_anthropic(provider):
    assert ADAPTERS[Provider.ANTHROPIC] is AnthropicModels
    port = open_language_models({ENDPOINT_VARIABLE: provider.endpoint})
    script(provider, Answer(json=recorded(Provider.ANTHROPIC, "structured_reply")))
    assert port.complete(request(), KEY).ending is Ending.COMPLETE
