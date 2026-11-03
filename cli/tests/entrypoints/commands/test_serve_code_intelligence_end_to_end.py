"""Code-intelligence sessions through a real `cstudy serve` (docs/specs/web-ui.md#sessions): the
handshake, messages and close codes over uvicorn and wsproto, the 4 MiB limit and the missing
compression on the wire, and what Ctrl-C, SIGTERM, a tab that vanishes and a server that dies do
to the language servers: none is left running.

The servers are the scripted fake (`tests/fake_language_server.py`) behind a `node` on `PATH`, in
a workspace whose `.cs/lsp/` holds the two files `cstudy` looks for, so the real doctor probe, the
real command of the catalog and the real process handling run. The real servers are tested
separately (`tests/entrypoints/web/test_real_language_servers.py`)."""

import json
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from wsproto.extensions import PerMessageDeflate

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.domain.preferences import Preferences, preferences_document
from tests.language_server_scripts import (
    ScriptedServer,
    answer,
    fake_node,
    install_fake_basedpyright,
    notification,
    request,
)
from tests.scripted_runs import eventually, is_alive
from tests.serve_page import RUN_SECONDS, Page, opened_page
from tests.serve_process import LOOPBACK, RunningServer, running_server, served_environment
from tests.websocket_client import Closed, RefusedError, WebSocketClient
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

MIB = 1024 * 1024
PATH = "/api/v1/code-intelligence"
PING = {"reply": "textDocument/hover", "result": "pong"}
STOPS_ONLY_FOR_SIGNALS = {"ignore": ["shutdown", "exit", "eof"]}
SIGINT_STOP_SECONDS = 15
"""The stop sequence ends in about three seconds after the sockets closed; the sockets, 2."""


def cstudy(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        timeout=RUN_SECONDS,
    )


@dataclass
class Lab:
    workspace: Path
    script: ScriptedServer
    variables: dict[str, str]
    """The server's environment: a `node` that is the scripted fake first on `PATH`."""


@pytest.fixture
def lab(practice_workspace: Path, tmp_path: Path) -> Lab:
    workspace = workspace_like(practice_workspace, tmp_path / "workspace")
    cstudy(workspace, "start", "two-sum", "--lang", "python", "--no-open")
    install_fake_basedpyright(workspace)
    FsPreferencesStore(workspace).write(preferences_document(Preferences(code_intelligence=True)))
    script = ScriptedServer(tmp_path / "server.json")
    script.play()
    return Lab(workspace, script, {"PATH": fake_node(tmp_path / "bin", script)})


@pytest.fixture
def served(lab: Lab) -> Iterator[tuple[RunningServer, Page]]:
    with running_server(lab.workspace, variables=lab.variables) as server:
        yield server, opened_page(server)


def handshake(server: RunningServer, page: Page) -> dict[str, str]:
    cookie = page.client.cookies.get(f"cstudy-{server.port}")
    return {"Origin": server.address, "Cookie": f"cstudy-{server.port}={cookie}"}


def connect(server: RunningServer, page: Page, **overrides: object) -> WebSocketClient:
    query = f"?attempt_id={page.attempts['two-sum']}"
    return WebSocketClient(
        (LOOPBACK, server.port),
        f"{PATH}{query}",
        handshake(server, page),
        **overrides,  # type: ignore[arg-type]
    )


def authorise(page: Page, websocket: WebSocketClient) -> None:
    websocket.send_text(json.dumps({"csrf": page.headers["X-Cstudy-CSRF"]}))


def hover(lab: Lab) -> dict[str, object]:
    """A hover request for a file inside the Python session's root."""
    document = {"uri": (lab.workspace / "python" / "x.py").as_uri()}
    return request(1, "textDocument/hover", {"textDocument": document})


def started_server(lab: Lab) -> int:
    return eventually(lab.script.pids, bool)[0]


# the wire


def test_a_page_talks_to_a_server_through_a_real_socket(lab, served):
    server, page = served
    lab.script.play(PING)
    with connect(server, page) as websocket:
        authorise(page, websocket)
        websocket.send_text(json.dumps(hover(lab)))
        assert json.loads(str(websocket.receive())) == answer(1, "pong")


def test_a_handshake_without_the_origin_is_refused_with_403_and_the_error_document(lab, served):
    server, page = served
    headers = {name: value for name, value in handshake(server, page).items() if name != "Origin"}
    query = f"?attempt_id={page.attempts['two-sum']}"
    with pytest.raises(RefusedError) as refused:
        WebSocketClient((LOOPBACK, server.port), f"{PATH}{query}", headers)
    document = json.loads(refused.value.body)
    assert (refused.value.status_code, document["error"]["code"]) == (403, "forbidden")
    assert refused.value.headers["cache-control"] == "no-store"
    assert lab.script.calls() == []


def test_a_handshake_without_the_cookie_is_refused_with_401(lab, served):
    server, page = served
    query = f"?attempt_id={page.attempts['two-sum']}"
    with pytest.raises(RefusedError) as refused:
        WebSocketClient((LOOPBACK, server.port), f"{PATH}{query}", {"Origin": server.address})
    assert refused.value.status_code == 401


