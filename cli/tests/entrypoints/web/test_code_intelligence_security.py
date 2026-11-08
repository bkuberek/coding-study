"""The security matrix of the code-intelligence WebSocket (docs/specs/web-ui.md#session-security):
what is refused before the upgrade, in the order the spec fixes, and what the CSRF first message
must be after it. The cookie alone keeps no page on another port out: a browser sends it on a
handshake from any `127.0.0.1` port, so the Host and Origin allow-lists and the token in the first
message are what refuse it."""

import hmac
import time
from collections.abc import Iterator
from dataclasses import replace

import pytest
from starlette.testclient import TestClient

from coding_study.domain.attempts import AttemptStatus
from coding_study.domain.problem import Language
from tests.language_sessions import (
    CSRF_MESSAGE,
    PAGE_HEADERS,
    Rig,
    closed_with,
    connect,
    refused,
    rig,
)
from tests.scripted_runs import eventually
from tests.web_server import HOST, PORT, SECRETS, anonymous_client, session_client

OTHER_PORT = PORT + 1
LOCALHOST = f"localhost:{PORT}"
CSRF_REFUSAL = (1008, "bad CSRF token")
UNSTARTED_S = 0.3


@pytest.fixture
def lab(tmp_path) -> Rig:
    return rig(tmp_path)


@pytest.fixture
def client(lab) -> Iterator[TestClient]:
    with session_client(lab.app) as page:
        yield page


def error_of(denial) -> tuple[int, str]:
    return denial.status_code, denial.json()["error"]["code"]


# before the upgrade: Host, cookie and Origin


@pytest.mark.parametrize(
    "host",
    [f"evil.example:{PORT}", f"127.0.0.1:{OTHER_PORT}", "127.0.0.1", "evil.example"],
    ids=["another server", "another port", "no port", "another name"],
)
def test_a_host_that_is_not_this_server_is_refused_with_403(lab, client, host):
    denial = refused(client, lab.query, host=host)
    assert error_of(denial) == (403, "forbidden")


@pytest.mark.parametrize(
    "origin",
    [
        f"http://127.0.0.1:{OTHER_PORT}",
        f"http://localhost:{OTHER_PORT}",
        "https://evil.example",
        f"http://evil.example:{PORT}",
        f"https://{HOST}",
        "null",
        "",
    ],
    ids=[
        "another port of 127.0.0.1",
        "another port of localhost",
        "another site",
        "another host on this port",
        "another scheme",
        "null",
        "empty",
    ],
)
def test_an_origin_that_is_not_this_servers_page_is_refused_with_403(lab, client, origin):
    denial = refused(client, lab.query, headers={"Origin": origin})
    assert error_of(denial) == (403, "forbidden")


def test_a_handshake_without_an_origin_is_refused_with_403(lab, client):
    assert error_of(refused(client, lab.query, headers={})) == (403, "forbidden")


def test_a_page_on_another_port_is_refused_though_the_browser_sends_it_the_cookie(lab, client):
    """`client` holds the session cookie, as a browser does for every port of 127.0.0.1."""
    denial = refused(client, lab.query, headers={"Origin": f"http://127.0.0.1:{OTHER_PORT}"})
    assert (error_of(denial), lab.server.calls()) == ((403, "forbidden"), [])


def test_a_handshake_without_the_session_cookie_is_refused_with_401(lab):
    with anonymous_client(lab.app) as stranger:
        assert error_of(refused(stranger, lab.query)) == (401, "unauthorized")


def test_a_handshake_with_another_cookie_is_refused_with_401(lab):
    with anonymous_client(lab.app) as stranger:
        stranger.cookies.set(f"cstudy-{PORT}", "not-the-cookie")
        assert error_of(refused(stranger, lab.query)) == (401, "unauthorized")


def test_the_host_is_checked_before_the_cookie(lab):
    with anonymous_client(lab.app) as stranger:
        denial = refused(stranger, lab.query, host=f"evil.example:{PORT}")
        assert error_of(denial) == (403, "forbidden")


