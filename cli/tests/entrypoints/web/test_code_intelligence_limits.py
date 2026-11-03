"""What a code-intelligence session does when one side stops reading
(docs/specs/web-ui.md#lifecycle-and-limits): messages for a server that reads nothing pile up
only to a limit and then end the session with 4002, output the page leaves unread ends it with
1008, and `cstudy serve` stops even while a server reads no input."""

import asyncio
import operator
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import cast

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from coding_study.application.code_intelligence import SessionTarget
from coding_study.domain.code_intelligence import BASEDPYRIGHT
from coding_study.entrypoints.web import code_intelligence, language_server
from coding_study.entrypoints.web.code_intelligence import LanguageSession
from coding_study.entrypoints.web.language_broker import LanguageBroker
from coding_study.entrypoints.web.language_server import ServerProcess
from tests.language_server_scripts import QUICK, ScriptedServer, notification
from tests.language_sessions import Rig, closed_with, rig, session, stopped_within
from tests.scripted_runs import eventually, is_alive
from tests.web_server import session_client

PAD = "x" * 300_000
WAIT_S = 10.0


@pytest.fixture
def lab(tmp_path) -> Rig:
    return rig(tmp_path)


@pytest.fixture
def client(lab) -> Iterator[TestClient]:
    with session_client(lab.app) as page:
        yield page


def flood(websocket, messages: int = 8) -> None:
    """Messages for a server, each of which the broker passes on as it is."""
    for _ in range(messages):
        websocket.send_json(notification("initialized", {"padding": PAD}))


def all_gone(lab: Rig) -> bool:
    eventually(lambda: [is_alive(pid) for pid in lab.server.pids()], lambda alive: not any(alive))
    return True


# what waits for a server that reads nothing


def test_messages_that_pile_up_for_a_server_that_reads_nothing_end_the_session_with_4002(
    lab, client, monkeypatch
):
    monkeypatch.setattr(code_intelligence, "OUTBOX_LIMIT", 1_000_000)
    lab.server.play({"deaf": True})
    with session(client, lab.query) as websocket:
        eventually(lab.server.ready, bool)
        flood(websocket)
        assert closed_with(websocket) == (4002, "stuck: the server does not read its input")
    assert all_gone(lab)


def test_a_server_that_keeps_up_never_reaches_the_limit_however_much_it_is_sent(
    lab, client, monkeypatch
):
    monkeypatch.setattr(code_intelligence, "OUTBOX_LIMIT", 1_000_000)
    lab.server.play({"reply": "textDocument/hover", "result": "pong"})
    with session(client, lab.query) as websocket:
        for number in range(12):
            flood(websocket, 1)
            eventually(lambda: len(lab.server.received()), partial(operator.lt, number))
        websocket.send_json(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "textDocument/hover",
                "params": {"textDocument": {"uri": lab.document}},
            }
        )
        assert websocket.receive_json()["result"] == "pong"


def test_stopping_the_sessions_does_not_wait_for_a_server_that_reads_nothing(lab, client):
    lab.server.play({"deaf": True})
    with session(client, lab.query) as websocket:
        eventually(lab.server.ready, bool)
        flood(websocket, 6)
        stopped_within(client, lab.sessions, QUICK_STOP_S)
        assert closed_with(websocket)[0] == 1001
    assert all_gone(lab)


QUICK_STOP_S = 10.0
"""The stop sequence under `QUICK` ends in about a second and a half."""


# output the page does not read


class StalledPage:
    """The socket of a page that reads nothing: sending to it never ends."""

    def __init__(self) -> None:
        self.closed: list[tuple[int, str | None]] = []
        self._never = asyncio.Event()

    async def receive(self) -> dict[str, str]:
        await self._never.wait()
        return {"type": "websocket.disconnect"}

    async def send_text(self, _text: str) -> None:
        await self._never.wait()

    async def close(self, code: int, reason: str | None = None) -> None:
        self.closed.append((code, reason))


def diagnostics(path: Path, number: int) -> dict[str, object]:
    params = {
        "uri": (path / "python" / "x.py").as_uri(),
        "diagnostics": [{"message": "x" * 30_000}],
    }
    return notification("textDocument/publishDiagnostics", {**params, "number": number})


def test_a_page_that_reads_nothing_ends_the_session_with_1008(tmp_path, monkeypatch):
    monkeypatch.setattr(language_server, "UNREAD_LIMIT", 100_000)
    script = ScriptedServer(tmp_path / "server.json")
    sends: list[dict[str, object]] = [
        {"send": diagnostics(tmp_path, number)} for number in range(8)
    ]
    script.play(*sends, {"wait_for": str(script.gate("never"))})
    (tmp_path / "python").mkdir()
    target = SessionTarget(BASEDPYRIGHT, tmp_path, "python", tmp_path / "content")
    page = StalledPage()

    async def run() -> None:
        process = await ServerProcess.start(script.arguments, tmp_path / "python", QUICK)
        broker = LanguageBroker(target, "test", 1)
        try:
            await asyncio.wait_for(
                LanguageSession(cast(WebSocket, page), process, broker).run(), WAIT_S
            )
        finally:
            await process.stop()

    asyncio.run(run())
    assert page.closed == [(1008, "the page does not read the server's messages")]
