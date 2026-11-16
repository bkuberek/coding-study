"""The OpenAI adapter (docs/specs/ai.md#providers and #errors) against recorded replies, served by
`tests/fake_ai_provider.py` on the loopback."""

from collections.abc import Iterator

import pytest

from coding_study.adapters.ai.http_json import ENDPOINT_VARIABLE, JsonClient
from coding_study.adapters.ai.models import ADAPTERS, open_language_models
from coding_study.adapters.ai.openai import OpenAiModels
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
GET_HEADERS = {"authorization", "user-agent", "host", "accept-encoding", "connection"}


@pytest.fixture
def provider() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as fake:
        yield fake
    assert fake.unanswered == []


@pytest.fixture
def models(provider: FakeAiProvider) -> OpenAiModels:
    return OpenAiModels(JsonClient({ENDPOINT_VARIABLE: provider.endpoint}, "1.2.3"))


def request(*, schema: bool = True) -> ModelRequest:
    return ModelRequest(
        ModelRef.parse("openai:gpt-example"),
        "be brief",
        "hello",
        16000,
        300.0,
        schema=SCHEMA if schema else None,
        schema_name="verdict",
    )


def script(provider: FakeAiProvider, *answers: Answer) -> None:
    provider.script(Provider.OPENAI, Route.COMPLETE, *answers)


def failure(models: OpenAiModels, **keywords) -> ProviderError:
    with pytest.raises(ProviderError) as raised:
        models.complete(request(**keywords), KEY)
    assert SECRET not in str(raised.value)
    assert SECRET not in repr(raised.value)
    return raised.value


def test_a_structured_request_sends_the_schema_as_a_strict_text_format(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    models.complete(request(), KEY)
    (received,) = provider.received
    assert (received.method, received.path) == ("POST", "/v1/responses")
    assert received.json == {
        "model": "gpt-example",
        "instructions": "be brief",
        "input": [{"role": "user", "content": "hello"}],
        "max_output_tokens": 16000,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "verdict",
                "schema": SCHEMA,
                "strict": True,
            }
        },
    }


