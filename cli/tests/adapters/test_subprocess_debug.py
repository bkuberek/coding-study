"""`SubprocessRunner` with a debug agent (docs/specs/runners.md#debug-mode): the runner waits for
the IDE with every time limit off, says when it is ready, and never restarts."""

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from coding_study.adapters import subprocess_runner
from coding_study.adapters.debug_process import terminated_like_interrupt
from coding_study.adapters.subprocess_runner import SubprocessRunner, _Attempt
from coding_study.application.ports import DebugLaunch, RunnerLaunch
from coding_study.domain.cases import FunctionInput, JsonValue
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    FileTarget,
    NotRun,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    TimedOut,
)
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

FAKE_RUNNER = Path(__file__).resolve().parents[1] / "fixtures" / "fake_runner.py"
READY = "fake agent listening"
REFUSED = "fake connect refused"
HANG_GUARD_MS = 200
IDLE_LIMIT_MS = 300
HELLO_TIMEOUT_MS = 100
SIGNATURE = FunctionSignature(
    "step", (Param("step", ScalarType(Scalar.STRING)),), Returns(ScalarType(Scalar.INT))
)
PYTHON_SESSION = DebugSession(Language.PYTHON, 5678)
JAVA_CONNECT = DebugSession(Language.JAVA, 5005, connect=True)


def case(case_id: str, do: str, **step: JsonValue) -> RunCase:
    return RunCase(case_id, FunctionInput({"step": {"do": do, **step}}), HANG_GUARD_MS)


def job(*cases: RunCase) -> RunJob:
    names = FunctionNames("step", {"step": "step"})
    return RunJob("j", ProblemKind.FUNCTION, FileTarget("/w/s.py"), names, SIGNATURE, cases)


class Debugging:
    """A runner that imitates a debug agent, and what it announced."""

    def __init__(
        self,
        tmp_path: Path,
        session: DebugSession = PYTHON_SESSION,
        stream: str = "stdout",
        ready_file: Path | None = None,
    ) -> None:
        self.session = session
        self.stream = stream
        self.ready_file = ready_file
        """Instead of a ready line, the agent writes its port here, as `debugserver` does."""
        self.release = tmp_path / "released"
        self.launches = tmp_path / "launches.log"
        self.leftover = tmp_path / "leftover.pid"
        self.scratch = tmp_path / "scratch"
        """The launch's private directory, where `debugserver`'s runner binary would be."""
        self.announced: list[str] = []
        self.on_announce: Callable[[], None] = self.release.touch
        """What the "user" does on seeing the ready line: by default, attach."""

    def launch(self, startup: str, hello_timeout_ms: int = HELLO_TIMEOUT_MS) -> RunnerLaunch:
        ready = "" if self.ready_file else READY
        runner_binary = self._private_runner_binary()
        command = (
            sys.executable,
            str(FAKE_RUNNER),
            "--startup",
            startup,
            "--ready-line",
            ready,
            "--ready-stream",
            self.stream,
            "--refused-line",
            REFUSED,
            "--release",
            str(self.release),
            "--launch-log",
            str(self.launches),
            "--leftover-pid",
            str(self.leftover),
            "--leftover-binary",
            str(runner_binary),
            *(("--ready-file", str(self.ready_file)) if self.ready_file else ()),
        )
        debug = DebugLaunch(self.session, self._announce, ready, REFUSED, self.ready_file)
        return RunnerLaunch(command, FAKE_RUNNER.parent, hello_timeout_ms, debug, self.scratch)

    def _private_runner_binary(self) -> Path:
        """An executable in the scratch directory, which `rmtree` removes with the run."""
        self.scratch.mkdir(exist_ok=True)
        binary = self.scratch / "cs-runner"
        if not binary.exists():
            binary.symlink_to(sys.executable)
        return binary

    def launch_count(self) -> int:
        return len(self.launches.read_text().splitlines()) if self.launches.exists() else 0

    def _announce(self, line: str) -> None:
        self.announced.append(line)
        self.on_announce()


