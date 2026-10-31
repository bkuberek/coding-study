"""A Rust project's native suite, run by `cstudy` itself (docs/specs/runners.md#rust-projects).

libtest has no stable machine-readable report, so no runner process hosts the suite: each test
binary lists its tests (`--list --format terse`), and each test runs as a process of its own
(`<binary> --exact <name> --nocapture`), judged by its exit code (`libtest.finished_outcome`). A
test that hangs past the hang guard has its process group killed, and one that aborts ends only
its own process: the next test runs, and nothing restarts.

`cstudy test --debug` runs one test under Rust's debug server, which holds it at its entry point
until the IDE connects. The server sends the test's output to the debugger, so `debugserver` writes
it to files instead (`--stdout-path`, `--stderr-path`), and the outcome is read from them.
"""

import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.adapters.debug_process import (
    kill_processes_started_from,
    terminated_like_interrupt,
)
from coding_study.adapters.languages.rust.libtest import (
    LIBTEST_ERROR,
    FinishedTest,
    debugged_outcome,
    finished_outcome,
    listed_tests,
)
from coding_study.adapters.languages.rust.project_build import BuiltTests, SuiteTarget
from coding_study.application.ports import SuiteListener
from coding_study.domain.debugging import LLDB_SERVER, DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.project_test_runs import TEST_ID_SEPARATOR
from coding_study.domain.runs import Raised, TimedOut, UserError
from coding_study.domain.suite_runs import SuiteJob, SuiteOutcome, SuiteTest

LIST_ARGUMENTS = ("--list", "--format", "terse")
EXACT = "--exact"
NO_CAPTURE = "--nocapture"
GDBSERVER_MODE = "gdbserver"
READY_FILE = "debug-port"
DEBUG_STDOUT = "stdout.txt"
DEBUG_STDERR = "stderr.txt"
SERVER_OUTPUT = "debug-server.txt"
ONE_DEBUGGED_TEST = "a debug run of a Rust project runs one test; pick it with --case"
UNKNOWN_UNDER_LLDB_SERVER = "the outcome of a test debugged under lldb-server is not known"
UNCLEAN_ENVIRONMENT = ("RUST_BACKTRACE", "RUST_LIB_BACKTRACE")
"""Left out of a test's environment: with them unset, a panic's message ends with libtest's note
on backtraces, which is where `libtest` finds its end."""
UNCLEAN_PREFIX = "RUST_TEST_"
"""libtest's own settings (threads, capture), which `cstudy` sets on the command line."""
POLL_SECONDS = 0.01
EXIT_GRACE_SECONDS = 5.0
MILLISECONDS_PER_SECOND = 1000
SIGNAL_EXIT_BASE = 128
"""A process a signal ended exits, as a shell reports it, with 128 plus the signal's number."""
SERVER_TAIL_LINES = 20


@dataclass(frozen=True, slots=True)
class DebuggedTest:
    """One test under the debug server."""

    command: tuple[str, ...]
    cwd: Path
    ready_file: Path
    """The server writes its port there once it listens."""
    scratch: Path
    """The run's private directory: whatever still runs from it when the session ends is
    killed."""
    announce: Callable[[], None]
    """Prints the session's ready line, once the server listens."""


class LibtestProcesses(Protocol):
    """Starting test binaries; tests substitute a fake."""

    def run(self, command: Sequence[str], cwd: Path, limit_ms: int) -> FinishedTest | None:
        """The process's exit and output; None when it ran past `limit_ms` and its process
        group was killed."""
        ...

    def debug(self, test: DebuggedTest) -> None:
        """Runs the debug server until it ends, with no time limit.

        Raises RunnerStartError when the server ends before it listens.
        """
        ...


@dataclass(frozen=True, slots=True)
class DebugTarget:
    """The debug server one test runs under, for `cstudy test --debug`."""

    session: DebugSession
    server: str
    """`debugserver` or `lldb-server`."""
    path: Path
    announce: Callable[[str], None]


