"""The grader's client as a browser, on loopback: origins by name, cookie jars and redirects."""

import re
import socket
from collections.abc import Callable
from pathlib import Path

from coding_study.adapters.http_grader.clients import HttpAppClient, HttpMockControl
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from coding_study.application.http_grading_ports import StackEndpoints
from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import HttpResponse
from tests.adapters.http_grader.raw_server import RawServer, raw_server
from tests.mock_server_support import GENEROUS_WAIT_S, SAMPLE_TOKEN, sample_document, write_config

GENEROUS_LIMIT_MS = int(GENEROUS_WAIT_S * 1000)
APP = "http://app:8000"
IDP = "http://idp:8080"
FAST_POLL_S = 0.01

type Reply = Callable[[bytes], bytes]


def replying(reply: Reply):
    def handler(server: RawServer, connection: socket.socket) -> None:
        connection.sendall(reply(server.read_request(connection)))

    return handler


def answer(status: str, *headers: str, body: str = "") -> bytes:
    lines = [f"HTTP/1.1 {status}", *headers, f"Content-Length: {len(body)}", "", body]
    return "\r\n".join(lines).encode()


def header_of(request: bytes, name: str) -> str | None:
    found = re.search(rf"^{name}: (.*)\r$", request.decode(), re.IGNORECASE | re.MULTILINE)
    return found[1] if found else None


def client_for(app: RawServer, idp: RawServer | None = None) -> HttpAppClient:
    origins = {IDP: f"http://127.0.0.1:{idp.port}"} if idp is not None else {}
    endpoints = StackEndpoints(f"http://127.0.0.1:{app.port}", None, "", (), APP, origins)
    return HttpAppClient(endpoints.app_url, endpoints)


def sent(client: HttpAppClient, request: HttpRequest) -> HttpResponse:
    response = client.send(request, GENEROUS_LIMIT_MS)
    assert isinstance(response, HttpResponse), response
    return response


def sets_cookie(cookie: str) -> Reply:
    return lambda _request: answer("200 OK", f"Set-Cookie: {cookie}")


def test_a_request_to_a_named_origin_goes_to_its_address_with_its_name_as_host():
    with (
        raw_server(replying(lambda _r: answer("200 OK"))) as app,
        raw_server(replying(lambda _r: answer("204 No Content"))) as idp,
    ):
        response = sent(client_for(app, idp), HttpRequest("GET", "/auth", origin=IDP))
        assert (response.status, header_of(idp.received[0], "Host")) == (204, "idp:8080")


def test_a_path_alone_still_goes_to_the_app_as_it_always_has():
    with raw_server(replying(lambda _r: answer("200 OK"))) as app:
        sent(client_for(app), HttpRequest("GET", "/a"))
        assert header_of(app.received[0], "Host") == f"127.0.0.1:{app.port}"


def test_the_apps_own_origin_reaches_the_app():
    with raw_server(replying(lambda _r: answer("200 OK"))) as app:
        sent(client_for(app), HttpRequest("GET", "/callback", origin=APP))
        assert header_of(app.received[0], "Host") == "app:8000"


def test_a_cookie_the_app_sets_goes_back_on_the_next_request_of_the_jar():
    with raw_server(replying(sets_cookie("session=s1; Path=/; HttpOnly"))) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        sent(client, HttpRequest("GET", "/me", jar="main"))
        assert header_of(app.received[1], "Cookie") == "session=s1"


def test_a_path_alone_and_the_apps_origin_share_their_cookies():
    with raw_server(replying(sets_cookie("state=st; Path=/"))) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        sent(client, HttpRequest("GET", "/callback", origin=APP, jar="main"))
        assert header_of(app.received[1], "Cookie") == "state=st"


def test_another_jar_is_another_browser():
    with raw_server(replying(sets_cookie("session=s1; Path=/"))) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        sent(client, HttpRequest("GET", "/me", jar="second"))
        assert header_of(app.received[1], "Cookie") is None


def test_a_request_with_no_jar_sends_and_keeps_no_cookies():
    with raw_server(replying(sets_cookie("session=s1; Path=/"))) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login"))
        sent(client, HttpRequest("GET", "/me", jar="main"))
        assert header_of(app.received[1], "Cookie") is None


def test_cookies_stay_with_their_origin():
    with (
        raw_server(replying(sets_cookie("session=s1; Path=/"))) as app,
        raw_server(replying(lambda _r: answer("200 OK"))) as idp,
    ):
        client = client_for(app, idp)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        sent(client, HttpRequest("GET", "/auth", origin=IDP, jar="main"))
        assert header_of(idp.received[0], "Cookie") is None


