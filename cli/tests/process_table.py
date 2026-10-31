"""The machine's processes, for tests of what a `cstudy` killed with SIGKILL leaves running
(docs/specs/runners.md#process-lifecycle)."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

PROCESS_LIST = ("ps", "-axww", "-o", "pid=,ppid=,pgid=,args=")
ORPHAN_PATIENCE_SECONDS = 2.0
"""How soon after `cstudy` died nothing it started may run any more."""
POLL_SECONDS = 0.05
STARTUP_PATIENCE_SECONDS = 30.0
DYING_CSTUDY = Path(__file__).resolve().parent / "fixtures" / "dying_cstudy.py"


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    parent: int
    group: int
    command: str


def running_processes() -> list[Process]:
    listing = subprocess.run(PROCESS_LIST, capture_output=True, text=True, check=True).stdout
    processes: list[Process] = []
    for line in listing.splitlines():
        pid, parent, group, *command = line.split(maxsplit=3)
        processes.append(Process(int(pid), int(parent), int(group), command[0] if command else ""))
    return processes


def groups_of_children(pid: int) -> set[int]:
    """The process groups of `pid`'s children: each one's, and those of what they started and
    kept in their group."""
    return {process.group for process in running_processes() if process.parent == pid}


def left_running(groups: set[int], directories: Iterable[Path] = ()) -> list[Process]:
    """The processes of `groups`, and those started from `directories`, that still run after
    `ORPHAN_PATIENCE_SECONDS`."""
    prefixes = tuple(
        f"{path}{os.sep}" for directory in directories for path in {directory, directory.resolve()}
    )
    deadline = time.monotonic() + ORPHAN_PATIENCE_SECONDS
    while True:
        left = [
            process
            for process in running_processes()
            if process.group in groups or (prefixes and process.command.startswith(prefixes))
        ]
        if not left or time.monotonic() > deadline:
            return left
        time.sleep(POLL_SECONDS)


class DyingCstudy:
    """tests/fixtures/dying_cstudy.py running one scenario, until `kill` ends it alone."""

    def __init__(self, scenario: str, path: Path) -> None:
        self._process = subprocess.Popen(
            [sys.executable, str(DYING_CSTUDY), scenario, str(path)],
            stdout=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

    def said(self) -> list[str]:
        """The words of the next line it printed."""
        assert self._process.stdout is not None
        return self._process.stdout.readline().split()

    def wait_for(self, path: Path) -> None:
        deadline = time.monotonic() + STARTUP_PATIENCE_SECONDS
        while not path.exists():
            assert self._process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(POLL_SECONDS)

    def kill(self) -> set[int]:
        """SIGKILL to it alone; the process groups of the children it had then."""
        children = groups_of_children(self._process.pid)
        self._process.kill()
        self._process.wait()
        assert self._process.stdout is not None
        self._process.stdout.close()
        return children


def kill_all(processes: Iterable[Process]) -> None:
    """What a failing test left running would otherwise run on for good; never this process's
    own group."""
    for process in processes:
        if process.group != os.getpgrp():
            with suppress(ProcessLookupError, PermissionError):
                os.killpg(process.group, signal.SIGKILL)
        with suppress(ProcessLookupError, PermissionError):
            os.kill(process.pid, signal.SIGKILL)
