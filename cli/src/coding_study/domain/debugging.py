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


def debug_session(request: DebugRequest, language: Language) -> DebugSession:
    """Raises ValueError when `--debug-connect` meets a language that has no connect mode."""
    if request.connect and language not in JVM_LANGUAGES:
        raise ValueError(f"--debug-connect is only for java and kotlin, not {language}")
    port = DEFAULT_DEBUG_PORTS[language] if request.port is None else request.port
    return DebugSession(language, port, request.connect)