@pytest.fixture
def runs_directory(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def runner(runs_directory: Path) -> SubprocessRunner:
    return SubprocessRunner(runs_directory, idle_limit_ms=IDLE_LIMIT_MS, connect_patience_seconds=3)


@pytest.fixture
def debugging(tmp_path: Path) -> Debugging:
    return Debugging(tmp_path)


def outcomes(report: RunReport) -> list[CaseOutcome]:
    return [case_report.outcome for case_report in report.job("j").cases]


def run(runner: SubprocessRunner, launch: RunnerLaunch, *cases: RunCase) -> list[CaseOutcome]:
    return outcomes(runner.run(launch, RunRequest((job(*cases),))))


def test_the_ready_line_is_announced_when_the_agent_says_it_listens(runner, debugging):
    seen_before_release: list[bool] = []
    debugging.on_announce = lambda: (
        seen_before_release.append(debugging.release.exists()),
        debugging.release.touch(),
    )
    run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert (debugging.announced, seen_before_release) == ([PYTHON_SESSION.ready_line], [False])


def test_the_marker_is_also_found_on_standard_error(tmp_path, runner):
    debugging = Debugging(tmp_path, stream="stderr")
    run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert debugging.announced == [PYTHON_SESSION.ready_line]


def test_the_run_finishes_after_the_ide_attached(runner, debugging):
    assert run(runner, debugging.launch("debug-wait"), case("a", "return", value=1)) == [
        Returned(1, 1000)
    ]


def test_waiting_for_the_ide_outlasts_the_hello_timeout(runner, debugging):
    def attach_after_the_hello_timeout() -> None:
        time.sleep(HELLO_TIMEOUT_MS * 4 / 1000)
        debugging.release.touch()

    debugging.on_announce = attach_after_the_hello_timeout
    assert run(runner, debugging.launch("debug-wait"), case("a", "return", value=1)) == [
        Returned(1, 1000)
    ]


def test_the_same_wait_is_an_environment_error_without_debugging(runner, tmp_path):
    silent = RunnerLaunch(
        (sys.executable, str(FAKE_RUNNER), "--startup", "silent"), FAKE_RUNNER.parent, 100
    )
    with pytest.raises(RunnerStartError, match="did not say hello within 100 ms"):
        runner.run(silent, RunRequest(()))


def test_a_case_may_outlast_its_hang_guard_while_debugging(runner, debugging):
    assert run(runner, debugging.launch("debug-wait"), case("a", "sleep", seconds=0.5)) == [
        Returned(0, 1000)
    ]


def test_the_same_case_times_out_without_debugging(runner):
    plain = RunnerLaunch((sys.executable, str(FAKE_RUNNER)), FAKE_RUNNER.parent, 5_000)
    assert run(runner, plain, case("a", "sleep", seconds=0.5))[0] == TimedOut(HANG_GUARD_MS)


def test_a_gap_between_cases_may_outlast_the_idle_limit_while_debugging(runner, debugging):
    assert run(runner, debugging.launch("debug-wait"), case("a", "stall", seconds=0.6)) == [
        Returned(0, 1000)
    ]


def test_a_crash_is_reported_and_the_runner_is_not_restarted(runner, debugging, runs_directory):
    outcome = run(
        runner,
        debugging.launch("debug-wait"),
        case("a", "crash", exit_code=3),
        case("b", "return", value=2),
    )
    assert (outcome, debugging.launch_count()) == (
        [
            Crashed(3, ("crashed",)),
            NotRun("the runner ended during the debug session; it is not restarted"),
        ],
        1,
    )


def test_one_request_file_is_written_for_a_crashed_debug_run(runner, debugging, runs_directory):
    run(runner, debugging.launch("debug-wait"), case("a", "crash", exit_code=3), case("b", "hang"))
    assert len(list(runs_directory.glob("*/request-*.json"))) == 1


def test_the_runners_standard_output_is_kept_for_the_ready_marker(
    runner, debugging, runs_directory
):
    run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    [kept] = runs_directory.glob("*/stdout-0.txt")
    assert READY in kept.read_text()


def test_a_normal_run_keeps_no_standard_output(runner, runs_directory):
    plain = RunnerLaunch((sys.executable, str(FAKE_RUNNER)), FAKE_RUNNER.parent, 5_000)
    run(runner, plain, case("a", "return", value=1))
    assert list(runs_directory.glob("*/stdout-*.txt")) == []


def test_a_runner_that_exits_before_its_agent_listens_is_a_start_error(runner, debugging):
    with pytest.raises(RunnerStartError) as raised:
        run(runner, debugging.launch("debug-exit"), case("a", "return", value=1))
    assert raised.value.stderr_tail == ("address already in use",)


def test_that_start_error_says_the_debug_session_ended(runner, debugging):
    with pytest.raises(RunnerStartError, match="the debug session ended before the run started"):
        run(runner, debugging.launch("debug-exit"), case("a", "return", value=1))


def test_a_run_that_finishes_without_an_agent_is_a_start_error(runner, debugging):
    with pytest.raises(RunnerStartError, match="finished without a debug agent listening"):
        run(runner, debugging.launch("normal"), case("a", "return", value=1))


def test_nothing_is_announced_for_a_run_that_never_listened(runner, debugging):
    with pytest.raises(RunnerStartError):
        run(runner, debugging.launch("normal"), case("a", "return", value=1))
    assert debugging.announced == []


def test_an_agent_that_writes_its_ready_file_is_announced(runner, tmp_path):
    debugging = Debugging(tmp_path, ready_file=tmp_path / "debug-port")
    outcome = run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert (outcome, debugging.announced) == ([Returned(1, 1000)], [PYTHON_SESSION.ready_line])


def test_the_ready_file_is_empty_when_the_agent_starts(runner, tmp_path):
    """`debugserver` writes only to a file that exists, and a stale port would announce early."""
    ready_file = tmp_path / "debug-port"
    ready_file.write_bytes(b"5555\0")
    debugging = Debugging(tmp_path, ready_file=ready_file)
    outcome = run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert outcome == [Returned(1, 1000)]


def ended(pid: int) -> bool:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.02)
    return False