def test_the_cookie_is_checked_before_the_origin(lab):
    with anonymous_client(lab.app) as stranger:
        assert error_of(refused(stranger, lab.query, headers={})) == (401, "unauthorized")


def test_the_origin_is_checked_before_the_attempt(lab, client):
    assert error_of(refused(client, "", headers={})) == (403, "forbidden")


@pytest.mark.parametrize(
    "host",
    [HOST, LOCALHOST],
    ids=["127.0.0.1", "localhost"],
)
def test_the_page_of_this_server_gets_in_by_either_name(lab, client, host):
    origin = f"http://{host}"
    with connect(client, lab.query, headers={"Origin": origin}, host=host) as websocket:
        websocket.send_json(CSRF_MESSAGE)
        eventually(lab.server.calls, bool)


def test_a_refusal_carries_the_security_headers_and_no_cors_headers(lab, client):
    headers = refused(client, "", headers={}).headers
    assert (
        headers["cache-control"],
        headers["x-content-type-options"],
        headers["referrer-policy"],
        "default-src 'self'" in headers["content-security-policy"],
        headers["content-type"],
        [name for name in headers if name.startswith("access-control-")],
    ) == ("no-store", "nosniff", "no-referrer", True, "application/json; charset=utf-8", [])


# before the upgrade: the attempt, the preference, the language and the server


@pytest.mark.parametrize(
    "query",
    ["", "?attempt_id=", "?attempt_id=abc", "?attempt_id=1.5", "?attempt_id=0", "?attempt_id=-1"],
    ids=["missing", "empty", "not a number", "decimal", "zero", "negative"],
)
def test_an_attempt_id_that_is_not_a_positive_integer_is_refused_with_422(lab, client, query):
    assert error_of(refused(client, query)) == (422, "usage")


def test_a_missing_attempt_id_says_what_the_request_needs(lab, client):
    message = refused(client, "").json()["error"]["message"]
    assert message == "the request needs attempt_id"


def test_an_attempt_nobody_started_is_refused_with_404(lab, client):
    denial = refused(client, "?attempt_id=41")
    assert (error_of(denial), denial.json()["error"]["message"]) == (
        (404, "not_found"),
        "unknown attempt 41",
    )


def test_an_attempt_that_ended_is_refused_with_409(lab, client):
    lab.environment.progress.update_attempt(replace(lab.attempt, status=AttemptStatus.PASSED))
    denial = refused(client, lab.query)
    assert (error_of(denial), denial.json()["error"]["message"]) == (
        (409, "attempt_ended"),
        f"attempt {lab.attempt.id} of two-sum is no longer in progress",
    )


def test_the_preference_off_is_refused_with_422_and_the_way_to_turn_it_on(lab, client):
    lab.turn_off()
    denial = refused(client, lab.query)
    assert (error_of(denial), denial.json()["error"]["message"]) == (
        (422, "usage"),
        "code intelligence is off: turn it on in Settings",
    )


def test_a_kotlin_lsp_whose_license_is_not_accepted_is_refused_with_503_and_the_command(
    tmp_path,
):
    lab = rig(tmp_path, language=Language.KOTLIN, licenses_accepted=False)
    with session_client(lab.app) as page:
        denial = refused(page, lab.query)
    assert (error_of(denial), denial.json()["error"]["fix"]) == (
        (503, "environment"),
        "cstudy doctor --fix --accept-license kotlin-lsp",
    )


def test_a_rust_server_that_is_not_installed_is_refused_with_503_and_the_rustup_fix(tmp_path):
    lab = rig(tmp_path, installed=False, language=Language.RUST)
    with session_client(lab.app) as page:
        denial = refused(page, lab.query)
    assert (error_of(denial), denial.json()["error"]["fix"]) == (
        (503, "environment"),
        "rustup component add rust-analyzer",
    )


