"""Process-level support for a runner under a debug agent (docs/specs/runners.md#debug-mode).

`SubprocessRunner` follows the runner's events like for any other run; what is special here is
that the runner's own output says when the agent listens (or could not connect), and that ending a
debug run, however it ends, must never leave the runner going or holding the debug port.
"""

import os
import signal
import subprocess
import time
from collections import deque
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from types import FrameType

from coding_study.adapters.process_liveness import is_alive
from coding_study.application.ports import DebugLaunch

TAIL_LINES = 20
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP)
PROCESS_LIST = ("ps", "-axww", "-o", "pid=,args=")
"""Every process and the command line it started with, on macOS. Linux reads `PROC_ROOT` instead:
BusyBox's `ps` (Alpine) rejects `-x` and would list nothing."""
PROC_ROOT = Path("/proc")
PROCESS_LIST_TIMEOUT_SECONDS = 10.0
EXIT_POLL_SECONDS = 0.01

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


def kill_processes_started_from(directory: Path | None, grace_seconds: float) -> None:
    """Kills every process running a file of `directory`, then waits up to `grace_seconds` for
    them to be gone.

    A debug server that lets go of its runner (`debugserver` after lldb's `detach`) exits and
    leaves it going, followed by nobody. The server starts the runner in a process group of its
    own, so the server's group says nothing about it; the launch's private directory, which only
    this run executes from, does. Only a process whose executable (the first word of its command
    line) is inside `directory` is killed: not one that merely names a file there.

    Does nothing without a directory, or where neither `/proc` nor `ps` can say what is running."""
    if directory is None:
        return
    running = _started_from(directory)
    for pid in running:
        with suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic() + grace_seconds
    while any(is_alive(pid) for pid in running) and time.monotonic() < deadline:
        time.sleep(EXIT_POLL_SECONDS)


def _started_from(directory: Path, proc_root: Path | None = None) -> list[int]:
    proc_root = proc_root or PROC_ROOT
    prefixes = tuple(f"{path}{os.sep}" for path in {directory, directory.resolve()})
    if proc_root.is_dir():
        return [pid for pid, command in _proc_commands(proc_root) if command.startswith(prefixes)]
    return [pid for pid, command in _listed_commands() if command.lstrip().startswith(prefixes)]


def _proc_commands(proc_root: Path) -> Iterator[tuple[int, str]]:
    """Each process and its executable as it was started: the first word of `cmdline`, which
    separates its arguments with NUL, so a path with a space stays whole."""
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().partition(b"\0")[0]
        except OSError:
            continue
        yield int(entry.name), command.decode(errors="replace")


def _listed_commands() -> Iterator[tuple[int, str]]:
    """Each process and its whole command line, from `ps`."""
    try:
        listing = subprocess.run(
            PROCESS_LIST,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=PROCESS_LIST_TIMEOUT_SECONDS,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return
    for line in listing.splitlines():
        pid, _, command_line = line.strip().partition(" ")
        if pid.isdigit():
            yield int(pid), command_line
