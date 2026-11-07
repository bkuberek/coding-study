import json
import socket
import threading
import time
from collections.abc import Iterator
from functools import partial
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.mock_server import http_server
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import (
    MAX_CONTROL_BODY_BYTES,
    MAX_REQUEST_BODY_BYTES,
    BoundedServer,
    ListenOn,
    start_servers,
)
from coding_study.adapters.mock_server.request_log import MAX_LOGGED_BODY_BYTES
from tests.mock_server_support import (
    GENEROUS_WAIT_S,
    SAMPLE_FOLDER,
    StackClient,
    exchange,
    has_no_answer_yet,
    sample_document,
    send_raw,
    wait_until,
    with_held_scenarios,
    write_config,
)

AVAILABILITY = "/v1/rooms/availability?date=2027-03-01"
AVAILABILITY_BODY = (SAMPLE_FOLDER / "bodies" / "availability.json").read_bytes()
FAST_POLL_S = 0.01
DRIP_S = 0.05
SHORT_REQUEST_LIMIT_S = 0.5
"""The limit under test."""
SAMPLE_SLOW_DELAY_MS = 60


@pytest.fixture
def client(tmp_path: Path) -> Iterator[StackClient]:
    config = load_stack_config(write_config(tmp_path, with_held_scenarios(sample_document())))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


def test_a_mock_server_answers_at_its_name(client: StackClient):
    answer = client.api(AVAILABILITY)
    assert (answer.status, answer.body, answer.headers["content-type"]) == (
        200,
        AVAILABILITY_BODY,
        "application/json",
    )


def test_a_host_without_a_port_names_it_too(client: StackClient):
    assert client.api(AVAILABILITY, host="room-vendor").status == 200


def test_a_host_in_another_case_names_it_too(client: StackClient):
    assert client.api(AVAILABILITY, host="Room-Vendor:8080").status == 200


def test_another_name_on_the_same_port_is_another_mock_server(client: StackClient):
    answer = client.api("/stock", host="second-vendor:8080")
    assert (answer.status, answer.document()) == (200, {"items": []})


def test_a_route_belongs_to_its_mock_server(client: StackClient):
    assert client.api("/stock").status == 404


def test_an_unknown_host_gets_a_404_listing_the_known_names(client: StackClient):
    answer = client.api("/stock", host="other:8080")
    assert (answer.status, answer.document()) == (
        404,
        {
            "error": "unknown mock server",
            "host": "other:8080",
            "known": ["room-vendor", "second-vendor"],
        },
    )


def test_a_request_without_a_host_gets_the_same_404(client: StackClient):
    raw = send_raw(client.api_port, b"GET /stock HTTP/1.0\r\n\r\n")
    assert raw.startswith(b"HTTP/1.0 404")
    assert b"second-vendor" in raw


def test_an_unmatched_request_gets_a_404_naming_the_mock_server(client: StackClient):
    answer = client.api("/v1/other")
    assert (answer.status, answer.document()) == (
        404,
        {"error": "no route", "mock": "room-vendor", "method": "GET", "path": "/v1/other"},
    )


def test_a_path_parameter_matches_over_http(client: StackClient):
    assert client.api("/v1/rooms/oak/slots").document() == {"slots": ["09:00", "10:00"]}


def test_the_first_matching_route_wins_over_http(client: StackClient):
    assert client.api("/v1/rooms/availability?date=2027-03-02").document() == {"rooms": []}


def test_a_mapping_body_is_sent_as_json_with_its_content_type(client: StackClient):
    assert client.api("/v1/rooms/oak/slots").headers["content-type"] == "application/json"


def test_an_answer_carries_its_length(client: StackClient):
    answer = client.api(AVAILABILITY)
    assert answer.headers["content-length"] == str(len(AVAILABILITY_BODY))


def test_an_answer_holds_no_clock_or_server_name(client: StackClient):
    assert not {"date", "server"} & client.api(AVAILABILITY).headers.keys()


def test_any_http_method_reaches_a_mock_server(client: StackClient):
    assert client.api("/v1/rooms", method="BREW").status == 404


def test_the_rate_limited_scenario_answers_429_with_retry_after(client: StackClient):
    client.set_scenario("room-vendor", "rate_limited")
    answer = client.api(AVAILABILITY)
    assert (answer.status, answer.headers["retry-after"], answer.body) == (429, "2", b"")


