"""Scripted language servers for the tests of the code-intelligence sessions
(docs/specs/web-ui.md#testing): the script `tests/fake_language_server.py` plays, the messages a
page and a server exchange, and the clocks of a session cut to a fraction of a second."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coding_study.entrypoints.web.language_server import LanguageServerCommand, LanguageTiming

FAKE_LANGUAGE_SERVER = Path(__file__).with_name("fake_language_server.py")
QUICK = LanguageTiming(
    first_message_s=0.5,
    shutdown_wait_s=0.3,
    terminate_after_s=0.6,
    kill_after_s=0.4,
    drain_s=0.3,
)
"""A stop sequence of about a second and no 10 s wait for the CSRF message."""
SHUTDOWN_ANSWER = {"jsonrpc": "2.0", "id": "cstudy-shutdown", "result": None}


def request(request_id: int | str, method: str, params: object = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


def notification(method: str, params: object = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def answer(request_id: int | str, result: object = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


@dataclass(frozen=True)
class ScriptedServer:
    """The steps of every server a test starts, and what each was called with and sent."""

    path: Path

    def play(self, *steps: dict[str, object]) -> None:
        self.path.write_text(json.dumps(steps), encoding="utf-8")

    @property
    def arguments(self) -> tuple[str, ...]:
        return (sys.executable, str(FAKE_LANGUAGE_SERVER), str(self.path), "--stdio")

    @property
    def command(self) -> LanguageServerCommand:
        return LanguageServerCommand(self.arguments)

    def calls(self) -> list[dict[str, Any]]:
        calls = self.path.with_suffix(".calls")
        if not calls.exists():
            return []
        return [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]

    def pids(self) -> list[int]:
        return [call["pid"] for call in self.calls()]

    def received(self) -> list[dict[str, Any]]:
        """Every message the servers read, in the order they read them."""
        received = self.path.with_suffix(".received")
        if not received.exists():
            return []
        return [json.loads(line) for line in received.read_text(encoding="utf-8").splitlines()]

    def methods(self) -> list[str]:
        return [message["method"] for message in self.received() if "method" in message]

    def ready(self) -> bool:
        """Whether a server played every step of its script and waits for messages."""
        return self.path.with_suffix(".ready").exists()

    def gate(self, name: str) -> Path:
        """A file a `wait_for` step waits on; the test creates it to let the server go on."""
        return self.path.with_name(name)