class LibtestSuite:
    """Runs the built test targets of one project, in path order, telling `listener` of each
    test as it starts and ends."""

    def __init__(
        self, processes: LibtestProcesses, job: SuiteJob, listener: SuiteListener | None
    ) -> None:
        self._processes = processes
        self._job = job
        self._root = Path(job.root)
        self._listener = listener

    def run(self, built: BuiltTests) -> tuple[SuiteTest, ...]:
        tests: list[SuiteTest] = []
        for target in built.targets:
            if target.binary is None:
                tests.append(self._failed_target(target))
                continue
            listing = self._listing(target, target.binary)
            if isinstance(listing, SuiteTest):
                tests.append(listing)
                continue
            tests += [self._test(target, target.binary, name) for name in listing]
        return tuple(tests)

    def debug(
        self, built: BuiltTests, debugging: DebugTarget
    ) -> tuple[tuple[SuiteTest, ...], str | None]:
        """The first test the suite would run, under the debug server, and the targets that did
        not compile; the reason the others did not run, when there are others."""
        tests: list[SuiteTest] = []
        chosen: list[tuple[SuiteTarget, Path, str]] = []
        for target in built.targets:
            if target.binary is None:
                tests.append(self._failed_target(target))
                continue
            listing = self._listing(target, target.binary)
            if isinstance(listing, SuiteTest):
                tests.append(listing)
                continue
            chosen += [(target, target.binary, name) for name in listing]
        if not chosen or built.scratch is None:
            return tuple(tests), None
        target, binary, name = chosen[0]
        tests.append(self._debugged(target, binary, name, debugging, built.scratch))
        return tuple(tests), ONE_DEBUGGED_TEST if len(chosen) > 1 else None

    def _listing(self, target: SuiteTarget, binary: Path) -> tuple[str, ...] | SuiteTest:
        """The selected tests of `binary`, or the `error` of a binary that cannot list them."""
        listed = self._processes.run(
            (str(binary), *LIST_ARGUMENTS), self._root, self._job.hang_guard_ms
        )
        if listed is None or listed.exit_code != 0:
            output = "" if listed is None else listed.output.strip()
            error = UserError(LIBTEST_ERROR, f"cannot list the tests of {target.path}: {output}")
            return self._failed_target(SuiteTarget(target.path, error=error))
        ids = ((name, _test_id(target, name)) for name in listed_tests(listed.output))
        return tuple(name for name, test_id in ids if _selected(test_id, self._job.select))

    def _test(self, target: SuiteTarget, binary: Path, name: str) -> SuiteTest:
        test_id = _test_id(target, name)
        self._started(test_id)
        limit = self._job.hang_guard_ms
        command = (str(binary), EXACT, name, NO_CAPTURE)
        finished = self._processes.run(command, self._root, limit)
        outcome = (
            TimedOut(limit) if finished is None else finished_outcome(name, finished, self._root)
        )
        return self._finished(test_id, outcome)

    def _debugged(
        self, target: SuiteTarget, binary: Path, name: str, debugging: DebugTarget, scratch: Path
    ) -> SuiteTest:
        test_id = _test_id(target, name)
        self._started(test_id)
        stdout, stderr = scratch / DEBUG_STDOUT, scratch / DEBUG_STDERR
        lldb_server = debugging.server == LLDB_SERVER
        server = (str(debugging.path), GDBSERVER_MODE) if lldb_server else (str(debugging.path),)
        output = () if lldb_server else (f"--stdout-path={stdout}", f"--stderr-path={stderr}")
        ready_file = scratch / READY_FILE
        session = debugging.session
        test = (str(binary), EXACT, name, NO_CAPTURE)
        command = (*server, *output, "--named-pipe", str(ready_file), session.address, "--", *test)
        announce = lambda: debugging.announce(session.ready_line)  # noqa: E731
        self._processes.debug(DebuggedTest(command, self._root, ready_file, scratch, announce))
        if lldb_server:
            unknown: SuiteOutcome = Raised(UserError(LIBTEST_ERROR, UNKNOWN_UNDER_LLDB_SERVER), 0)
            return self._finished(test_id, unknown)
        text = _read(stdout) + _read(stderr)
        return self._finished(test_id, debugged_outcome(name, text, self._root))

    def _failed_target(self, target: SuiteTarget) -> SuiteTest:
        """One `error` result for a target that did not compile, or whose tests cannot be
        listed, with the target's path as its id."""
        assert target.error is not None
        self._started(target.path)
        return self._finished(target.path, Raised(target.error, 0))

    def _started(self, test_id: str) -> None:
        if self._listener is not None:
            self._listener.test_started(test_id)

    def _finished(self, test_id: str, outcome: SuiteOutcome) -> SuiteTest:
        test = SuiteTest(test_id, outcome)
        if self._listener is not None:
            self._listener.test_finished(test)
        return test


