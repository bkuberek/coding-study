"""The default language's server, started ahead of any page (docs/specs/web-ui.md#warm-up): the
first session of its target takes it over, initialized; with no editor for `WARM_IDLE_S` it stops,
on a fake clock here, where time passes only when the test says so."""

import asyncio
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.application.code_intelligence import SessionTarget, warm_up_target
from coding_study.domain.code_intelligence import WARM_IDLE_S
from coding_study.domain.problem import Language
from coding_study.domain.sandbox import (
    SandboxUser,
    SharedFolder,
    SidecarPlan,
    StackIdentity,
    StackKind,
)
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from coding_study.entrypoints.web.language_broker import WARM_UP_ID, LanguageBroker
from tests.language_server_scripts import QUICK, request
from tests.language_sessions import (
    CODE_INTELLIGENCE_ON,
    Rig,
    received,
    rig,
    session,
    stopped,
)
from tests.scripted_runs import eventually, is_alive
from tests.web_server import TEST_VERSION, session_client, web_app

CAPABILITIES = {"capabilities": {"hoverProvider": True}}
INITIALIZE = {"reply": "initialize", "result": CAPABILITIES}
POLL_S = 0.01


@dataclass
class FakeSleep:
    """The warm server's clock: it records what it is asked to wait, and the wait ends only once
    the test lets the time pass."""

    asked: list[float] = field(default_factory=list[float])
    passed: bool = False

    async def __call__(self, seconds: float) -> None:
        self.asked.append(seconds)
        while not self.passed:
            await asyncio.sleep(POLL_S)


@pytest.fixture
def clock() -> FakeSleep:
    return FakeSleep()


def warm_rig(tmp_path: Path, clock: FakeSleep, limit: int = 4) -> Rig:
    lab = rig(tmp_path, limit=limit)
    lab.sessions = LanguageSessions(lab.server.command, QUICK, limit, sleep=clock)
    lab.server.play(INITIALIZE)
    return lab


@pytest.fixture
def lab(tmp_path, clock) -> Rig:
    return warm_rig(tmp_path, clock)


def default_target(lab: Rig) -> SessionTarget:
    found = warm_up_target(lab.environment, CODE_INTELLIGENCE_ON)
    assert found is not None
    return found


def warmed(client: TestClient, lab: Rig, target: SessionTarget | None = None) -> bool:
    """Whether the sessions started the server of `target`, the default language's unless said."""
    portal = client.portal
    assert portal is not None
    chosen = target or default_target(lab)
    broker = LanguageBroker(chosen, TEST_VERSION, os.getpid())
    return portal.call(lab.sessions.warm, chosen, broker)


def started_servers(lab: Rig) -> int:
    return len(lab.server.calls())


def test_the_default_languages_server_starts_before_any_page(lab):
    with session_client(lab.app) as client:
        assert warmed(client, lab)
        eventually(lab.server.ready, bool)
        assert started_servers(lab) == 1


def test_its_broker_initializes_it(lab):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.methods, lambda methods: "initialized" in methods)
    first = lab.server.received()[0]
    assert (first["id"], first["method"]) == (WARM_UP_ID, "initialize")


def test_the_first_session_of_its_target_takes_it_over(lab):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        with session(client, lab.query) as websocket:
            websocket.send_json(request(1, "initialize", {}))
            reply = received(websocket)
        assert (reply["id"], reply["result"], started_servers(lab)) == (1, CAPABILITIES, 1)


def test_the_server_hears_initialized_once(lab):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        with session(client, lab.query) as websocket:
            websocket.send_json(request(1, "initialize", {}))
            received(websocket)
            websocket.send_json({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            websocket.send_json(request(2, "shutdown"))
            received(websocket)
    assert lab.server.methods().count("initialized") == 1


def test_with_no_editor_it_stops_after_its_idle_time(lab, clock):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        (pid,) = lab.server.pids()
        clock.passed = True
        eventually(lambda: is_alive(pid), lambda alive: not alive)
        assert (clock.asked, lab.sessions.warm_target) == ([WARM_IDLE_S], None)


def test_a_server_an_editor_took_over_outlives_the_idle_time(lab, clock):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        with session(client, lab.query) as websocket:
            websocket.send_json(request(1, "initialize", {}))
            received(websocket)
            clock.passed = True
            websocket.send_json(request(2, "textDocument/hover", {}))
            (pid,) = lab.server.pids()
            assert is_alive(pid)


def test_stopping_cstudy_serve_stops_it(lab):
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        (pid,) = lab.server.pids()
        stopped(client, lab.sessions)
        assert not is_alive(pid)


def test_it_gives_its_slot_to_a_session_of_another_target(tmp_path, clock):
    lab = warm_rig(tmp_path, clock, limit=1)
    typescript = lab.start(Language.TYPESCRIPT)
    with session_client(lab.app) as client:
        warmed(client, lab)
        eventually(lab.server.ready, bool)
        (warm_pid,) = lab.server.pids()
        with session(client, f"?attempt_id={typescript.id}") as websocket:
            websocket.send_json(request(1, "initialize", {}))
            reply = received(websocket)
            assert (reply["id"], is_alive(warm_pid), started_servers(lab)) == (1, False, 2)


def test_one_server_at_most_is_warmed(lab):
    with session_client(lab.app) as client:
        warmed(client, lab)
        assert not warmed(client, lab)


def test_a_sidecar_is_never_warmed(lab):
    identity = StackIdentity("cstudy-l-1-a", StackKind.LSP, "d", "rooms", 1)
    folder = SharedFolder("/work/rooms", "/work/rooms")
    plan = SidecarPlan(identity, SandboxUser(501, 20), folder, folder, "/work/.cs/runs/x")
    with session_client(lab.app) as client:
        assert not warmed(client, lab, replace(default_target(lab), sidecar=plan))
    assert started_servers(lab) == 0


def test_cstudy_serve_warms_the_default_language_up_as_it_starts(lab):
    app = web_app(lab.root, lab.environment, sessions=lab.sessions, warm_up=True)
    with session_client(app):
        eventually(lab.server.ready, bool)
        assert lab.sessions.warm_target == default_target(lab)


def test_a_test_app_warms_nothing_up(lab):
    with session_client(lab.app):
        pass
    assert started_servers(lab) == 0