def test_the_outage_scenario_answers_503(client: StackClient):
    client.set_scenario("room-vendor", "outage")
    assert client.api(AVAILABILITY).status == 503


def test_the_malformed_scenario_sends_its_broken_body_as_it_is(client: StackClient):
    client.set_scenario("room-vendor", "malformed")
    answer = client.api(AVAILABILITY)
    assert (answer.status, answer.body) == (200, b'{"rooms": [')


def test_a_sequence_answers_in_order_and_repeats_its_last_entry(client: StackClient):
    client.set_scenario("room-vendor", "rate_limited_then_ok")
    statuses = [client.api(AVAILABILITY).status for _ in range(3)]
    assert statuses == [429, 200, 200]


def test_a_scenario_on_one_mock_server_leaves_another_alone(client: StackClient):
    client.set_scenario("room-vendor", "outage")
    assert client.api("/stock", host="second-vendor").status == 200


def test_the_slow_scenario_answers_no_sooner_than_its_delay(client: StackClient):
    client.set_scenario("room-vendor", "slow")
    started = time.monotonic()
    client.api(AVAILABILITY)
    assert time.monotonic() - started >= SAMPLE_SLOW_DELAY_MS / 1000


def test_a_slow_request_does_not_block_another_mock_server(client: StackClient):
    client.set_scenario("room-vendor", "held")
    with client.hold_a_request(AVAILABILITY, "room-vendor") as held:
        assert client.api("/stock", host="second-vendor").status == 200
        assert has_no_answer_yet(held)


def test_a_slow_request_does_not_block_its_own_mock_server(client: StackClient):
    client.set_scenario("room-vendor", "held")
    with client.hold_a_request(AVAILABILITY, "room-vendor") as held:
        client.set_scenario("room-vendor", None)
        assert client.api(AVAILABILITY).status == 200
        assert has_no_answer_yet(held)


def test_a_slow_request_does_not_block_the_control_port(client: StackClient):
    client.set_scenario("room-vendor", "held")
    with client.hold_a_request(AVAILABILITY, "room-vendor") as held:
        assert client.control("/health").status == 200
        assert has_no_answer_yet(held)


def test_a_request_being_answered_is_already_in_the_log(client: StackClient):
    client.set_scenario("room-vendor", "held")
    with client.hold_a_request(AVAILABILITY, "room-vendor"):
        entry = client.entries()[0]
    assert (entry["scenario"], entry["responded_ms"]) == ("held", None)


def test_a_wrong_token_gets_401(client: StackClient):
    assert client.control("/mocks/room-vendor/log", token="wrong").status == 401


def test_no_token_gets_401(client: StackClient):
    answer = exchange(client.control_port, ("GET", "/mocks/room-vendor/log"), {})
    assert answer.status == 401


def test_a_wrong_token_changes_no_scenario(client: StackClient):
    body = json.dumps({"scenario": "outage"}).encode()
    client.control("/mocks/room-vendor/scenario", method="PUT", token="wrong", body=body)
    assert client.api(AVAILABILITY).status == 200


def test_no_token_gets_its_401_before_any_body_comes(client: StackClient):
    """A body read first would let anyone hold one of the control port's few slots with it."""
    head = b"PUT /mocks/room-vendor/scenario HTTP/1.0\r\nContent-Length: 1000\r\n\r\n"
    with socket.create_connection(
        ("127.0.0.1", client.control_port), timeout=GENEROUS_WAIT_S
    ) as connection:
        connection.sendall(head)

        assert connection.recv(65536).startswith(b"HTTP/1.0 401")


def test_a_wrong_token_gets_its_401_before_any_body_comes(client: StackClient):
    head = (
        b"PUT /mocks/room-vendor/scenario HTTP/1.0\r\n"
        b"Authorization: Bearer wrong\r\nContent-Length: 1000\r\n\r\n"
    )
    with socket.create_connection(
        ("127.0.0.1", client.control_port), timeout=GENEROUS_WAIT_S
    ) as connection:
        connection.sendall(head)

        assert connection.recv(65536).startswith(b"HTTP/1.0 401")