def test_a_runner_left_behind_by_an_agent_that_exited_is_killed(runner, debugging):
    """lldb's `detach` ends `debugserver` and leaves the runner going, in a process group of its
    own and followed by nobody."""
    with pytest.raises(RunnerStartError):
        run(runner, debugging.launch("debug-detach"), case("a", "return", value=1))
    leftover = int(debugging.leftover.read_text())
    survived = not ended(leftover)
    if survived:
        os.kill(leftover, signal.SIGKILL)
    assert not survived


def test_a_runner_left_behind_is_killed_even_when_the_group_kill_fails(
    monkeypatch, runner, debugging
):
    group_kill = subprocess_runner._kill_group

    def kill_then_report_a_live_runner(process: subprocess.Popen[bytes]) -> None:
        group_kill(process)
        raise PermissionError

    monkeypatch.setattr(subprocess_runner, "_kill_group", kill_then_report_a_live_runner)
    with pytest.raises(PermissionError):
        run(runner, debugging.launch("debug-detach"), case("a", "return", value=1))
    leftover = int(debugging.leftover.read_text())
    survived = not ended(leftover)
    if survived:
        os.kill(leftover, signal.SIGKILL)
    assert not survived


def test_a_group_is_never_signalled_once_its_leader_was_reaped(monkeypatch, runner, debugging):
    """The id of a reaped leader may name an unrelated group by then."""
    signalled: list[int] = []
    monkeypatch.setattr(subprocess_runner.os, "killpg", lambda group, _: signalled.append(group))
    run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert signalled == []


def test_a_ready_marker_that_lands_with_bye_after_the_last_check_is_no_failure(
    monkeypatch, runner, debugging
):
    """The marker is printed after the poll's check for it and `bye` arrives in the same poll."""
    monkeypatch.setattr(_Attempt, "_announce_when_listening", lambda _attempt: None)
    debugging.release.touch()
    outcome = run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert outcome == [Returned(1, 1000)]


