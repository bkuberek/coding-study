"""Whether processes are alive, and ending the ones a run started, also once `cstudy` itself died
(docs/specs/runners.md#process-lifecycle).

Run as a script, this file is the process of an `OrphanGuard`. It imports only the standard
library, so that process starts in a few milliseconds without `site` and needs nothing installed.
"""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import IO, Self

PROCESS_LIST = ("ps", "-axww", "-o", "pid=,args=")
"""Every process and the command line it started with, on macOS. Linux reads `PROC_ROOT` instead:
BusyBox's `ps` (Alpine) rejects `-x` and would list nothing."""
PROC_ROOT = Path("/proc")
PROCESS_LIST_TIMEOUT_SECONDS = 10.0
EXIT_POLL_SECONDS = 0.01
GUARD_READ_BYTES = 4096


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


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


class OrphanGuard:
    """A process of its own that kills the process groups it watches, and every process started
    from `directory`, once `cstudy` dies, however it dies: SIGKILL and a crash included.

    The guard reads its standard input, a pipe whose writing end only `cstudy` holds, until the
    pipe ends; the kernel closes that end when `cstudy` exits, so nothing polls. `watch` sends a
    group's id through the pipe. `release` kills the guard and only then closes the pipe, so a run
    that ends normally never sets it off; a guard collected as garbage unreleased closes its pipe,
    and kills what it watches.

    Start the guard before the processes it watches, so that a guard that cannot start leaves
    nothing behind, and release it after killing them, so that a `cstudy` that dies during that
    cleanup still leaves nothing behind. The guard runs in a session of its own, where no
    terminal's signals reach it.
    """

    def __init__(self, directory: Path | None = None) -> None:
        arguments = () if directory is None else (str(directory),)
        self._process = subprocess.Popen(
            [sys.executable, "-I", "-S", __file__, *arguments],
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        assert self._process.stdin is not None
        self._pipe: IO[bytes] = self._process.stdin

    def watch(self, group: int) -> None:
        """A guard that someone else killed guards nothing more."""
        with suppress(BrokenPipeError):
            self._pipe.write(f"{group}\n".encode())

    def release(self) -> None:
        self._process.kill()
        self._process.wait()
        self._pipe.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.release()


def _guard(directories: Sequence[str]) -> None:
    """The guard's process: once standard input ends, kills each process group read from it, then
    every process started from `directories`."""
    watched = bytearray()
    with suppress(OSError):
        while chunk := os.read(sys.stdin.fileno(), GUARD_READ_BYTES):
            watched += chunk
    for group in watched.split():
        with suppress(OSError, ValueError):
            os.killpg(int(group), signal.SIGKILL)
    for directory in directories:
        kill_processes_started_from(Path(directory), 0)


if __name__ == "__main__":
    _guard(sys.argv[1:])
