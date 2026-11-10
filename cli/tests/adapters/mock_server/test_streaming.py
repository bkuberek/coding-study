"""A streamed answer over real sockets on loopback: its events, its timing, and a scenario that
drops or stalls it."""

import json
import socket
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from tests.mock_server_support import (
    GENEROUS_WAIT_S,
    SAMPLE_TOKEN,
    StackClient,
    has_no_answer_yet,
    send_raw,
    wait_until,
)

FAST_POLL_S = 0.01
GAP_MS = 100
"""The wait between the first two events; a test asserts only that it is at least this long."""
QUIET_S = 0.2
"""How long a stalled stream is watched for one more event that must not come."""
CHAT_REQUEST = b"POST /v1/chat HTTP/1.1\r\nHost: llm:8080\r\nContent-Length: 2\r\n\r\n{}"
WHOLE_STREAM = b"data: one\n\ndata: two\n\ndata: [DONE]\n\n"


def streaming_document() -> dict[str, Any]:
    stream = [{"data": "one"}, {"data": "two", "after_ms": GAP_MS}, {"data": "[DONE]"}]
    return {
        "control_token": SAMPLE_TOKEN,
        "mocks": {
            "llm": {
                "routes": [
                    {
                        "id": "chat",
                        "method": "POST",
                        "path": "/v1/chat",
                        "response": {"status": 200, "stream": stream},
                    }
                ],
                "scenarios": {
                    "dropped": {"drop_after_chunks": 1},
                    "stalled": {"stall_after_chunks": 1},
                },
            }
        },
    }


@pytest.fixture
def client(tmp_path: Path) -> Iterator[StackClient]:
    path = tmp_path / "mocks.json"
    path.write_text(json.dumps(streaming_document()))
    servers = start_servers(load_stack_config(path), ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


def chat(client: StackClient) -> bytes:
    """What the mock server sends, up to its closing the connection, without the head."""
    return send_raw(client.api_port, CHAT_REQUEST).partition(b"\r\n\r\n")[2]


def read_until(connection: socket.socket, marker: bytes) -> bytes:
    received = b""
    while marker not in received:
        chunk = connection.recv(65536)
        assert chunk, f"the connection closed before {marker!r}"
        received += chunk
    return received


def test_a_stream_arrives_as_server_sent_events(client: StackClient):
    assert chat(client) == WHOLE_STREAM


def test_a_stream_says_it_is_one_and_gives_no_length(client: StackClient):
    answer = client.api("/v1/chat", method="POST", host="llm:8080", body=b"{}")
    assert (answer.headers["content-type"], "content-length" in answer.headers) == (
        "text/event-stream",
        False,
    )


def test_an_event_waits_its_after_ms(client: StackClient):
    with socket.create_connection(("127.0.0.1", client.api_port), GENEROUS_WAIT_S) as connection:
        connection.sendall(CHAT_REQUEST)
        read_until(connection, b"data: one\n\n")
        first_at = time.monotonic()
        read_until(connection, b"data: two\n\n")
        assert (time.monotonic() - first_at) * 1000 >= GAP_MS * 0.9


def test_a_drop_closes_the_connection_after_its_chunks(client: StackClient):
    client.set_scenario("llm", "dropped")
    assert chat(client) == b"data: one\n\n"


def test_a_stall_holds_the_connection_open_after_its_chunks(client: StackClient):
    client.set_scenario("llm", "stalled")
    with socket.create_connection(("127.0.0.1", client.api_port), GENEROUS_WAIT_S) as connection:
        connection.sendall(CHAT_REQUEST)
        read_until(connection, b"data: one\n\n")
        time.sleep(QUIET_S)
        assert has_no_answer_yet(connection)


def test_a_stall_ends_when_the_app_closes_the_connection(client: StackClient):
    client.set_scenario("llm", "stalled")
    with socket.create_connection(("127.0.0.1", client.api_port), GENEROUS_WAIT_S) as connection:
        connection.sendall(CHAT_REQUEST)
        read_until(connection, b"data: one\n\n")
    wait_until(lambda: client.entries("llm")[0]["responded_ms"] is not None)


def test_a_stream_is_logged_as_answered_once_it_ends(client: StackClient):
    chat(client)
    (entry,) = client.entries("llm")
    assert (entry["status"], entry["responded_ms"] is not None) == (200, True)
