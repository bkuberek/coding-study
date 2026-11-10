import socket
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from coding_study.adapters.http_grader.clients import (
    MAX_RESPONSE_BYTES,
    HttpAppClient,
    HttpMockControl,
    open_stack_clients,
)
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from coding_study.application.http_grading_ports import StackEndpoints
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import ExchangeFailed, ExchangeFailure, HttpResponse, MockLog
from tests.adapters.http_grader.raw_server import RawServer, closed_port, raw_server
from tests.mock_server_support import (
    GENEROUS_WAIT_S,
    SAMPLE_TOKEN,
    StackClient,
    sample_document,
    write_config,
)

ROOM_VENDOR = "room-vendor"
AVAILABILITY_TARGET = "/v1/rooms/availability?date=2027-03-01"
GENEROUS_LIMIT_MS = int(GENEROUS_WAIT_S * 1000)
SHORT_LIMIT_MS = 100
"""A case's limit in a test that waits it out: a test about a limit stays this strict."""
DRIP_INTERVAL_S = 0.01
FAST_POLL_S = 0.01
GET_A = HttpRequest("GET", "/a")
OK = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"


def app_at(server: RawServer) -> HttpAppClient:
    return HttpAppClient(f"http://127.0.0.1:{server.port}")


def answering(reply: bytes):
    def handler(server: RawServer, connection: socket.socket) -> None:
        server.read_request(connection)
        connection.sendall(reply)

    return handler


def failure_of(sent: HttpResponse | ExchangeFailed) -> ExchangeFailure:
    assert isinstance(sent, ExchangeFailed), sent
    return sent.failure


