"""Running a build tool for at most a fixed time (docs/specs/runners.md#build-timeouts).

A wedged toolchain (a lock held forever, a stuck proc-macro, a network attempt) must not hang
`cstudy`. The tool runs in a session of its own, so on expiry or an interrupt the whole process
group is killed, not only the process that was started: `pnpm` and `gradlew` start the real tool
as a child.
"""

import os
import signal
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path

from coding_study.domain.errors import RunnerStartError

DEFAULT_BUILD_TIMEOUT_SECONDS = 300.0
"""Generous for a cold build of the runner crates or the standard library on a loaded machine."""
DRAIN_SECONDS = 5.0
"""How long to wait for output after the group is killed; a process that left the group may
still hold the pipes."""
TAIL_LINES = 5
_EMPTY = b""


class BoundedProcess:
    """Runs one kind of build step with a time limit; `step` names it in the error."""

    def __init__(self, step: str, timeout_seconds: float = DEFAULT_BUILD_TIMEOUT_SECONDS) -> None:
        self._step = step
        self._timeout_seconds = timeout_seconds

    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None
    ) -> "subprocess.CompletedProcess[bytes]":
        """Standard output and standard error captured apart.

        Raises RunnerStartError when the step outlives its limit, and OSError when the program
        cannot be started."""
        return self._execute(command, cwd, environment, subprocess.PIPE)

    def run_interleaved(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None
    ) -> "subprocess.CompletedProcess[bytes]":
        """Standard error merged into standard output, as the tool wrote them; `stderr` is
        empty. Raises as `run` does."""
        return self._execute(command, cwd, environment, subprocess.STDOUT)

    def _execute(
        self,
        command: Sequence[str],
        cwd: Path,
        environment: Mapping[str, str] | None,
        stderr: int,
    ) -> "subprocess.CompletedProcess[bytes]":
        with subprocess.Popen(
            command,
            cwd=cwd,
            env=None if environment is None else dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
            start_new_session=True,
        ) as process:
            try:
                output, errors = process.communicate(timeout=self._timeout_seconds)
            except subprocess.TimeoutExpired:
                raise self._expired(process) from None
            except BaseException:
                _kill_group(process)
                raise
        return subprocess.CompletedProcess(command, process.returncode, output, errors or _EMPTY)

    def _expired(self, process: "subprocess.Popen[bytes]") -> RunnerStartError:
        _kill_group(process)
        try:
            output, errors = process.communicate(timeout=DRAIN_SECONDS)
        except subprocess.TimeoutExpired:
            output, errors = _EMPTY, _EMPTY
        text = (output + b"\n" + (errors or _EMPTY)).decode("utf-8", errors="replace")
        tail = [line for line in text.splitlines() if line.strip()][-TAIL_LINES:]
        message = f"{self._step} did not finish within {self._timeout_seconds:g} s and was stopped"
        return RunnerStartError(message, tail)


def _kill_group(process: "subprocess.Popen[bytes]") -> None:
    """Kill the tool and everything it started, then reap it. The group id is the tool's pid
    because it leads a session of its own."""
    with suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    process.kill()
    process.wait()
