"""The environment of a language server (docs/specs/runners.md#process-environment): a server
analyses user code and may run its tools, so it inherits what user code does and no secret of the
shell that started `cstudy serve`, and a Node server keeps the options its user set beside the
preload that hides the directories (docs/specs/web-ui.md#hidden-directories)."""

import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import ClassVar, cast

import pytest
from starlette.websockets import WebSocket

from coding_study.application.code_intelligence import SessionTarget
from coding_study.domain.code_intelligence import BASEDPYRIGHT
from coding_study.entrypoints.web import code_intelligence
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from coding_study.entrypoints.web.language_broker import LanguageBroker
from coding_study.entrypoints.web.language_server import (
    PRELOAD,
    LanguageTiming,
    ServerProcess,
    ServerStartError,
)
from tests.language_server_scripts import QUICK
from tests.launch_environment import (
    environment_recorder,
    leaked_secrets,
    missing_needs,
    plant_secrets,
    recorded,
)

WAIT_S = 10.0
USER_OPTIONS = "--max-old-space-size=512"


@pytest.fixture(autouse=True)
def secrets_in_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    plant_secrets(monkeypatch)
    monkeypatch.setenv("NODE_OPTIONS", USER_OPTIONS)


def test_a_server_does_not_inherit_a_secret(tmp_path):
    record = tmp_path / "environment.txt"
    command = (sys.executable, "-I", "-c", environment_recorder(record))

    async def run() -> None:
        process = await ServerProcess.start(command, tmp_path, QUICK)
        await asyncio.wait_for(process.exited(), WAIT_S)

    asyncio.run(run())
    inherited = recorded(record)
    assert (leaked_secrets(inherited), missing_needs(inherited)) == (set(), set())


def test_a_server_given_an_environment_runs_in_it(tmp_path):
    record = tmp_path / "environment.txt"
    command = (sys.executable, "-I", "-c", environment_recorder(record))

    async def run() -> None:
        process = await ServerProcess.start(command, tmp_path, QUICK, {"ONLY": "this"})
        await asyncio.wait_for(process.exited(), WAIT_S)

    asyncio.run(run())
    started_in = recorded(record)
    assert (started_in.get("ONLY"), "PATH" in started_in) == ("this", False)


class RefusingServer:
    """Stands in for `ServerProcess`: keeps the environment a session asks it to start in."""

    environments: ClassVar[list[Mapping[str, str] | None]] = []

    @classmethod
    async def start(
        cls,
        arguments: Sequence[str],
        directory: Path,
        timing: LanguageTiming,
        environment: Mapping[str, str] | None = None,
    ) -> ServerProcess:
        cls.environments.append(environment)
        raise ServerStartError("not started")


class ClosedSocket:
    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        return None


def environment_of_a_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Mapping[str, str]:
    """What a session asks its server to start in, for a workspace whose content root is hidden."""
    target = SessionTarget(BASEDPYRIGHT, tmp_path / "ws", "python", tmp_path / "content")
    (tmp_path / "ws" / "python").mkdir(parents=True)
    RefusingServer.environments = []
    monkeypatch.setattr(code_intelligence, "ServerProcess", RefusingServer)
    socket = cast(WebSocket, ClosedSocket())
    asyncio.run(LanguageSessions().serve(socket, target, LanguageBroker(target, "test", 1)))
    (environment,) = RefusingServer.environments
    assert environment is not None
    return environment


def test_a_session_starts_its_server_without_a_secret(tmp_path, monkeypatch):
    environment = environment_of_a_session(tmp_path, monkeypatch)
    assert (leaked_secrets(environment), missing_needs(environment)) == (set(), set())


def test_a_session_keeps_the_node_options_of_the_user(tmp_path, monkeypatch):
    environment = environment_of_a_session(tmp_path, monkeypatch)
    assert environment["NODE_OPTIONS"].startswith(USER_OPTIONS)


def test_a_session_hides_the_directories_from_a_node_server(tmp_path, monkeypatch):
    environment = environment_of_a_session(tmp_path, monkeypatch)
    hidden = json.loads(environment["CSTUDY_HIDDEN_DIRECTORIES"])
    assert (PRELOAD.name in environment["NODE_OPTIONS"], str(tmp_path / "content") in hidden) == (
        True,
        True,
    )
