"""Running the user's code under an IDE debugger (docs/specs/runners.md#debug-mode).

`cstudy test --debug` starts the runner with its language's debug agent bound to the loopback
interface and leaves the IDE to attach. The ready lines are a stable contract: IDE tasks match them.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from coding_study.domain.layout import JVM_LANGUAGES, PYTHON_PROJECT
from coding_study.domain.problem import Language

DEBUG_HOST = "127.0.0.1"
"""Debug agents never listen on another interface."""
DEFAULT_DEBUG_PORTS: Mapping[Language, int] = {
    Language.PYTHON: 5678,
    Language.TYPESCRIPT: 9229,
    Language.JAVA: 5005,
    Language.KOTLIN: 5005,
    Language.GO: 2345,
    Language.RUST: 12345,
}
"""debugpy, the Node inspector, JDWP and Delve each use their usual port; Rust's debug server has no
usual one, so it takes 12345."""
DEBUGPY_INSTALL_COMMAND = f"uv add --dev debugpy --directory {PYTHON_PROJECT}"
"""Puts debugpy in a workspace's venv, also one created before the template listed it."""
DELVE = "dlv"
DELVE_VERSION = "1.27.2"
"""The Delve release `cstudy test --debug` is tested with for Go."""
DELVE_REQUIRING_NEWER_GO = (1, 27)
DELVE_MINIMUM_GO = (1, 25)
"""From Delve 1.27 on, the oldest Go it debugs: it refuses a binary built with an older one
(`Go version go1.24.x is too old for this version of Delve`). It is cstudy's own minimum, so a Go
that Delve refuses is one the Go row already warns about."""
DEBUGSERVER = "debugserver"
LLDB_SERVER = "lldb-server"
"""Rust's debug server: Xcode's `debugserver` on macOS, LLDB's `lldb-server` on Linux."""
INSTALL_DELVE = f"run `go install github.com/go-delve/delve/cmd/dlv@v{DELVE_VERSION}`"
INSTALL_DEBUGSERVER = "run `xcode-select --install`"
INSTALL_LLDB_SERVER = "install your distribution's lldb package"


@dataclass(frozen=True, slots=True)
class DebugRequest:
    """`--debug-port` and `--debug-connect`; the language fills in the rest."""

    port: int | None = None
    connect: bool = False


@dataclass(frozen=True, slots=True)
class DebugSession:
    language: Language
    port: int
    connect: bool = False
    """JVM only: the runner connects to an IDE that is already listening, instead of
    listening for the IDE."""

    @property
    def address(self) -> str:
        return f"{DEBUG_HOST}:{self.port}"

    @property
    def ready_line(self) -> str:
        """What `cstudy test --debug` prints, once, when the IDE can attach (or, when
        connecting, as the runner starts)."""
        if self.connect:
            return f"cstudy: connecting to debugger at {self.address} ({self.language})"
        return f"cstudy: waiting for debugger on {self.address} ({self.language})"


def delve_minimum_go(delve_version: str) -> tuple[int, int] | None:
    """The oldest Go (major, minor) the Delve release debugs; None when it is not known to refuse
    any that cstudy builds with."""
    major, minor, *_ = (int(part) for part in delve_version.split("."))
    return DELVE_MINIMUM_GO if (major, minor) >= DELVE_REQUIRING_NEWER_GO else None


def debug_session(request: DebugRequest, language: Language) -> DebugSession:
    """Raises ValueError when `--debug-connect` meets a language that has no connect mode."""
    if request.connect and language not in JVM_LANGUAGES:
        raise ValueError(f"--debug-connect is only for java and kotlin, not {language}")
    port = DEFAULT_DEBUG_PORTS[language] if request.port is None else request.port
    return DebugSession(language, port, request.connect)


CONTAINER_DEBUG_HOST = "0.0.0.0"
"""In a dev stack the forwarder, another container, relays the debug port, so the agent listens on
every interface of the app's container; the forwarder publishes it on 127.0.0.1 alone."""
NODE = "node"
PYTHON_INTERPRETER_PREFIX = "python"


@dataclass(frozen=True, slots=True)
class ContainerDebugAgent:
    """`cstudy dev --debug` (docs/specs/service-projects.md#your-own-ide): `commands.run` under its
    language's debug agent, on that language's usual port."""

    port: int
    command: tuple[str, ...]


def container_debug_agent(language: Language, run: tuple[str, ...]) -> ContainerDebugAgent:
    """Node's inspector for a run that starts `node`, debugpy for one that starts a Python
    interpreter; debugpy must be installed in the project. Neither waits for a debugger, so the
    app answers its health path as it does without one.

    Raises ValueError for another language or another first word."""
    port = DEFAULT_DEBUG_PORTS[language]
    address = f"{CONTAINER_DEBUG_HOST}:{port}"
    program, *arguments = run
    name = program.rsplit("/", 1)[-1]
    if language is Language.TYPESCRIPT and name == NODE:
        return ContainerDebugAgent(port, (program, f"--inspect={address}", *arguments))
    if language is Language.PYTHON and name.startswith(PYTHON_INTERPRETER_PREFIX):
        return ContainerDebugAgent(
            port, (program, "-m", "debugpy", "--listen", address, *arguments)
        )
    raise ValueError(
        f"cstudy dev --debug runs a typescript app's node or a python app's interpreter under "
        f"its debugger; this {language} app runs {' '.join(run)}"
    )
