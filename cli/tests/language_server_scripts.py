"""Scripted language servers for the tests of the code-intelligence sessions
(docs/specs/web-ui.md#testing): the script `tests/fake_language_server.py` plays, the messages a
page and a server exchange, and the clocks of a session cut to a fraction of a second."""

import json
import os
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coding_study.domain.code_intelligence import GOPLS, JDTLS, LSP_DIRECTORY
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

    def play(self, *steps: Mapping[str, object]) -> None:
        self.path.write_text(json.dumps(steps), encoding="utf-8")

    @property
    def arguments(self) -> tuple[str, ...]:
        return (sys.executable, str(FAKE_LANGUAGE_SERVER), str(self.path), "--stdio")

    @property
    def command(self) -> LanguageServerCommand:
        return LanguageServerCommand(self.arguments)

    def calls(self) -> list[dict[str, Any]]:
        return _records(self.path.with_suffix(".calls"))

    def pids(self) -> list[int]:
        return [call["pid"] for call in self.calls()]

    def received(self) -> list[dict[str, Any]]:
        """Every message the servers read, in the order they read them."""
        return _records(self.path.with_suffix(".received"))

    def methods(self) -> list[str]:
        return [message["method"] for message in self.received() if "method" in message]

    def ready(self) -> bool:
        """Whether a server played every step of its script and waits for messages."""
        return self.path.with_suffix(".ready").exists()

    def gate(self, name: str) -> Path:
        """A file a `wait_for` step waits on; the test creates it to let the server go on."""
        return self.path.with_name(name)


def _records(log: Path) -> list[dict[str, Any]]:
    """The complete lines of a log a server is still appending to; a message of hundreds of
    kilobytes reaches the file in several writes, so the last line may be half there."""
    if not log.exists():
        return []
    *complete, _unfinished = log.read_text(encoding="utf-8").split("\n")
    return [json.loads(line) for line in complete]


def fake_node(directory: Path, script: ScriptedServer) -> str:
    """A `node` that runs the fake language server on the script, in a new `directory`; the new
    `PATH`. The doctor's version command and the session's server command both run it."""
    directory.mkdir()
    node = directory / "node"
    node.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_LANGUAGE_SERVER}" "{script.path}" "$@"\n'
    )
    node.chmod(0o755)
    return f"{directory}{os.pathsep}{os.environ['PATH']}"


def install_fake_basedpyright(workspace: Path) -> None:
    """The two files `cstudy` looks for in `.cs/lsp/`, so that Python counts as installed."""
    package = workspace / ".cs" / "lsp" / "node_modules" / "basedpyright"
    package.mkdir(parents=True)
    for name in ("index.js", "langserver.index.js"):
        (package / name).write_text("")


def install_fake_jdtls(workspace: Path) -> None:
    """The file `cstudy` looks for in `.cs/lsp/`, so that Java counts as installed."""
    core = workspace / LSP_DIRECTORY / str(JDTLS.script)
    core.parent.mkdir(parents=True)
    core.write_text("")


def fake_jdk(home: Path, script: ScriptedServer, feature: int = 25) -> str:
    """A JDK home of release `feature`, as its `release` file says, whose `java` runs the fake
    language server on the script; the home, for `JAVA_HOME`. JDT LS runs on the selected JDK."""
    java = home / "bin" / "java"
    java.parent.mkdir(parents=True)
    java.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_LANGUAGE_SERVER}" "{script.path}" "$@"\n'
    )
    java.chmod(0o755)
    (home / "release").write_text(f'JAVA_VERSION="{feature}.0.1"\n')
    return str(home)


FAKE_GO_RELEASE = "go1.27.3"
"""What the fake `go` says the selected Go is, so gopls is pinned at 0.24.0 on any machine."""
RUSTUP_PROXY_ERROR = (
    "error: Unknown binary 'rust-analyzer' in official toolchain 'stable-aarch64-apple-darwin'."
)


def _runs_the_fake(path: Path, script: ScriptedServer) -> None:
    """An executable at `path` that runs the fake language server on the script, with its own
    path as the server script, so the fake prints the version of the server it is named after."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_LANGUAGE_SERVER}" "{script.path}" "$0" "$@"\n'
    )
    path.chmod(0o755)


def install_fake_gopls(workspace: Path, script: ScriptedServer) -> None:
    """`.cs/lsp/bin/gopls`, where `go install` puts it, running the fake language server."""
    _runs_the_fake(workspace / LSP_DIRECTORY / str(GOPLS.script), script)


def fake_go(directory: Path) -> None:
    """A `go` in `directory`, which is on the served PATH, whose `go env GOVERSION` says
    `FAKE_GO_RELEASE`; anything else goes to the real `go`, if there is one."""
    real = shutil.which("go")
    otherwise = f'exec "{real}" "$@"' if real else "exit 127"
    go = directory / "go"
    go.write_text(
        "#!/bin/sh\n"
        f'if [ "$1 $2" = "env GOVERSION" ]; then echo {FAKE_GO_RELEASE}; exit 0; fi\n'
        f"{otherwise}\n"
    )
    go.chmod(0o755)


def fake_rust_analyzer(directory: Path, script: ScriptedServer) -> None:
    """A `rust-analyzer` in `directory`, which is on the served PATH, running the fake."""
    _runs_the_fake(directory / "rust-analyzer", script)


def fake_rustup_proxy(directory: Path) -> None:
    """The rustup proxy of a `rust-analyzer` component that is not installed, in `directory`."""
    proxy = directory / "rust-analyzer"
    proxy.write_text(f'#!/bin/sh\necho "{RUSTUP_PROXY_ERROR}" >&2\nexit 1\n')
    proxy.chmod(0o755)
