"""A mock server that passes requests through to an upstream, over real sockets on loopback: the
upstream is a tiny stand-in for a provider such as Keycloak."""

import base64
import http.client
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from tests.adapters.http_grader.raw_server import closed_port
from tests.mock_server_support import GENEROUS_WAIT_S, StackClient, write_config

FAST_POLL_S = 0.01
IDP = "idp:8080"
TOKEN_PATH = "/realms/pp3/protocol/openid-connect/token"
PAYLOAD = "eyJzdWIiOiJsZWFybmVyIn0"
ID_TOKEN = f"eyJhbGciOiJSUzI1NiJ9.{PAYLOAD}.c2lnbmF0dXJl"


@dataclass
class Heard:
    method: str
    target: str
    headers: dict[str, str]
    body: bytes


@dataclass
class StandInUpstream:
    """Answers every request with a token answer and two cookies, and keeps what it heard."""

    heard: list[Heard] = field(default_factory=list[Heard])

    def __post_init__(self) -> None:
        upstream = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                headers = {name.lower(): value for name, value in self.headers.items()}
                upstream.heard.append(
                    Heard(self.command, self.path, headers, self.rfile.read(length))
                )
                body = json.dumps({"access_token": "at", "id_token": ID_TOKEN}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", "AUTH_SESSION_ID=a1; Path=/realms/pp3/")
                self.send_header("Set-Cookie", "KC_RESTART=r1; Path=/realms/pp3/")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = _answer  # noqa: N815
            do_POST = _answer  # noqa: N815

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        threading.Thread(
            target=self._server.serve_forever, args=(FAST_POLL_S,), daemon=True
        ).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def idp_document(upstream_port: int) -> dict[str, Any]:
    return {
        "control_token": "sample-token",
        "mocks": {
            "idp": {
                "upstream": f"http://127.0.0.1:{upstream_port}",
                "routes": [{"id": "token", "method": "POST", "path": TOKEN_PATH}],
                "scenarios": {
                    "alg_none": {
                        "route": "token",
                        "jwt": {"field": "id_token", "tamper": "alg_none"},
                    },
                    "bad_signature": {
                        "route": "token",
                        "jwt": {"field": "id_token", "tamper": "bad_signature"},
                    },
                    "outage": {"route": "token", "status": 503, "body": {"error": "down"}},
                    "late": {"route": "token", "delay_ms": 1},
                },
            }
        },
    }


@pytest.fixture
def upstream() -> Iterator[StandInUpstream]:
    stand_in = StandInUpstream()
    yield stand_in
    stand_in.close()


def serve(tmp_path: Path, document: dict[str, Any]) -> Iterator[StackClient]:
    servers = start_servers(
        load_stack_config(write_config(tmp_path, document)),
        ListenOn("127.0.0.1", 0, 0),
        FAST_POLL_S,
    )
    yield StackClient(servers.api_port, servers.control_port)
    servers.close()


@pytest.fixture
def client(tmp_path: Path, upstream: StandInUpstream) -> Iterator[StackClient]:
    yield from serve(tmp_path, idp_document(upstream.port))


def post_token(client: StackClient, form: str = "grant_type=authorization_code&code=c1"):
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept-Encoding": "gzip"}
    return client.api(
        f"{TOKEN_PATH}?x=1", method="POST", host=IDP, body=form.encode(), headers=headers
    )


def id_token_of(answer: Any) -> str:
    return answer.document()["id_token"]


def header_of(token: str) -> Any:
    part = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def test_a_route_without_a_response_answers_with_the_upstreams_answer(client: StackClient):
    answer = post_token(client)
    assert (answer.status, id_token_of(answer)) == (200, ID_TOKEN)


def test_the_upstream_hears_the_request_as_it_came(client: StackClient, upstream: StandInUpstream):
    post_token(client)
    heard = upstream.heard[0]
    assert (heard.method, heard.target, heard.body, heard.headers["host"]) == (
        "POST",
        f"{TOKEN_PATH}?x=1",
        b"grant_type=authorization_code&code=c1",
        IDP,
    )


def test_the_upstream_is_asked_for_no_compression(client: StackClient, upstream: StandInUpstream):
    post_token(client)
    assert upstream.heard[0].headers["accept-encoding"] == "identity"


def test_every_cookie_the_upstream_sets_reaches_the_client(client: StackClient):
    assert set_cookies_of_a_token_answer(client) == [
        "AUTH_SESSION_ID=a1; Path=/realms/pp3/",
        "KC_RESTART=r1; Path=/realms/pp3/",
    ]


def set_cookies_of_a_token_answer(client: StackClient) -> list[str]:
    """Each `Set-Cookie` line apart, which `StackClient` would fold into one."""
    connection = http.client.HTTPConnection("127.0.0.1", client.api_port, timeout=GENEROUS_WAIT_S)
    try:
        connection.request("POST", TOKEN_PATH, body=b"", headers={"Host": IDP})
        response = connection.getresponse()
        response.read()
        return [value for name, value in response.getheaders() if name.lower() == "set-cookie"]
    finally:
        connection.close()


def test_a_passed_request_is_logged_under_its_route_with_the_upstreams_status(
    client: StackClient,
):
    post_token(client)
    entry = client.entries("idp")[0]
    assert (entry["route"], entry["status"], entry["body"]) == (
        "token",
        200,
        "grant_type=authorization_code&code=c1",
    )


def test_a_request_no_route_matches_passes_through_and_is_logged_without_a_route(
    client: StackClient, upstream: StandInUpstream
):
    answer = client.api("/realms/pp3/protocol/openid-connect/certs", host=IDP)
    entry = client.entries("idp")[0]
    assert (answer.status, upstream.heard[0].target, entry["route"], entry["matched"]) == (
        200,
        "/realms/pp3/protocol/openid-connect/certs",
        None,
        False,
    )


def test_alg_none_answers_the_upstreams_token_with_no_algorithm_and_no_signature(
    client: StackClient,
):
    client.set_scenario("idp", "alg_none")
    token = id_token_of(post_token(client))
    assert (header_of(token), token.split(".")[1:]) == ({"alg": "none"}, [PAYLOAD, ""])


def test_bad_signature_answers_the_upstreams_token_with_a_changed_signature(client: StackClient):
    client.set_scenario("idp", "bad_signature")
    header, payload, signature = id_token_of(post_token(client)).split(".")
    assert [header, payload, signature != ID_TOKEN.split(".")[2]] == [
        *ID_TOKEN.split(".")[:2],
        True,
    ]


def test_a_scenario_with_a_status_answers_alone_and_calls_no_upstream(
    client: StackClient, upstream: StandInUpstream
):
    client.set_scenario("idp", "outage")
    answer = post_token(client)
    assert (answer.status, answer.document(), upstream.heard) == (503, {"error": "down"}, [])


def test_a_scenario_with_only_a_delay_keeps_the_upstreams_answer(client: StackClient):
    client.set_scenario("idp", "late")
    assert id_token_of(post_token(client)) == ID_TOKEN


def test_an_upstream_that_does_not_answer_is_a_502_naming_it(tmp_path: Path):
    port = closed_port()
    for client in serve(tmp_path, idp_document(port)):
        answer = post_token(client)
        assert (answer.status, answer.document()["upstream"]) == (502, f"http://127.0.0.1:{port}")


def test_an_upstream_that_does_not_answer_is_logged_with_the_502(tmp_path: Path):
    for client in serve(tmp_path, idp_document(closed_port())):
        post_token(client)
        assert client.entries("idp")[0]["status"] == 502
