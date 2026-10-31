"""The real `cstudy serve` on a free port: login with the printed token, every refusal of the
security layer over real HTTP, and the exit codes of its signals (docs/specs/web-ui.md#security,
docs/specs/cli.md#cstudy-serve)."""

import os
import queue
import signal
import socket
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import httpx2
import pytest

from tests.helpers import mark_workspace

pytestmark = pytest.mark.slow

START_SECONDS = 90
"""Generous: the machine running the slow tests is often loaded."""
STOP_SECONDS = 30
URL_LABEL = "open"
MIB = 1024 * 1024


@dataclass
class RunningServer:
    process: subprocess.Popen[str]
    login_url: str
    lines: "queue.Queue[str | None]" = field(default_factory=queue.Queue)

    @property
    def address(self) -> str:
        return self.login_url.split("/?")[0]

    @property
    def port(self) -> int:
        return int(self.address.rsplit(":", 1)[1])

    def stop(self, signal_number: int) -> tuple[int, list[str]]:
        """The exit code and the lines printed after the URL."""
        self.process.send_signal(signal_number)
        exit_code = self.process.wait(STOP_SECONDS)
        return exit_code, list(iter(partial(self.lines.get, timeout=STOP_SECONDS), None))


def _read_lines(stream: "subprocess.Popen[str]", lines: "queue.Queue[str | None]") -> None:
    assert stream.stdout is not None
    for line in stream.stdout:
        lines.put(line.rstrip("\n"))
    lines.put(None)


@contextmanager
def running_server(
    workspace: Path, *arguments: str, ignore_interrupts: bool = False
) -> Iterator[RunningServer]:
    """`python -m coding_study serve`; with `ignore_interrupts`, started as a shell starts a
    background job, with SIGINT ignored."""
    environment = {
        **os.environ,
        "CSTUDY_WORKSPACE": str(workspace),
        "XDG_CONFIG_HOME": str(workspace.parent / "config"),
        "NO_COLOR": "1",
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "coding_study", "serve", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=environment,
        preexec_fn=_ignore_interrupts if ignore_interrupts else None,
    )
    lines: queue.Queue[str | None] = queue.Queue()
    threading.Thread(target=_read_lines, args=(process, lines), daemon=True).start()
    try:
        yield RunningServer(process, _login_url(lines), lines)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _ignore_interrupts() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _login_url(lines: "queue.Queue[str | None]") -> str:
    while (line := lines.get(timeout=START_SECONDS)) is not None:
        label, _, value = line.partition(" ")
        if label == URL_LABEL:
            return value.strip()
    raise AssertionError("cstudy serve printed no URL")


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
    assert (response.status_code, response.headers["location"], len(anonymous.cookies)) == (
        303,
        "/",
        1,
    )


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


def test_the_editor_bundle_is_served(browser):
    response = browser.get("/assets/editor.js")
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