def is_dropped_while_dripping(port: int, start: bytes) -> bool:
    """Sends `start`, then a byte at a time, more often than any limit on one read."""
    with socket.create_connection(("127.0.0.1", port), timeout=DRIP_S) as connection:
        connection.sendall(start)
        deadline = time.monotonic() + GENEROUS_WAIT_S
        while time.monotonic() < deadline:
            try:
                connection.sendall(b"a")
                if connection.recv(1) == b"":
                    return True
            except TimeoutError:
                continue
            except OSError:
                return True
    return False


@pytest.mark.parametrize(
    "start",
    [
        b"",
        b"GET /health HTTP/1.0\r\nX-Slow: ",
        (
            b"PUT /mocks/room-vendor/scenario HTTP/1.0\r\n"
            b"Authorization: Bearer sample-token\r\nContent-Length: 100000\r\n\r\n"
        ),
    ],
    ids=["request-line", "headers", "authorized-body"],
)
def test_a_control_request_that_drips_is_dropped_at_its_limit(tmp_path, monkeypatch, start):
    """A limit on each read would never run out here, and 4 such clients hold every slot."""
    monkeypatch.setattr(http_server, "SOCKET_TIMEOUT_S", SHORT_REQUEST_LIMIT_S)
    config = load_stack_config(write_config(tmp_path, sample_document()))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    try:
        assert is_dropped_while_dripping(servers.control_port, start)
    finally:
        servers.close()


def test_health_answers_on_the_control_port_without_a_token(client: StackClient):
    answer = exchange(client.control_port, ("GET", "/health"), {})
    assert (answer.status, answer.document()) == (200, {"status": "ok"})


def test_a_mocked_api_has_no_health_endpoint_of_its_own(client: StackClient):
    assert client.api("/health").document()["error"] == "no route"


def test_the_control_port_serves_no_mocked_route(client: StackClient):
    answer = exchange(
        client.control_port,
        ("GET", AVAILABILITY),
        {"Host": "room-vendor:8080", "Authorization": f"Bearer {client.token}"},
    )
    assert answer.status == 404


def test_a_scenario_cannot_be_set_through_the_mocked_api(client: StackClient):
    body = json.dumps({"scenario": "outage"}).encode()
    answer = client.api(
        "/mocks/room-vendor/scenario",
        method="PUT",
        body=body,
        headers={"Authorization": f"Bearer {client.token}"},
    )
    assert answer.status == 404
    assert client.api(AVAILABILITY).status == 200


def test_a_reset_cannot_be_sent_through_the_mocked_api(client: StackClient):
    client.set_scenario("room-vendor", "outage")
    client.api("/reset", method="POST", headers={"Authorization": f"Bearer {client.token}"})
    assert client.api(AVAILABILITY).status == 503


def test_a_log_cannot_be_read_through_the_mocked_api(client: StackClient):
    answer = client.api(
        "/mocks/room-vendor/log", headers={"Authorization": f"Bearer {client.token}"}
    )
    assert answer.document()["error"] == "no route"


def test_a_scenario_is_no_query_parameter_of_the_mocked_api(client: StackClient):
    assert client.api(f"{AVAILABILITY}&scenario=outage").status == 200


def test_a_reset_clears_the_log_and_restarts_a_sequence(client: StackClient):
    client.set_scenario("room-vendor", "rate_limited_then_ok")
    client.api(AVAILABILITY)
    client.control("/reset", method="POST")
    client.set_scenario("room-vendor", "rate_limited_then_ok")
    assert (client.entries(), client.api(AVAILABILITY).status) == ([], 429)


def test_a_reset_clears_the_scenario_over_http(client: StackClient):
    client.set_scenario("room-vendor", "outage")
    client.control("/reset", method="POST")
    assert client.api(AVAILABILITY).status == 200


def test_the_log_records_what_was_sent(client: StackClient):
    client.api(
        "/v1/bookings?date=2027-03-01&tag=a&tag=b",
        method="POST",
        body=b'{"room": "oak"}',
        headers={"X-Api-Key": "fake"},
    )
    entry = client.entries()[0]
    assert (entry["method"], entry["path"], entry["query"], entry["body"]) == (
        "POST",
        "/v1/bookings",
        {"date": "2027-03-01", "tag": ["a", "b"]},
        '{"room": "oak"}',
    )


def test_the_log_lowercases_header_names(client: StackClient):
    client.api(AVAILABILITY, headers={"X-Api-Key": "fake"})
    assert client.entries()[0]["headers"]["x-api-key"] == "fake"


