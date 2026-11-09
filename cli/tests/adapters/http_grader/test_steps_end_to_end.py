"""A login flow graded end to end on loopback, with no container: the real mock server stands in
front of a stand-in identity provider and passes its token endpoint through, a stand-in app logs in
against it, and multi-step cases from a tests.json document drive both as a browser would.

Each flaw switched on in the app must fail exactly the case written for it: a forged state, a token
spoiled to `alg: none` in flight, and tokens or codes printed to the app's output.
"""

import base64
import http.client
import json
import secrets
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from coding_study.adapters.http_grader.clients import open_stack_clients
from coding_study.adapters.mock_server.config import load_stack_config
from coding_study.adapters.mock_server.http_server import ListenOn, start_servers
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from tests.adapters.http_grader.standin_app import (
    APP_ORIGIN,
    AppAnswer,
    AppRequest,
    StandInApp,
    StandInStack,
)
from tests.mock_server_support import GENEROUS_WAIT_S, SAMPLE_TOKEN
from tests.project_builders import project_meta

IDP = "idp"
IDP_ORIGIN = "http://idp:8080"
FAST_POLL_S = 0.01
GOOD_SIGNATURE = "c2lnbmVkLWJ5LXRoZS1wcm92aWRlcg"
"""What the stand-in provider signs every token with; the stand-in app checks it as a real one
would check a signature against the provider's key."""
PASSWORD = "learner-pass"


