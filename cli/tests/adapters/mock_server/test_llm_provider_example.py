"""The example mock LLM provider config, served by the real mock server on loopback: it is data on
the mock server's format, with streaming, a 429 with Retry-After, token usage and embeddings."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from coding_study.adapters.schema_validation import SchemaValidator
from coding_study.domain.mock_configs import (
    MockFiles,
    ScenarioReach,
    malformed_run_time_value,
    rendered_mock_config,
    response_fields,
    response_texts,
)
from tests.helpers import SCHEMAS_DIRECTORY
from tests.mock_server_support import LLM_PROVIDER_CONFIG, SAMPLE_TOKEN, StackClient

FAST_POLL_S = 0.01
HOST = "llm:8080"
QUESTION = [
    {"role": "system", "content": "You answer questions about desks."},
    {"role": "user", "content": "Which desks are free?"},
]
PROMPT_WORDS = 11
"""The words of QUESTION's texts, its roles included, as `words(...)` counts them."""


def provider_files() -> MockFiles:
    return MockFiles(yaml.safe_load(LLM_PROVIDER_CONFIG.read_text()))


@pytest.fixture
def client(tmp_path: Path) -> Iterator[StackClient]:
    path = tmp_path / "mocks.json"
    path.write_text(
        rendered_mock_config({"llm": provider_files()}, SAMPLE_TOKEN, ScenarioReach.EVERY)
    )
    servers = start_servers(load_stack_config(path), ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


def chat(client: StackClient, **fields: Any) -> tuple[int, dict[str, str], bytes]:
    body = {"model": "chat-small", "messages": QUESTION, "max_tokens": 64, **fields}
    answer = client.api(
        "/v1/chat/completions", method="POST", host=HOST, body=json.dumps(body).encode()
    )
    return answer.status, answer.headers, answer.body


def events(stream: bytes) -> list[str]:
    return [line.removeprefix("data: ") for line in stream.decode().split("\n") if line]


def test_the_example_is_a_valid_mock_config():
    document = yaml.safe_load(LLM_PROVIDER_CONFIG.read_text())
    validator = SchemaValidator.from_file(SCHEMAS_DIRECTORY / "mock.schema.json")
    assert validator.violations(document, str(LLM_PROVIDER_CONFIG)) == []


def test_the_example_records_where_its_shape_comes_from():
    assert "chat-completions" in yaml.safe_load(LLM_PROVIDER_CONFIG.read_text())["shape_version"]


def test_the_example_names_only_run_time_values_s20_accepts():
    files = provider_files()
    texts = [
        text for _where, fields in response_fields(files) for text in response_texts(fields, files)
    ]
    assert [text for text in texts if malformed_run_time_value(text) is not None] == []


def test_a_rendering_leaves_the_shape_record_out():
    rendered = rendered_mock_config({"llm": provider_files()}, SAMPLE_TOKEN, ScenarioReach.EVERY)
    assert "shape_version" not in json.loads(rendered)["mocks"]["llm"]


def test_a_streaming_request_gets_events_that_end_in_done(client: StackClient):
    status, headers, body = chat(client, stream=True)
    assert (status, headers["content-type"], events(body)[-1]) == (
        200,
        "text/event-stream",
        "[DONE]",
    )


def test_a_stream_echoes_the_model_it_was_asked_for(client: StackClient):
    _status, _headers, body = chat(client, stream=True, model="chat-large")
    assert json.loads(events(body)[0])["model"] == "chat-large"


def test_a_stream_ends_with_usage_counted_from_the_messages(client: StackClient):
    _status, _headers, body = chat(client, stream=True)
    usage = json.loads(events(body)[-2])["usage"]
    assert usage == {"prompt_tokens": PROMPT_WORDS, "completion_tokens": 3}


def test_a_plain_request_gets_a_whole_answer_with_its_usage(client: StackClient):
    status, _headers, body = chat(client)
    answer = json.loads(body)
    assert (status, answer["model"], answer["usage"]["prompt_tokens"]) == (
        200,
        "chat-small",
        PROMPT_WORDS,
    )


def test_a_rate_limit_says_when_to_retry(client: StackClient):
    client.set_scenario("llm", "rate_limited")
    status, headers, body = chat(client, stream=True)
    assert (status, headers["retry-after"], json.loads(body)["error"]["type"]) == (
        429,
        "1",
        "rate_limit",
    )


def test_a_rate_limit_then_the_stream_again(client: StackClient):
    client.set_scenario("llm", "rate_limited_then_ok")
    statuses = [chat(client, stream=True)[0] for _ in range(2)]
    assert statuses == [429, 200]


def test_a_dropped_stream_ends_after_one_event_with_no_done(client: StackClient):
    client.set_scenario("llm", "dropped_mid_stream")
    _status, _headers, body = chat(client, stream=True)
    assert len(events(body)) == 1


def test_a_malformed_chunk_is_not_json(client: StackClient):
    client.set_scenario("llm", "malformed_chunk")
    _status, _headers, body = chat(client, stream=True)
    with pytest.raises(json.JSONDecodeError):
        json.loads(events(body)[0])


def embed(client: StackClient, text: str) -> dict[str, Any]:
    body = json.dumps({"model": "embed-small", "input": text}).encode()
    answer = client.api("/v1/embeddings", method="POST", host=HOST, body=body)
    assert answer.status == 200
    return answer.document()


def test_an_embedding_is_chosen_by_the_text_it_embeds(client: StackClient):
    refund, hours = embed(client, "desk pass refunds"), embed(client, "opening hours")
    assert refund["data"][0]["embedding"] != hours["data"][0]["embedding"]


def test_an_embedding_counts_the_words_it_embedded(client: StackClient):
    assert embed(client, "desk pass refunds")["usage"]["prompt_tokens"] == 3