def test_the_log_records_what_was_answered(client: StackClient):
    client.set_scenario("room-vendor", "outage")
    client.api(AVAILABILITY)
    entry = client.entries()[0]
    assert (entry["matched"], entry["route"], entry["scenario"], entry["status"]) == (
        True,
        "availability",
        "outage",
        503,
    )


def test_the_log_is_per_mock_server(client: StackClient):
    client.api(AVAILABILITY)
    assert client.entries("second-vendor") == []


def test_arrival_times_never_go_backwards(client: StackClient):
    for _ in range(3):
        client.api(AVAILABILITY)
    arrivals = [entry["received_ms"] for entry in client.entries()]
    assert arrivals == sorted(arrivals)


def test_a_finished_response_time_is_no_earlier_than_its_arrival(client: StackClient):
    client.api(AVAILABILITY)
    wait_until(lambda: client.entries()[0]["responded_ms"] is not None)
    entry = client.entries()[0]
    assert entry["responded_ms"] >= entry["received_ms"]


def test_a_delay_shows_between_arrival_and_response_in_the_log(client: StackClient):
    client.set_scenario("room-vendor", "slow")
    client.api(AVAILABILITY)
    wait_until(lambda: client.entries()[0]["responded_ms"] is not None)
    entry = client.entries()[0]
    rounding_ms = 1
    assert entry["responded_ms"] - entry["received_ms"] >= SAMPLE_SLOW_DELAY_MS - rounding_ms


def test_a_body_at_the_cap_is_served_and_its_log_entry_truncated(client: StackClient):
    body = b"a" * MAX_REQUEST_BODY_BYTES
    assert client.api("/v1/bookings", method="POST", body=body).status == 201
    entry = client.entries()[0]
    assert (len(entry["body"]), entry["truncated"]) == (MAX_LOGGED_BODY_BYTES, True)


def test_a_body_past_the_cap_gets_413(client: StackClient):
    body = b"a" * (MAX_REQUEST_BODY_BYTES + 1)
    assert client.api("/v1/bookings", method="POST", body=body).status == 413


def test_a_body_past_the_cap_is_logged_without_its_body(client: StackClient):
    body = b"a" * (MAX_REQUEST_BODY_BYTES + 1)
    client.api("/v1/bookings", method="POST", body=body)
    entry = client.entries()[0]
    assert (entry["matched"], entry["status"], entry["body"]) == (False, 413, None)


def test_a_body_past_the_cap_does_not_advance_a_sequence(client: StackClient):
    client.set_scenario("room-vendor", "rate_limited_then_ok")
    client.api("/v1/bookings", method="POST", body=b"a" * (MAX_REQUEST_BODY_BYTES + 1))
    assert client.api(AVAILABILITY).status == 429


@pytest.mark.parametrize("length", [b"many", b"-1", b"1 2"])
def test_a_bad_content_length_gets_400(client: StackClient, length: bytes):
    raw = send_raw(
        client.api_port,
        b"POST /v1/bookings HTTP/1.1\r\nHost: room-vendor\r\nContent-Length: "
        + length
        + b"\r\n\r\n",
    )
    assert raw.startswith(b"HTTP/1.0 400")


def test_a_chunked_body_gets_411(client: StackClient):
    raw = send_raw(
        client.api_port,
        b"POST /v1/bookings HTTP/1.1\r\nHost: room-vendor\r\nTransfer-Encoding: chunked\r\n\r\n"
        b"1\r\na\r\n0\r\n\r\n",
    )
    assert raw.startswith(b"HTTP/1.0 411")


def test_a_control_body_past_its_cap_gets_413(client: StackClient):
    body = b"a" * (MAX_CONTROL_BODY_BYTES + 1)
    answer = client.control("/mocks/room-vendor/scenario", method="PUT", body=body)
    assert answer.status == 413


def test_a_request_line_that_is_not_http_gets_a_json_error(client: StackClient):
    raw = send_raw(client.api_port, b"nonsense\r\n\r\n")
    assert "Bad request" in json.loads(raw)["error"]