def test_a_host_that_is_not_this_server_is_refused_with_403(lab, served):
    server, page = served
    query = f"?attempt_id={page.attempts['two-sum']}"
    with pytest.raises(RefusedError) as refused:
        WebSocketClient(
            (LOOPBACK, server.port), f"{PATH}{query}", handshake(server, page), host="evil.example"
        )
    assert refused.value.status_code == 403


def test_a_wrong_token_closes_the_socket_with_1008_and_starts_no_server(lab, served):
    server, page = served
    with connect(server, page) as websocket:
        websocket.send_text('{"csrf": "wrong"}')
        assert websocket.receive() == Closed(1008, "bad CSRF token")
    assert lab.script.calls() == []


def test_compression_is_not_negotiated_whatever_the_page_offers(lab, served):
    server, page = served
    with connect(server, page, extensions=[PerMessageDeflate()]) as websocket:
        assert websocket.extensions == []


def test_a_message_of_4_mib_is_a_message_and_one_byte_more_closes_the_socket_with_1009(lab, served):
    server, page = served
    with connect(server, page) as websocket:
        authorise(page, websocket)
        websocket.send_text("x" * (4 * MIB))
        parse_error = json.loads(str(websocket.receive()))["error"]["code"]
        websocket.send_text("x" * (4 * MIB + 1))
        closed = websocket.receive()
    assert (parse_error, isinstance(closed, Closed) and closed.code) == (-32700, 1009)


def test_a_binary_message_closes_the_socket_with_1003(lab, served):
    server, page = served
    with connect(server, page) as websocket:
        authorise(page, websocket)
        websocket.send_bytes(b"{}")
        assert websocket.receive() == Closed(1003, "binary messages are not accepted")


def test_a_server_that_exits_closes_the_socket_with_4002_and_its_last_line(lab, served):
    server, page = served
    lab.script.play({"err": "Error: Cannot find module 'x'"}, {"exit": 1})
    with connect(server, page) as websocket:
        authorise(page, websocket)
        assert websocket.receive() == Closed(4002, "exit 1: Error: Cannot find module 'x'")


# the end


def test_a_tab_that_vanishes_without_a_close_frame_stops_its_server(lab, served):
    server, page = served
    lab.script.play(PING)
    with connect(server, page) as websocket:
        authorise(page, websocket)
        websocket.send_text(json.dumps(hover(lab)))
        websocket.receive()
        pid = started_server(lab)
        websocket.drop()
    eventually(lab.script.methods, lambda methods: methods[-2:] == ["shutdown", "exit"])
    eventually(lambda: is_alive(pid), lambda alive: not alive)


@pytest.mark.parametrize(
    ("number", "exit_code", "how"),
    [(signal.SIGINT, 130, "Ctrl-C"), (signal.SIGTERM, 143, "SIGTERM")],
    ids=["Ctrl-C", "SIGTERM"],
)
def test_stopping_the_server_closes_every_socket_with_1001_and_leaves_no_language_server(
    lab, number, exit_code, how
):
    lab.script.play(STOPS_ONLY_FOR_SIGNALS)
    with running_server(lab.workspace, variables=lab.variables) as server:
        page = opened_page(server)
        with connect(server, page) as first, connect(server, page) as second:
            for websocket in (first, second):
                authorise(page, websocket)
            eventually(lab.script.pids, lambda pids: len(pids) == 2)
            eventually(lab.script.ready, bool)
            pids = lab.script.pids()
            page.client.close()
            code, printed = server.stop(number)
            closes = [first.receive(), second.receive()]
    assert (code, closes, printed[-1]) == (
        exit_code,
        [Closed(1001, "cstudy serve is stopping")] * 2,
        f"stop       {how}",
    )
    assert not any(is_alive(pid) for pid in pids)


def test_ctrl_c_does_not_wait_for_a_language_server_that_reads_no_input(lab):
    """The server stopped reading while messages waited for it, so no `shutdown` and no `exit`
    could be written; the stop escalates to SIGTERM and SIGKILL on time all the same."""
    lab.script.play({"deaf": True})
    with running_server(lab.workspace, variables=lab.variables) as server:
        page = opened_page(server)
        with connect(server, page) as websocket:
            authorise(page, websocket)
            eventually(lab.script.ready, bool)
            for _ in range(6):
                padding = {"padding": "x" * 300_000}
                websocket.send_text(json.dumps(notification("initialized", padding)))
            time.sleep(0.5)
            pid = started_server(lab)
            page.client.close()
            begun = time.monotonic()
            code, _printed = server.stop(signal.SIGINT)
            took = time.monotonic() - begun
            websocket.receive()
    assert (code, took < SIGINT_STOP_SECONDS, is_alive(pid)) == (130, True, False)


def test_a_server_that_dies_leaves_its_language_server_the_end_of_its_input(lab, served):
    server, page = served
    lab.script.play(PING)
    with connect(server, page) as websocket:
        authorise(page, websocket)
        websocket.send_text(json.dumps(hover(lab)))
        websocket.receive()
        pid = started_server(lab)
        server.process.kill()
        server.process.wait()
        eventually(lambda: is_alive(pid), lambda alive: not alive)