def test_an_answer_keeps_its_status_and_body():
    with raw_server(answering(OK)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert (sent.status, sent.body) == (200, b"ok")


def test_a_header_is_found_by_its_lowercase_name():
    reply = b"HTTP/1.1 204 No Content\r\nX-Trace: 1\r\n\r\n"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.headers["x-trace"] == "1"


def test_a_repeated_header_is_joined():
    reply = b"HTTP/1.1 204 No Content\r\nX-Tag: a\r\nX-Tag: b\r\n\r\n"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.headers["x-tag"] == "a, b"


def test_a_chunked_body_is_read_whole():
    reply = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\nok\r\n0\r\n\r\n"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.body == b"ok"


def test_a_body_that_ends_with_the_connection_is_read_whole():
    reply = b"HTTP/1.0 200 OK\r\n\r\nall of it"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.body == b"all of it"


def test_an_answer_says_how_long_it_took():
    with raw_server(answering(OK)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.duration_ns > 0


BODY_DELAY_S = 0.2
"""How long a server holds back its body after its headers: a lower bound, kept on any machine."""


def body_held_back(server: RawServer, connection: socket.socket) -> None:
    server.read_request(connection)
    connection.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
    server.stopping.wait(BODY_DELAY_S)
    connection.sendall(b"2\r\nok\r\n0\r\n\r\n")


def test_an_answer_says_when_its_first_body_byte_came_not_its_headers():
    with raw_server(body_held_back) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert sent.first_byte_ns >= BODY_DELAY_S * 1_000_000_000


def test_an_empty_body_s_first_byte_is_the_end_of_the_answer():
    reply = b"HTTP/1.1 204 No Content\r\n\r\n"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert 0 < sent.first_byte_ns <= sent.duration_ns


def test_the_request_goes_out_as_the_case_says():
    request = HttpRequest("POST", "/bookings", {"date": "2027-03-01"}, {"X-Member": "m1"}, b"{}")
    with raw_server(answering(OK)) as server:
        app_at(server).send(request, GENEROUS_LIMIT_MS)
    sent = server.received[0]
    assert sent.startswith(b"POST /bookings?date=2027-03-01 HTTP/1.1\r\n")
    assert b"X-Member: m1\r\n" in sent


def test_a_malformed_body_goes_out_byte_for_byte():
    malformed = b'{"member": '
    request = HttpRequest("POST", "/bookings", body=malformed)
    with raw_server(answering(OK)) as server:
        app_at(server).send(request, GENEROUS_LIMIT_MS)
    assert server.received[0].endswith(b"\r\n\r\n" + malformed)


def test_a_body_with_no_bytes_is_still_a_body():
    request = HttpRequest("POST", "/bookings", body=b"")
    with raw_server(answering(OK)) as server:
        app_at(server).send(request, GENEROUS_LIMIT_MS)
    assert b"Content-Length: 0\r\n" in server.received[0]


def test_nothing_listening_is_a_refused_connection():
    client = HttpAppClient(f"http://127.0.0.1:{closed_port()}")
    assert failure_of(client.send(GET_A, GENEROUS_LIMIT_MS)) is ExchangeFailure.REFUSED


def test_a_refused_connection_says_where_it_tried():
    port = closed_port()
    sent = HttpAppClient(f"http://127.0.0.1:{port}").send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, ExchangeFailed)
    assert f"127.0.0.1:{port}/a" in sent.detail


def test_an_app_that_closes_without_answering_dropped_the_connection():
    def handler(server: RawServer, connection: socket.socket) -> None:
        server.read_request(connection)

    with raw_server(handler) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.DROPPED


def test_a_body_cut_short_of_its_length_dropped_the_connection():
    reply = b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nabc"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.DROPPED


def test_a_chunked_body_cut_short_dropped_the_connection():
    reply = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nab"
    with raw_server(answering(reply)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.DROPPED


def test_an_answer_that_is_not_http_says_so():
    with raw_server(answering(b"hello there\r\n\r\n")) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.NOT_HTTP


def test_a_body_past_the_limit_is_too_large():
    head = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % (MAX_RESPONSE_BYTES + 1)
    with raw_server(answering(head + b"x" * (MAX_RESPONSE_BYTES + 1))) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.TOO_LARGE


def test_a_body_at_the_limit_is_kept():
    head = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % MAX_RESPONSE_BYTES
    with raw_server(answering(head + b"x" * MAX_RESPONSE_BYTES)) as server:
        sent = app_at(server).send(GET_A, GENEROUS_LIMIT_MS)
    assert isinstance(sent, HttpResponse)
    assert len(sent.body) == MAX_RESPONSE_BYTES


def holding(server: RawServer, connection: socket.socket) -> None:
    server.read_request(connection)
    server.stopping.wait(GENEROUS_WAIT_S)


def test_an_app_that_never_answers_times_out():
    with raw_server(holding) as server:
        sent = app_at(server).send(GET_A, SHORT_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.TIMED_OUT


def test_a_timeout_comes_no_earlier_than_the_limit():
    with raw_server(holding) as server:
        sent = app_at(server).send(GET_A, SHORT_LIMIT_MS)
    assert isinstance(sent, ExchangeFailed)
    assert sent.duration_ns >= SHORT_LIMIT_MS * 1_000_000


def dripping(prefix: bytes):
    """Sends `prefix`, then a byte at a time far past the limit: no single read waits long, so only
    a limit on the whole exchange can stop it. It ends, so that a client without one fails here on
    what it got back instead of hanging the test."""

    def handler(server: RawServer, connection: socket.socket) -> None:
        server.read_request(connection)
        connection.sendall(prefix)
        give_up_at = time.monotonic() + GENEROUS_WAIT_S
        while not server.stopping.wait(DRIP_INTERVAL_S) and time.monotonic() < give_up_at:
            connection.sendall(b"x")

    return handler


def test_a_slow_drip_of_headers_cannot_outlast_the_limit():
    with raw_server(dripping(b"HTTP/1.1 200 OK\r\nX-Slow: ")) as server:
        sent = app_at(server).send(GET_A, SHORT_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.TIMED_OUT


def test_a_slow_drip_of_body_cannot_outlast_the_limit():
    with raw_server(dripping(b"HTTP/1.1 200 OK\r\nContent-Length: 999\r\n\r\n")) as server:
        sent = app_at(server).send(GET_A, SHORT_LIMIT_MS)
    assert failure_of(sent) is ExchangeFailure.TIMED_OUT


def test_the_shortest_limit_still_answers_with_a_verdict():
    with raw_server(holding) as server:
        sent = app_at(server).send(GET_A, 1)
    assert failure_of(sent) is ExchangeFailure.TIMED_OUT


def test_no_time_left_times_out_without_connecting():
    client = HttpAppClient(f"http://127.0.0.1:{closed_port()}")
    assert failure_of(client.send(GET_A, 0)) is ExchangeFailure.TIMED_OUT


@pytest.fixture
def mock_servers(tmp_path: Path) -> Iterator[StackClient]:
    config = load_stack_config(write_config(tmp_path, sample_document()))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


def control_of(mock_servers: StackClient, token: str = SAMPLE_TOKEN) -> HttpMockControl:
    return HttpMockControl(f"http://127.0.0.1:{mock_servers.control_port}", token)


def test_a_scenario_set_takes_effect(mock_servers: StackClient):
    assert control_of(mock_servers).set_scenario(ROOM_VENDOR, "outage") is True
    assert mock_servers.api(AVAILABILITY_TARGET).status == 503


def test_an_unknown_scenario_says_so(mock_servers: StackClient):
    assert control_of(mock_servers).set_scenario(ROOM_VENDOR, "no-such") is False


def test_a_reset_clears_the_scenario(mock_servers: StackClient):
    control = control_of(mock_servers)
    control.set_scenario(ROOM_VENDOR, "outage")
    control.reset()
    assert mock_servers.api(AVAILABILITY_TARGET).status == 200


def test_a_log_holds_each_request_with_its_route_and_times(mock_servers: StackClient):
    mock_servers.api(AVAILABILITY_TARGET)
    log = control_of(mock_servers).log(ROOM_VENDOR)
    entry = log.entries[0]
    assert (entry.route, entry.received_ms >= 0, entry.responded_ms is not None) == (
        "availability",
        True,
        True,
    )


def test_a_request_no_route_matched_has_no_route(mock_servers: StackClient):
    mock_servers.api("/v1/other")
    assert control_of(mock_servers).log(ROOM_VENDOR).entries[0].route is None


def test_a_reset_clears_the_log(mock_servers: StackClient):
    mock_servers.api(AVAILABILITY_TARGET)
    control = control_of(mock_servers)
    control.reset()
    assert control.log(ROOM_VENDOR) == MockLog()


def test_a_wrong_token_is_a_stack_failure_that_keeps_the_token_to_itself(
    mock_servers: StackClient,
):
    with pytest.raises(RunnerStartError) as raised:
        control_of(mock_servers, token="wrong-token").reset()
    assert "wrong-token" not in str(raised.value)


def test_a_control_interface_that_is_gone_is_a_stack_failure():
    control = HttpMockControl(f"http://127.0.0.1:{closed_port()}", SAMPLE_TOKEN)
    with pytest.raises(RunnerStartError, match="control interface"):
        control.reset()


def test_clients_open_at_a_stacks_endpoints(mock_servers: StackClient):
    endpoints = StackEndpoints(
        app_url=f"http://127.0.0.1:{closed_port()}",
        control_url=f"http://127.0.0.1:{mock_servers.control_port}",
        control_token=SAMPLE_TOKEN,
        mocks=(ROOM_VENDOR,),
    )
    clients = open_stack_clients(endpoints)
    assert clients.mocks.set_scenario(ROOM_VENDOR, "outage") is True
    assert failure_of(clients.app.send(GET_A, GENEROUS_LIMIT_MS)) is ExchangeFailure.REFUSED


def test_a_stack_without_mock_servers_has_nothing_to_reset():
    endpoints = StackEndpoints(f"http://127.0.0.1:{closed_port()}", None, "", ())
    open_stack_clients(endpoints).mocks.reset()


def test_a_stack_without_mock_servers_has_no_scenario():
    endpoints = StackEndpoints(f"http://127.0.0.1:{closed_port()}", None, "", ())
    assert open_stack_clients(endpoints).mocks.set_scenario(ROOM_VENDOR, "outage") is False
