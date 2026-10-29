"""Process-level support for a runner under a debug agent (docs/specs/runners.md#debug-mode).

`SubprocessRunner` follows the runner's events like for any other run; what is special here is
that the runner's own output says when the agent listens (or could not connect), and that stopping
`cstudy` must never leave the runner holding the debug port.
"""

import signal
from collections import deque
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType

from coding_study.application.ports import DebugLaunch

TAIL_LINES = 20
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP)

type _Handler = Callable[[int, FrameType | None], object] | int | signal.Handlers | None


class _GrowingText:
    """The text of a file that another process keeps appending to."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._offset = 0
        self._text = ""

    def read(self) -> str:
        """Everything written so far."""
        try:
            with self._path.open("rb") as stream:
                stream.seek(self._offset)
                added = stream.read()
        except FileNotFoundError:
            return self._text
        self._offset += len(added)
        self._text += added.decode("utf-8", errors="replace")
        return self._text


class DebugOutput:
    """What a runner started under a debug agent has printed to standard output and error."""

    def __init__(self, debug: DebugLaunch, stdout: Path, stderr: Path) -> None:
        self._debug = debug
        self._streams = (_GrowingText(stdout), _GrowingText(stderr))

    def agent_listens(self) -> bool:
        marker = self._debug.ready_marker
        printed = bool(marker) and any(marker in text for text in self._texts())
        return printed or _has_content(self._debug.ready_file)

    def refused_connection(self) -> bool:
        """The runner, which connects to the IDE, found nobody listening."""
        marker = self._debug.refused_marker
        connecting = self._debug.session.connect
        return connecting and bool(marker) and any(marker in text for text in self._texts())

    def tail(self) -> tuple[str, ...]:
        """The last lines of standard output, then of standard error."""
        lines = (deque(text.splitlines(), maxlen=TAIL_LINES) for text in self._texts())
        return tuple(line for stream in lines for line in stream)

    def _texts(self) -> list[str]:
        return [stream.read() for stream in self._streams]


def _has_content(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


@contextmanager
def terminated_like_interrupt() -> Generator[None]:
    """SIGTERM and SIGHUP, which an IDE sends when its task is stopped, unwind like Ctrl-C so the
    runner's process group is killed instead of left holding the debug port.

    Does nothing off the main thread, where signal handlers cannot be set.
    """
    previous: dict[signal.Signals, _Handler] = {}

    def stop(signal_number: int, _frame: FrameType | None) -> None:
        raise SystemExit(128 + signal_number)

    try:
        for stop_signal in STOP_SIGNALS:
            previous[stop_signal] = signal.signal(stop_signal, stop)
    except ValueError:
        pass
    try:
        yield
    finally:
        for stop_signal, handler in previous.items():
            signal.signal(stop_signal, handler)