# Connecting to an IDE that listens (JVM): the runner exits at once when nobody listens yet.


@pytest.fixture
def connecting(tmp_path: Path) -> Debugging:
    return Debugging(tmp_path, JAVA_CONNECT)


def test_connecting_is_announced_as_the_runner_starts(runner, connecting):
    connecting.release.touch()
    run(runner, connecting.launch("debug-refuse"), case("a", "return", value=1))
    assert connecting.announced == [JAVA_CONNECT.ready_line]


def test_a_listening_ide_gets_the_run_at_the_first_launch(runner, connecting):
    connecting.release.touch()
    assert run(runner, connecting.launch("debug-refuse"), case("a", "return", value=1)) == [
        Returned(1, 1000)
    ]
    assert connecting.launch_count() == 1


def test_the_runner_launches_again_until_an_ide_listens(runner, connecting):
    connecting.on_announce = lambda: threading.Timer(0.4, connecting.release.touch).start()
    assert run(runner, connecting.launch("debug-refuse"), case("a", "return", value=1)) == [
        Returned(1, 1000)
    ]
    assert connecting.launch_count() > 1


def test_relaunching_announces_only_once(runner, connecting):
    connecting.on_announce = lambda: threading.Timer(0.4, connecting.release.touch).start()
    run(runner, connecting.launch("debug-refuse"), case("a", "return", value=1))
    assert connecting.announced == [JAVA_CONNECT.ready_line]


def test_no_ide_listening_in_time_is_an_environment_error(runs_directory, connecting):
    patient = SubprocessRunner(runs_directory, connect_patience_seconds=0.5)
    connecting.on_announce = lambda: None
    with pytest.raises(RunnerStartError) as raised:
        run(patient, connecting.launch("debug-refuse"), case("a", "return", value=1))
    assert str(raised.value) == (
        "no debugger listening on 127.0.0.1:5005; "
        "start the IDE's 'Debug JVM (listen)' configuration first"
    )


def test_giving_up_takes_about_the_patience(runs_directory, connecting):
    patient = SubprocessRunner(runs_directory, connect_patience_seconds=0.5)
    connecting.on_announce = lambda: None
    started = time.monotonic()
    with pytest.raises(RunnerStartError):
        run(patient, connecting.launch("debug-refuse"), case("a", "return", value=1))
    assert 0.4 < time.monotonic() - started < 3


def test_a_connecting_runner_that_dies_for_another_reason_is_not_launched_again(runner, connecting):
    with pytest.raises(RunnerStartError, match="the debug session ended"):
        run(runner, connecting.launch("debug-exit"), case("a", "return", value=1))
    assert connecting.launch_count() == 1


# Stopping: Ctrl-C and the signals an IDE sends when its task is stopped.


def test_ctrl_c_while_waiting_kills_the_runner(monkeypatch, runner, debugging):
    started: list[subprocess.Popen] = []
    popen = subprocess.Popen

    def recording_popen(*arguments, **keywords):
        started.append(popen(*arguments, **keywords))
        return started[-1]

    def interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess_runner.subprocess, "Popen", recording_popen)
    debugging.on_announce = interrupt
    with pytest.raises(KeyboardInterrupt):
        run(runner, debugging.launch("debug-wait"), case("a", "return", value=1))
    assert started[0].poll() is not None


@pytest.mark.parametrize("signal_number", [signal.SIGTERM, signal.SIGHUP])
def test_stop_signals_unwind_like_ctrl_c(signal_number):
    with pytest.raises(SystemExit) as raised, terminated_like_interrupt():
        os.kill(os.getpid(), signal_number)
    assert raised.value.code == 128 + signal_number


@pytest.mark.parametrize("signal_number", [signal.SIGTERM, signal.SIGHUP])
def test_the_previous_signal_handlers_come_back(signal_number):
    before = signal.getsignal(signal_number)
    with terminated_like_interrupt():
        pass
    assert signal.getsignal(signal_number) is before