def test_a_cookie_under_a_path_goes_only_below_it():
    with (
        raw_server(replying(sets_cookie("AUTH=a1; Path=/realms/pp3/"))) as idp,
        raw_server(replying(lambda _r: answer("200 OK"))) as app,
    ):
        client = client_for(app, idp)
        sent(client, HttpRequest("GET", "/realms/pp3/auth", origin=IDP, jar="main"))
        sent(client, HttpRequest("GET", "/realms/other", origin=IDP, jar="main"))
        sent(client, HttpRequest("POST", "/realms/pp3/login", origin=IDP, jar="main"))
        cookies = [header_of(request, "Cookie") for request in idp.received[1:]]
        assert cookies == [None, "AUTH=a1"]


def test_every_cookie_of_an_answer_is_kept():
    def two_cookies(_request: bytes) -> bytes:
        return answer("200 OK", "Set-Cookie: a=1; Path=/", "Set-Cookie: b=2; Path=/")

    with raw_server(replying(two_cookies)) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        sent(client, HttpRequest("GET", "/me", jar="main"))
        assert header_of(app.received[1], "Cookie") in ("a=1; b=2", "b=2; a=1")


def test_clearing_the_cookies_empties_every_jar():
    with raw_server(replying(sets_cookie("session=s1; Path=/"))) as app:
        client = client_for(app)
        sent(client, HttpRequest("GET", "/login", jar="main"))
        client.clear_cookies()
        sent(client, HttpRequest("GET", "/me", jar="main"))
        assert header_of(app.received[1], "Cookie") is None


def redirecting_once(location: str) -> Reply:
    def reply(request: bytes) -> bytes:
        if request.startswith(b"GET /start"):
            return answer("302 Found", f"Location: {location}", "Set-Cookie: hop=1; Path=/")
        return answer("200 OK", body="arrived")

    return reply


def test_a_step_that_follows_redirects_answers_with_where_they_end():
    with raw_server(replying(redirecting_once("/end"))) as app:
        request = HttpRequest("GET", "/start", jar="main", follow_redirects=True)
        response = sent(client_for(app), request)
        assert (response.status, response.body, header_of(app.received[1], "Cookie")) == (
            200,
            b"arrived",
            "hop=1",
        )


def test_a_step_that_follows_no_redirects_answers_with_the_redirect():
    with raw_server(replying(redirecting_once("/end"))) as app:
        response = sent(client_for(app), HttpRequest("GET", "/start"))
        assert (response.status, response.headers["location"]) == (302, "/end")


def test_a_redirect_to_an_origin_the_stack_does_not_publish_is_not_followed():
    with raw_server(replying(redirecting_once("http://evil:80/steal"))) as app:
        request = HttpRequest("GET", "/start", follow_redirects=True)
        response = sent(client_for(app), request)
        assert (response.status, len(app.received)) == (302, 1)


def test_a_redirect_to_a_named_origin_goes_to_its_address():
    with (
        raw_server(replying(lambda _r: answer("200 OK", body="idp"))) as idp,
        raw_server(replying(redirecting_once(f"{IDP}/auth"))) as app,
    ):
        request = HttpRequest("GET", "/start", follow_redirects=True)
        response = sent(client_for(app, idp), request)
        assert (response.body, header_of(idp.received[0], "Host")) == (b"idp", "idp:8080")


def test_a_mock_servers_log_carries_each_requests_headers_and_body(tmp_path: Path):
    config = load_stack_config(write_config(tmp_path, sample_document()))
    servers = start_servers(config, ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    try:
        mock = f"http://127.0.0.1:{servers.api_port}"
        endpoints = StackEndpoints(mock, None, "", (), None, {"http://room-vendor:8080": mock})
        booking = HttpRequest(
            "POST", "/v1/bookings", body=b"room=oak", origin="http://room-vendor:8080"
        )
        HttpAppClient(mock, endpoints).send(booking, GENEROUS_LIMIT_MS)
        control = HttpMockControl(f"http://127.0.0.1:{servers.control_port}", SAMPLE_TOKEN)
        entry = control.log("room-vendor").entries[0]
        assert (entry.body, entry.headers["host"], entry.truncated) == (
            "room=oak",
            "room-vendor:8080",
            False,
        )
    finally:
        servers.close()