def test_a_free_text_request_has_no_text_format(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    models.complete(request(schema=False), KEY)
    assert provider.received[0].json == {
        "model": "gpt-example",
        "instructions": "be brief",
        "input": [{"role": "user", "content": "hello"}],
        "max_output_tokens": 16000,
        "store": False,
    }


def test_the_headers_are_the_bearer_key_and_the_agent(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    models.complete(request(), KEY)
    headers = provider.received[0].headers
    assert set(headers) == GET_HEADERS | {"content-type", "content-length"}
    assert headers["authorization"] == f"Bearer {SECRET}"
    assert headers["content-type"] == "application/json"
    assert headers["user-agent"] == "cstudy/1.2.3"


def test_a_structured_reply_is_parsed_from_its_output_text(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    reply = models.complete(request(), KEY)
    text = '{"verdict": "met", "summary": "The notes cover the criteria."}'
    assert reply == ModelReply(
        Ending.COMPLETE,
        text=text,
        data={"verdict": "met", "summary": "The notes cover the criteria."},
        usage=Usage(input_tokens=1500, output_tokens=1186),
    )


def test_a_free_text_reply_is_its_text(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    reply = models.complete(request(schema=False), KEY)
    assert (reply.ending, reply.data) == (Ending.COMPLETE, None)
    assert reply.text.startswith('{"verdict"')


def test_a_reply_cut_by_its_limit_ends_as_length_with_its_tokens(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "cut_reply")))
    reply = models.complete(request(), KEY)
    assert reply.ending is Ending.LENGTH
    assert reply.data is None
    assert reply.usage == Usage(900, 16000)


def test_a_refusal_ends_as_refused_with_no_text(provider, models):
    script(provider, Answer(json=recorded(Provider.OPENAI, "refusal")))
    assert models.complete(request(), KEY) == ModelReply(Ending.REFUSED, usage=Usage(850, 14))


def test_a_content_filter_stop_is_a_refusal(provider, models):
    reply = recorded(Provider.OPENAI, "cut_reply")
    reply["incomplete_details"] = {"reason": "content_filter"}
    script(provider, Answer(json=reply))
    assert models.complete(request(), KEY) == ModelReply(Ending.REFUSED, usage=Usage(900, 16000))


def test_a_reply_without_usage_reports_none(provider, models):
    reply = recorded(Provider.OPENAI, "structured_reply")
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
    reply = recorded(Provider.OPENAI, "structured_reply")
    reply["output"] = [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
    script(provider, Answer(json=reply))
    error = failure(models)
    assert (error.kind, str(error)) == (ProviderErrorKind.INVALID_REPLY, f"openai {reason}")
    assert error.usage == Usage(1500, 1186)


def test_a_response_that_failed_after_a_200_is_a_provider_failure_without_the_key(provider, models):
    body = recorded(Provider.OPENAI, "failed_reply")
    assert SECRET in body["error"]["message"]
    script(provider, Answer(json=body))
    error = failure(models)
    assert (error.kind, str(error)) == (
        ProviderErrorKind.PROVIDER,
        "openai failed: The model failed to generate a response for <key>.",
    )


@pytest.mark.parametrize(
    ("status", "fixture", "kind", "message"),
    [
        (
            401,
            "error_401",
            ProviderErrorKind.AUTH,
            "openai refused the key (401): set it again with cstudy ai key openai",
        ),
        (
            404,
            "error_404",
            ProviderErrorKind.MODEL,
            "openai has no model gpt-example, or it cannot answer in a JSON schema: "
            "see cstudy ai models openai",
        ),
        (
            429,
            "error_429",
            ProviderErrorKind.RATE_LIMIT,
            "openai is limiting this key's requests (429): try again later",
        ),
        (
            503,
            "error_5xx",
            ProviderErrorKind.PROVIDER,
            "openai failed (503): The server had an error while processing your request. "
            "Sorry about that!",
        ),
    ],
)
def test_a_failed_request_maps_to_its_kind_and_message(
    provider, models, status, fixture, kind, message
):
    script(provider, Answer(status, json=recorded(Provider.OPENAI, fixture)))
    error = failure(models)
    assert (error.kind, str(error)) == (kind, message)


def test_a_providers_text_that_echoes_the_key_is_scrubbed(provider, models):
    body = recorded(Provider.OPENAI, "error_401")
    assert SECRET in body["error"]["message"]
    script(provider, Answer(500, json=body))
    shown = str(failure(models))
    assert shown.startswith("openai failed (500): Incorrect API key provided: <key>.")


def test_a_400_about_the_schema_is_a_model_error(provider, models):
    body = {
        "error": {
            "message": "Invalid schema for response_format 'verdict': "
            "additionalProperties is required.",
            "type": "invalid_request_error",
            "param": "text.format.schema",
            "code": "invalid_json_schema",
        }
    }
    script(provider, Answer(400, json=body))
    assert failure(models).kind is ProviderErrorKind.MODEL


def test_a_model_list_is_the_ids_in_order(provider, models):
    provider.script(Provider.OPENAI, Route.MODELS, Answer(json=recorded(Provider.OPENAI, "models")))
    assert models.list_models(KEY, 30.0) == (
        "gpt-fast-example",
        "gpt-strong-example",
        "text-embedding-example",
    )
    (received,) = provider.received
    assert (received.method, received.path, received.query) == ("GET", "/v1/models", "")
    assert set(received.headers) == GET_HEADERS
    assert received.headers["authorization"] == f"Bearer {SECRET}"


def test_a_model_list_that_fails_keeps_the_key_out_of_its_error(provider, models):
    provider.script(
        Provider.OPENAI, Route.MODELS, Answer(401, json=recorded(Provider.OPENAI, "error_401"))
    )
    with pytest.raises(ProviderError) as raised:
        models.list_models(KEY, 30.0)
    assert raised.value.kind is ProviderErrorKind.AUTH
    assert SECRET not in str(raised.value)


def test_the_registry_opens_this_adapter_for_openai(provider):
    assert ADAPTERS[Provider.OPENAI] is OpenAiModels
    port = open_language_models({ENDPOINT_VARIABLE: provider.endpoint})
    script(provider, Answer(json=recorded(Provider.OPENAI, "structured_reply")))
    assert port.complete(request(), KEY).ending is Ending.COMPLETE