def test_a_server_that_is_not_installed_is_refused_with_503_and_the_fix(tmp_path):
    lab = rig(tmp_path, installed=False)
    with session_client(lab.app) as page:
        denial = refused(page, lab.query)
    assert (error_of(denial), denial.json()["error"]["fix"]) == (
        (503, "environment"),
        "cstudy doctor --fix",
    )


def test_no_refusal_starts_a_server(lab, client):
    lab.turn_off()
    for query in ("", "?attempt_id=41", lab.query):
        refused(client, query)
    refused(client, lab.query, headers={})
    assert lab.server.calls() == []


# after the upgrade: the CSRF message


def refused_by_the_first_message(client, lab, send) -> tuple[int, str]:
    with connect(client, lab.query) as websocket:
        send(websocket)
        return closed_with(websocket)


@pytest.mark.parametrize(
    "text",
    [
        '{"csrf": "wrong"}',
        '{"csrf": ""}',
        f'{{"csrf": "{SECRETS.csrf}x"}}',
        f'{{"csrf": "{SECRETS.csrf[:-1]}"}}',
        '{"csrf": "é"}',
        '{"csrf": 1}',
        '{"csrf": null}',
        '{"csrf": ["x"]}',
        '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}',
        "{}",
        f'["{SECRETS.csrf}"]',
        f'"{SECRETS.csrf}"',
        SECRETS.csrf,
        "",
        "null",
        "[" * 100_000,
    ],
    ids=[
        "wrong token",
        "empty token",
        "token and more",
        "token less one",
        "token that is not ASCII",
        "number",
        "null",
        "list",
        "a JSON-RPC message first",
        "empty object",
        "token in a list",
        "token as a string",
        "token as text",
        "empty text",
        "null document",
        "nesting too deep",
    ],
)
def test_a_first_message_that_is_not_the_token_closes_with_1008(lab, client, text):
    assert refused_by_the_first_message(client, lab, lambda ws: ws.send_text(text)) == CSRF_REFUSAL
    assert lab.server.calls() == []


def test_a_binary_first_message_closes_with_1008(lab, client):
    send = lambda ws: ws.send_bytes(SECRETS.csrf.encode())  # noqa: E731
    assert refused_by_the_first_message(client, lab, send) == CSRF_REFUSAL


def test_no_first_message_within_the_deadline_closes_with_1008(lab, client):
    begun = time.monotonic()
    with connect(client, lab.query) as websocket:
        closed = closed_with(websocket)
    assert (closed, time.monotonic() - begun >= lab.sessions.timing.first_message_s) == (
        CSRF_REFUSAL,
        True,
    )


def test_a_token_that_comes_too_late_finds_the_socket_closed(lab, client):
    with connect(client, lab.query) as websocket:
        time.sleep(lab.sessions.timing.first_message_s + 0.3)
        websocket.send_json(CSRF_MESSAGE)
        assert closed_with(websocket) == CSRF_REFUSAL
    assert lab.server.calls() == []


def test_the_token_in_the_handshake_header_is_not_the_message(lab, client):
    headers = {**PAGE_HEADERS, "X-Cstudy-CSRF": SECRETS.csrf}
    with connect(client, lab.query, headers=headers) as websocket:
        assert closed_with(websocket) == CSRF_REFUSAL


def test_the_server_starts_only_after_the_token_arrives(lab, client):
    with connect(client, lab.query) as websocket:
        time.sleep(UNSTARTED_S / 2)
        before = lab.server.calls()
        websocket.send_json(CSRF_MESSAGE)
        eventually(lab.server.calls, bool)
    assert before == []


def test_the_token_is_compared_in_constant_time(lab, client, monkeypatch):
    compared: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(given: bytes, expected: bytes) -> bool:
        compared.append((given, expected))
        return real(given, expected)

    monkeypatch.setattr(hmac, "compare_digest", spy)
    refused_by_the_first_message(client, lab, lambda ws: ws.send_json({"csrf": "wrong"}))
    assert (b"wrong", SECRETS.csrf.encode()) in compared
