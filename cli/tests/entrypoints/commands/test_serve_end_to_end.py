"""The real `cstudy serve` on a free port: login with the printed token, every refusal of the
security layer over real HTTP, and the exit codes of its signals (docs/specs/web-ui.md#security,
docs/specs/cli.md#cstudy-serve)."""

import os
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator

import httpx2
import pytest

from tests.helpers import mark_workspace
from tests.serve_process import START_SECONDS, RunningServer, running_server

pytestmark = pytest.mark.slow

MIB = 1024 * 1024


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    with running_server(mark_workspace(tmp_path_factory.mktemp("served"))) as running:
        yield running


@pytest.fixture
def anonymous(server: RunningServer) -> Iterator[httpx2.Client]:
    with httpx2.Client(base_url=server.address, follow_redirects=False) as client:
        yield client


@pytest.fixture
def browser(server: RunningServer, anonymous: httpx2.Client) -> httpx2.Client:
    """A client that opened the printed URL and holds the session cookie."""
    anonymous.get(server.login_url)
    return anonymous


@pytest.fixture
def write_headers(server: RunningServer, browser: httpx2.Client) -> dict[str, str]:
    page = browser.get("/").text
    csrf = page.split('<meta name="cstudy-csrf" content="')[1].split('"')[0]
    return {"Origin": server.address, "X-Cstudy-CSRF": csrf}


def test_the_printed_url_buys_the_session_cookie(server, anonymous):
    response = anonymous.get(server.login_url)
    assert (response.status_code, len(anonymous.cookies)) == (200, 1)


def test_the_session_opens_the_api(browser):
    assert browser.get("/api/v1/session").status_code == 200


def test_the_api_without_the_cookie_answers_401(anonymous):
    assert anonymous.get("/api/v1/session").status_code == 401


def test_the_page_without_the_cookie_answers_401(anonymous):
    assert anonymous.get("/").status_code == 401


def test_a_wrong_token_answers_401(anonymous):
    assert anonymous.get("/?token=guessed").status_code == 401


def test_another_host_answers_403(server, browser):
    response = browser.get("/api/v1/session", headers={"Host": f"rebound.example:{server.port}"})
    assert response.status_code == 403


def test_a_write_from_another_origin_answers_403(browser, write_headers):
    headers = {**write_headers, "Origin": "https://evil.example"}
    assert browser.put("/api/v1/preferences", json={}, headers=headers).status_code == 403


def test_a_write_without_the_csrf_header_answers_403(server, browser):
    headers = {"Origin": server.address}
    assert browser.put("/api/v1/preferences", json={}, headers=headers).status_code == 403


def test_a_body_over_2_mib_answers_413(browser, write_headers):
    body = b" " * (2 * MIB + 1)
    response = browser.put("/api/v1/preferences", content=body, headers=write_headers)
    assert response.status_code == 413


def test_a_write_from_the_page_passes(browser, write_headers):
    response = browser.put("/api/v1/preferences", json={"vim": True}, headers=write_headers)
    assert (response.status_code, response.json()["vim"]) == (200, True)


def test_the_page_carries_its_policy_and_nonce(browser):
    response = browser.get("/")
    nonce = response.text.split('<meta name="cstudy-csp-nonce" content="')[1].split('"')[0]
    assert f"style-src 'self' 'nonce-{nonce}'" in response.headers["content-security-policy"]


def test_the_page_bundle_is_served(browser):
    response = browser.get("/assets/app.js")
    assert (response.status_code, response.headers["cache-control"]) == (200, "no-cache")


def test_nothing_listens_on_another_address(server):
    with socket.socket(socket.AF_INET6) as probe:
        assert probe.connect_ex(("::1", server.port)) != 0


def test_ctrl_c_exits_130_saying_so(tmp_path):
    with running_server(mark_workspace(tmp_path)) as running:
        assert running.stop(signal.SIGINT) == (130, ["stop       Ctrl-C"])


def test_sigterm_exits_143_saying_so(tmp_path):
    with running_server(mark_workspace(tmp_path)) as running:
        assert running.stop(signal.SIGTERM) == (143, ["stop       SIGTERM"])


def test_sigint_stops_a_server_started_in_the_background(tmp_path):
    with running_server(mark_workspace(tmp_path), ignore_interrupts=True) as running:
        assert running.stop(signal.SIGINT) == (130, ["stop       Ctrl-C"])


def test_a_port_in_use_exits_4(tmp_path):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = str(taken.getsockname()[1])
        finished = subprocess.run(
            [sys.executable, "-m", "coding_study", "serve", "--port", port],
            env={**os.environ, "CSTUDY_WORKSPACE": str(mark_workspace(tmp_path))},
            capture_output=True,
            text=True,
            check=False,
            timeout=START_SECONDS,
        )
    assert finished.returncode == 4
