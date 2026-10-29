"""Where the debug servers of Go and Rust are on this machine (docs/specs/runners.md#debug-mode).

`go install` puts Delve in `GOBIN`, or in `bin` of the first `GOPATH` entry (`~/go` by default),
which is often not on PATH. Xcode keeps `debugserver` inside LLDB.framework, never on PATH: the
developer directory (`DEVELOPER_DIR`, or `xcode-select -p`) says which Xcode or Command Line
Tools to take it from, as it does for `lldb`. LLDB packages on Linux put `lldb-server` on PATH.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from coding_study.application.ports import DebugServer
from coding_study.domain.debugging import (
    DEBUGSERVER,
    DELVE,
    INSTALL_DEBUGSERVER,
    INSTALL_DELVE,
    INSTALL_LLDB_SERVER,
    LLDB_SERVER,
)
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.guides import TOOLCHAINS_GUIDE
from coding_study.domain.problem import Language

MACOS = "darwin"
DEFAULT_GOPATH = "go"
"""Relative to the home directory."""
FRAMEWORK_SERVER = Path("LLDB.framework/Resources/debugserver")
XCODE_FRAMEWORKS = "SharedFrameworks"
"""Next to an Xcode's developer directory (`Xcode.app/Contents/Developer`)."""
TOOLS_FRAMEWORKS = Path("Library/PrivateFrameworks")
"""Inside the Command Line Tools' developer directory."""
COMMAND_LINE_TOOLS = Path("/Library/Developer/CommandLineTools")
DEBUGSERVER_SETTING = "LLDB_DEBUGSERVER_PATH"
"""LLDB's own variable for the debugserver it starts."""
XCODE_SELECT_TIMEOUT_SECONDS = 10.0


def selected_developer_directory() -> Path | None:
    """`xcode-select -p`: the Xcode or Command Line Tools that `lldb` uses."""
    try:
        completed = subprocess.run(
            ("xcode-select", "-p"),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=XCODE_SELECT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    selected = completed.stdout.strip()
    return Path(selected) if completed.returncode == 0 and selected else None


@dataclass(frozen=True, slots=True)
class Machine:
    """What the search looks at; tests describe other machines."""

    environment: Mapping[str, str]
    home: Path
    platform: str = sys.platform
    developer_directory: Callable[[], Path | None] = selected_developer_directory


def this_machine() -> Machine:
    return Machine(os.environ, Path.home())


class InstalledDebugServers:
    """`DebugServers` found on a machine; nothing is searched until a server is asked for."""

    def __init__(self, machine: Machine) -> None:
        self._machine = machine

    def delve(self) -> DebugServer:
        return DebugServer(DELVE, INSTALL_DELVE, _first_executable(self._delve_candidates()))

    def lldb_server(self) -> DebugServer:
        if self._machine.platform == MACOS:
            found = _first_executable(self._debugserver_candidates())
            return DebugServer(DEBUGSERVER, INSTALL_DEBUGSERVER, found)
        found = _first_executable(self._on_path(LLDB_SERVER))
        return DebugServer(LLDB_SERVER, INSTALL_LLDB_SERVER, found)

    def _delve_candidates(self) -> Iterator[Path]:
        yield from self._on_path(DELVE)
        environment = self._machine.environment
        go_bin = environment.get("GOBIN")
        if go_bin:
            yield Path(go_bin) / DELVE
        go_paths = [entry for entry in environment.get("GOPATH", "").split(os.pathsep) if entry]
        go_path = Path(go_paths[0]) if go_paths else self._machine.home / DEFAULT_GOPATH
        yield go_path / "bin" / DELVE

    def _debugserver_candidates(self) -> Iterator[Path]:
        setting = self._machine.environment.get(DEBUGSERVER_SETTING)
        if setting:
            yield Path(setting)
        yield from self._on_path(DEBUGSERVER)
        developer = self._developer_directory()
        if developer is not None:
            yield developer.parent / XCODE_FRAMEWORKS / FRAMEWORK_SERVER
            yield developer / TOOLS_FRAMEWORKS / FRAMEWORK_SERVER
        yield COMMAND_LINE_TOOLS / TOOLS_FRAMEWORKS / FRAMEWORK_SERVER

    def _developer_directory(self) -> Path | None:
        selected = self._machine.environment.get("DEVELOPER_DIR")
        return Path(selected) if selected else self._machine.developer_directory()

    def _on_path(self, name: str) -> Iterator[Path]:
        found = shutil.which(name, path=self._machine.environment.get("PATH", os.defpath))
        if found:
            yield Path(found)


def require_installed(server: DebugServer, language: Language) -> Path:
    """The server's path; RunnerStartError (exit 4) with its install step when it is missing."""
    if server.path is None:
        raise RunnerStartError(
            f"cannot debug {language}: {server.name} was not found; {server.install} "
            f"({TOOLCHAINS_GUIDE}#{language})"
        )
    return server.path


def _first_executable(candidates: Iterable[Path]) -> Path | None:
    return next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)