def test_a_request_line_past_the_limit_gets_a_json_414(client: StackClient):
    line_past_the_limit = b"GET /" + b"a" * (65537 - len(b"GET /"))
    raw = send_raw(client.api_port, line_past_the_limit)
    assert raw.startswith(b"HTTP/1.0 414")
    assert b"application/json" in raw


def raw_answer_of_route(folder: Path, route: dict[str, Any], request: bytes) -> bytes:
    """The bytes a mock server sends to `request`, with `route` added to the sample's."""
    document = sample_document()
    document["mocks"]["room-vendor"]["routes"].append(route)
    config = load_stack_config(write_config(folder, document))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    try:
        return send_raw(servers.api_port, request)
    finally:
        servers.close()


def test_head_sends_its_length_and_no_body(tmp_path: Path):
    route = {
        "id": "ping",
        "method": "HEAD",
        "path": "/ping",
        "response": {"status": 200, "body": "x"},
    }
    raw = raw_answer_of_route(tmp_path, route, b"HEAD /ping HTTP/1.1\r\nHost: room-vendor\r\n\r\n")
    assert raw.endswith(b"Content-Length: 1\r\n\r\n")


def test_204_sends_no_body_or_length(tmp_path: Path):
    route = {
        "id": "gone",
        "method": "DELETE",
        "path": "/x",
        "response": {"status": 204, "body": "x"},
    }
    raw = raw_answer_of_route(tmp_path, route, b"DELETE /x HTTP/1.1\r\nHost: room-vendor\r\n\r\n")
    assert raw == b"HTTP/1.0 204 No Content\r\n\r\n"


def test_an_authors_content_length_is_sent_as_it_is(tmp_path: Path):
    route = {
        "id": "lying",
        "method": "GET",
        "path": "/lying",
        "response": {"status": 200, "headers": {"Content-Length": "99"}, "body": "x"},
    }
    raw = raw_answer_of_route(tmp_path, route, b"GET /lying HTTP/1.1\r\nHost: room-vendor\r\n\r\n")
    assert raw == b"HTTP/1.0 200 OK\r\nContent-Length: 99\r\n\r\nx"


def test_a_client_that_left_does_not_stop_the_server(client: StackClient):
    client.set_scenario("room-vendor", "slow")
    with socket.create_connection(("127.0.0.1", client.api_port), timeout=GENEROUS_WAIT_S) as gone:
        gone.sendall(f"GET {AVAILABILITY} HTTP/1.1\r\nHost: room-vendor\r\n\r\n".encode())
        wait_until(lambda: len(client.entries()) == 1)
    wait_until(lambda: client.entries()[0]["responded_ms"] is not None)
    client.set_scenario("room-vendor", None)
    assert client.api(AVAILABILITY).status == 200


class _GatedHandler(BaseHTTPRequestHandler):
    """Holds each connection until the test opens the gate, counting those it has let in."""

    def __init__(self, gate: "_Gate", *args) -> None:
        self._gate = gate
        super().__init__(*args)

    def do_GET(self) -> None:
        self._gate.enter()
        self.send_response_only(204)
        self.end_headers()


class _Gate:
    def __init__(self) -> None:
        self._opened = threading.Event()
        self._lock = threading.Lock()
        self.entered = 0

    def enter(self) -> None:
        with self._lock:
            self.entered += 1
        assert self._opened.wait(GENEROUS_WAIT_S)

    def open(self) -> None:
        self._opened.set()


def test_connections_past_the_limit_wait_their_turn():
    gate = _Gate()
    server = BoundedServer(("127.0.0.1", 0), partial(_GatedHandler, gate), max_connections=1)
    serving = threading.Thread(target=server.serve_forever, args=(FAST_POLL_S,), daemon=True)
    serving.start()
    port = server.server_address[1]
    request = b"GET / HTTP/1.0\r\n\r\n"
    first = socket.create_connection(("127.0.0.1", port), timeout=GENEROUS_WAIT_S)
    second = socket.create_connection(("127.0.0.1", port), timeout=GENEROUS_WAIT_S)
    try:
        first.sendall(request)
        wait_until(lambda: gate.entered == 1)
        second.sendall(request)
        time.sleep(FAST_POLL_S * 5)
        held_back = gate.entered == 1
        gate.open()
        assert held_back
        wait_until(lambda: gate.entered == 2)
    finally:
        gate.open()
        first.close()
        second.close()
        server.shutdown()
        server.server_close()