def _test_id(target: SuiteTarget, name: str) -> str:
    return f"{target.path}{TEST_ID_SEPARATOR}{name}"


def _selected(test_id: str, select: tuple[str, ...]) -> bool:
    """Every test without a selection; else one named by its id or the id's last part."""
    if not select:
        return True
    return any(
        test_id == wanted or test_id.endswith(f"{TEST_ID_SEPARATOR}{wanted}") for wanted in select
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


class SubprocessTests:
    """`LibtestProcesses` as real processes, each in a process group of its own, so a test that
    started processes of its own is ended with them."""

    def run(self, command: Sequence[str], cwd: Path, limit_ms: int) -> FinishedTest | None:
        started = time.perf_counter_ns()
        process = _start(command, cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            output, _ = process.communicate(timeout=limit_ms / MILLISECONDS_PER_SECOND)
        except subprocess.TimeoutExpired:
            _kill_group(process)
            process.communicate()
            return None
        except BaseException:
            _kill_group(process)
            raise
        duration = time.perf_counter_ns() - started
        return FinishedTest(
            _exit_code(process.returncode), output.decode(errors="replace"), duration
        )

    def debug(self, test: DebuggedTest) -> None:
        test.ready_file.write_bytes(b"")
        server_output = test.scratch / SERVER_OUTPUT
        with terminated_like_interrupt(), server_output.open("wb") as output:
            process = _start(test.command, test.cwd, stdout=output, stderr=subprocess.STDOUT)
            try:
                self._follow(process, test, server_output)
            finally:
                _kill_group(process)
                kill_processes_started_from(test.scratch, EXIT_GRACE_SECONDS)

    def _follow(self, process: "subprocess.Popen[bytes]", test: DebuggedTest, output: Path) -> None:
        announced = False
        while process.poll() is None:
            if not announced and _has_content(test.ready_file):
                test.announce()
                announced = True
            time.sleep(POLL_SECONDS)
        if not announced and not _has_content(test.ready_file):
            lines = _read(output).splitlines()[-SERVER_TAIL_LINES:]
            raise RunnerStartError(
                f"the debug server ended before it listened (exit code {process.returncode})",
                lines,
            )


def _start(
    command: Sequence[str], cwd: Path, *, stdout: object, stderr: object
) -> "subprocess.Popen[bytes]":
    try:
        return subprocess.Popen(
            list(command),
            cwd=cwd,
            env=_test_environment(os.environ),
            stdin=subprocess.DEVNULL,
            stdout=stdout,  # type: ignore[arg-type]
            stderr=stderr,  # type: ignore[arg-type]
            start_new_session=True,
        )
    except OSError as error:
        raise RunnerStartError(f"cannot run {command[0]}: {error.strerror or error}") from error


def _test_environment(inherited: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in inherited.items()
        if name not in UNCLEAN_ENVIRONMENT and not name.startswith(UNCLEAN_PREFIX)
    }


def _exit_code(returncode: int) -> int:
    return SIGNAL_EXIT_BASE - returncode if returncode < 0 else returncode


def _has_content(path: Path) -> bool:
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def _kill_group(process: "subprocess.Popen[bytes]") -> None:
    """Kills the process and anything it started, only while it runs, so its group is ours."""
    if process.poll() is not None:
        return
    with suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=EXIT_GRACE_SECONDS)