def segment(document: dict[str, Any]) -> str:
    raw = json.dumps(document, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decoded(part: str) -> Any:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


@dataclass
class StandInProvider:
    """An identity provider in miniature: a login form behind a session cookie, a redirect back to
    the app with a single-use code, and a token endpoint that signs."""

    codes: set[str] = field(default_factory=set[str])

    def __post_init__(self) -> None:
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                state = parse_qs(urlsplit(self.path).query)["state"][0]
                action = f"{IDP_ORIGIN}/login?session=s1&amp;state={state}"
                page = f'<form id="kc-form-login" method="post" action="{action}"></form>'
                self._reply(200, page.encode(), {"Set-Cookie": "AUTH_SESSION=as1; Path=/"})

            def do_POST(self) -> None:
                fields = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
                if self.path.startswith("/login"):
                    self._logged_in(fields)
                else:
                    self._token(fields)

            def _logged_in(self, fields: dict[str, list[str]]) -> None:
                if self.headers.get("Cookie") != "AUTH_SESSION=as1":
                    self._reply(400, b"no login session")
                    return
                if fields["password"] != [PASSWORD]:
                    self._reply(200, b"wrong password")
                    return
                code = secrets.token_hex(4)
                provider.codes.add(code)
                state = parse_qs(urlsplit(self.path).query)["state"][0]
                back = f"{APP_ORIGIN}/callback?{urlencode({'state': state, 'code': code})}"
                self._reply(302, b"", {"Location": back})

            def _token(self, fields: dict[str, list[str]]) -> None:
                code = fields["code"][0]
                if code not in provider.codes:
                    self._reply(400, b'{"error": "invalid_grant"}')
                    return
                provider.codes.discard(code)
                header = segment({"alg": "RS256", "typ": "JWT"})
                token = f"{header}.{segment({'sub': 'learner'})}.{GOOD_SIGNATURE}"
                self._reply(200, json.dumps({"access_token": "at", "id_token": token}).encode())

            def _reply(self, status: int, body: bytes, headers: dict[str, str] | None = None):
                self.send_response(status)
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

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


class Flaw(StrEnum):
    NO_STATE_CHECK = "no state check"
    ACCEPTS_ALG_NONE = "accepts alg none"
    PRINTS_TOKENS = "prints tokens"


@dataclass
class LoginApp:
    """The learner's app in miniature: an OAuth client whose mistakes a test switches on."""

    idp_port: int
    flaws: frozenset[Flaw] = frozenset()
    sessions: set[str] = field(default_factory=set[str])

    def routes(self) -> dict[tuple[str, str], Any]:
        return {
            ("GET", "/login"): self.login,
            ("GET", "/callback"): self.callback,
            ("GET", "/me"): self.me,
        }

    def login(self, request: AppRequest) -> AppAnswer:
        state = secrets.token_hex(4)
        location = f"{IDP_ORIGIN}/auth?{urlencode({'state': state})}"
        cookie = f"state={state}; Path=/; HttpOnly"
        return AppAnswer(302, None, {"Location": location, "Set-Cookie": cookie})

    def callback(self, request: AppRequest) -> AppAnswer:
        state_cookie = cookie_of(request, "state")
        if Flaw.NO_STATE_CHECK not in self.flaws and request.query.get("state") != state_cookie:
            return AppAnswer(400, {"error": "state"})
        code = request.query["code"]
        token = self.exchanged(code)
        if Flaw.PRINTS_TOKENS in self.flaws:
            request.app.print_line(f"exchanged {code} for {token}")
        if not self.trusted(token):
            return AppAnswer(401, {"error": "id_token"})
        session = secrets.token_hex(4)
        self.sessions.add(session)
        cookie = f"session={session}; Path=/; HttpOnly"
        return AppAnswer(302, None, {"Location": "/", "Set-Cookie": cookie})

    def me(self, request: AppRequest) -> AppAnswer:
        if cookie_of(request, "session") in self.sessions:
            return AppAnswer(200, {"user": "learner"})
        return AppAnswer(401, {"error": "login"})

    def exchanged(self, code: str) -> str:
        """The back channel: the token endpoint, reached at the provider's name, as the app would
        from inside the stack, so the mock server in front of it logs and may spoil it."""
        connection = http.client.HTTPConnection("127.0.0.1", self.idp_port, timeout=GENEROUS_WAIT_S)
        body = urlencode({"grant_type": "authorization_code", "code": code})
        headers = {"Host": "idp:8080", "Content-Type": "application/x-www-form-urlencoded"}
        try:
            connection.request("POST", "/token", body=body, headers=headers)
            return json.loads(connection.getresponse().read())["id_token"]
        finally:
            connection.close()

    def trusted(self, token: str) -> bool:
        header, _payload, signature = token.split(".")
        if Flaw.ACCEPTS_ALG_NONE in self.flaws and decoded(header)["alg"] == "none":
            return True
        return decoded(header)["alg"] == "RS256" and signature == GOOD_SIGNATURE


def cookie_of(request: AppRequest, name: str) -> str | None:
    for pair in request.headers.get("cookie", "").split(";"):
        key, _, value = pair.strip().partition("=")
        if key == name:
            return value
    return None


def login_steps(callback_status: int | str) -> list[dict[str, Any]]:
    return [
        {"use": "authorize", "with": {"user": "learner"}},
        {
            "request": {"method": "GET", "url": "{{callback}}"},
            "expected": {"status": callback_status},
        },
    ]


TESTS = {
    "version": 1,
    "flows": {
        "authorize": [
            {
                "request": {"method": "GET", "path": "/login"},
                "expected": {"status": 302},
                "capture": {"auth": "header.location"},
            },
            {
                "request": {"method": "GET", "url": "{{auth}}"},
                "expected": {"status": 200},
                "capture": {"form": "form.kc-form-login.action"},
            },
            {
                "request": {
                    "method": "POST",
                    "url": "{{form}}",
                    "form": {"username": "{{user}}", "password": PASSWORD},
                },
                "expected": {"status": 302},
                "capture": {"callback": "header.location", "code": "header.location.query.code"},
            },
        ]
    },
    "cases": [
        {
            "id": "login",
            "level": 1,
            "steps": [
                *login_steps(302),
                {
                    "request": {"method": "GET", "path": "/me"},
                    "expected": {"status": 200, "body": {"user": "learner"}},
                },
            ],
            "log": [{"mock": IDP, "route": "token", "count": 1, "form": {"code": "{{code}}"}}],
        },
        {
            "id": "forged-state",
            "level": 1,
            "steps": [
                {"use": "authorize", "with": {"user": "learner"}},
                {
                    "request": {
                        "method": "GET",
                        "path": "/callback",
                        "query": {"code": "{{code}}", "state": "forged"},
                    },
                    "expected": {"status": "4xx"},
                },
                {"request": {"method": "GET", "path": "/me"}, "expected": {"status": 401}},
            ],
        },
        {
            "id": "alg-none",
            "level": 1,
            "mocks": {IDP: "alg_none"},
            "steps": [
                *login_steps("4xx"),
                {"request": {"method": "GET", "path": "/me"}, "expected": {"status": 401}},
            ],
        },
        {
            "id": "quiet-output",
            "level": 1,
            "steps": login_steps(302),
            "app_output": {"absent": ["{{code}}", {"regex": r"eyJ[A-Za-z0-9_-]+\.eyJ"}]},
        },
    ],
}
IDP_CONFIG = {
    "routes": [{"id": "token", "method": "POST", "path": "/token"}],
    "scenarios": {
        "alg_none": {"route": "token", "jwt": {"field": "id_token", "tamper": "alg_none"}}
    },
}


@dataclass(frozen=True)
class Loopback:
    provider: StandInProvider
    api_port: int
    control_port: int


@pytest.fixture
def loopback(tmp_path: Path) -> Iterator[Loopback]:
    provider = StandInProvider()
    config = {
        "control_token": SAMPLE_TOKEN,
        "mocks": {IDP: {"upstream": f"http://127.0.0.1:{provider.port}", **IDP_CONFIG}},
    }
    path = tmp_path / "mocks.json"
    path.write_text(json.dumps(config))
    servers = start_servers(load_stack_config(path), ListenOn("127.0.0.1", 0, 0), FAST_POLL_S)
    yield Loopback(provider, servers.api_port, servers.control_port)
    servers.close()
    provider.close()


def graded(loopback: Loopback, *flaws: Flaw) -> dict[str, CaseVerdict]:
    login_app = LoginApp(loopback.api_port, frozenset(flaws))
    app = StandInApp(login_app.routes())
    try:
        stack = StandInStack(
            app,
            loopback.control_port,
            mocks=(IDP,),
            origins={IDP_ORIGIN: f"http://127.0.0.1:{loopback.api_port}"},
        )
        comparator = ComparatorSpec(ComparatorType.EXACT)
        cases = cases_from_document(TESTS, comparator, "tests.json")
        problem = Problem(project_meta(comparator=comparator), cases)
        run = HttpGradingRun(problem, 1, Config())
        judgement = run_http_grading(run, stack, open_stack_clients)
    finally:
        app.close()
    return {verdict.case.id: verdict for verdict in judgement.verdicts}


def failing(verdicts: dict[str, CaseVerdict]) -> dict[str, str | None]:
    return {
        case_id: verdict.mismatch.detail if verdict.mismatch else verdict.status.value
        for case_id, verdict in verdicts.items()
        if verdict.status is not CaseStatus.PASS
    }


def test_the_reference_app_passes_every_case(loopback: Loopback):
    assert failing(graded(loopback)) == {}


def test_an_app_that_skips_the_state_check_fails_the_forged_state_case_alone(loopback: Loopback):
    assert list(failing(graded(loopback, Flaw.NO_STATE_CHECK))) == ["forged-state"]


def test_an_app_that_trusts_alg_none_fails_the_tampered_token_case_alone(loopback: Loopback):
    found = failing(graded(loopback, Flaw.ACCEPTS_ALG_NONE))
    assert found == {
        "alg-none": "step 2 GET {{callback}}: expected a 4xx status, got 302",
    }


def test_an_app_that_prints_tokens_fails_the_output_case_alone(loopback: Loopback):
    found = failing(graded(loopback, Flaw.PRINTS_TOKENS))
    assert list(found) == ["quiet-output"]
    assert "app output: printed" in (found["quiet-output"] or "")
