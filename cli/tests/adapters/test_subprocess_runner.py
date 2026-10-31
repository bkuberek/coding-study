import json
import os
import signal
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters import subprocess_runner
from coding_study.adapters.runner_protocol import encode_request
from coding_study.adapters.subprocess_runner import (
    KEPT_RUNS,
    MAX_RESTARTS,
    SubprocessRunner,
    _kill_group,
)
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.cases import FunctionInput, JsonValue
from coding_study.domain.errors import RunnerProtocolError, RunnerStartError
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    FileTarget,
    InvalidOutput,
    NotRun,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunnerInfo,
    RunReport,
    RunRequest,
    TimedOut,
    UserError,
)
from coding_study.domain.signature import FunctionSignature, Param, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType

FAKE_RUNNER = Path(__file__).resolve().parents[1] / "fixtures" / "fake_runner.py"
HANG_GUARD_MS = 200
IDLE_LIMIT_MS = 300
SLEEPING_COMMAND = (sys.executable, "-c", "import time; time.sleep(60)")
SIGNATURE = FunctionSignature(
    "step", (Param("step", ScalarType(Scalar.STRING)),), Returns(ScalarType(Scalar.INT))
)


def launch(startup: str = "normal", hello_timeout_ms: int = 5_000) -> RunnerLaunch:
    command = (sys.executable, str(FAKE_RUNNER), "--startup", startup)
    return RunnerLaunch(command, FAKE_RUNNER.parent, hello_timeout_ms)


def case(case_id: str, do: str, **step: JsonValue) -> RunCase:
    return RunCase(case_id, FunctionInput({"step": {"do": do, **step}}), HANG_GUARD_MS)


def returns(case_id: str, value: JsonValue) -> RunCase:
    return case(case_id, "return", value=value)


def job(*cases: RunCase, job_id: str = "j", path: str = "/w/solution.py") -> RunJob:
    names = FunctionNames("step", {"step": "step"})
    return RunJob(job_id, ProblemKind.FUNCTION, FileTarget(path), names, SIGNATURE, cases)


@pytest.fixture
def runs_directory(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def runner(runs_directory: Path) -> SubprocessRunner:
    return SubprocessRunner(runs_directory, idle_limit_ms=IDLE_LIMIT_MS)


def run(runner: SubprocessRunner, *jobs: RunJob, startup: str = "normal") -> RunReport:
    return runner.run(launch(startup), RunRequest(jobs))


def outcomes(report: RunReport, job_id: str = "j") -> list[CaseOutcome]:
    return [case_report.outcome for case_report in report.job(job_id).cases]


def test_returns_outputs_in_request_order(runner):
    report = run(runner, job(returns("a", 1), returns("b", [2, 3])))
    assert outcomes(report) == [Returned(1, 1000), Returned([2, 3], 1000)]


def test_reports_the_runner_from_hello(runner):
    assert run(runner, job(returns("a", 1))).runner == RunnerInfo("fake", 1, "0.1")


def test_empty_request_is_a_hello_handshake(runner):
    assert run(runner).runner == RunnerInfo("fake", 1, "0.1")


def test_user_exceptions_are_reported(runner):
    [outcome] = outcomes(run(runner, job(case("a", "raise", message="boom"))))
    assert outcome == Raised(UserError("ValueError", "boom"), 1000)


def test_invalid_output_is_reported(runner):
    assert outcomes(run(runner, job(case("a", "invalid")))) == [InvalidOutput("cyclic", 1000)]


def test_load_error_replaces_the_cases_of_its_job(runner):
    report = run(runner, job(returns("a", 1), path="/w/missing.py"))
    assert (report.job("j").load_error, report.job("j").cases) == (
        UserError("FileNotFoundError", "missing.py"),
        (),
    )


def test_jobs_report_separately(runner):
    report = run(runner, job(returns("a", 1), job_id="one"), job(returns("a", 2), job_id="two"))
    assert outcomes(report, "two") == [Returned(2, 1000)]


def test_hang_times_out_and_the_remaining_cases_still_run(runner):
    report = run(runner, job(returns("a", 1), case("b", "hang"), returns("c", 3)))
    assert outcomes(report) == [Returned(1, 1000), TimedOut(HANG_GUARD_MS), Returned(3, 1000)]


def test_stall_outside_a_case_times_out_the_next_case(runner):
    report = run(runner, job(case("a", "stall"), returns("b", 2)))
    assert outcomes(report) == [TimedOut(IDLE_LIMIT_MS), Returned(2, 1000)]


def test_crash_is_reported_on_its_case_with_stderr(runner):
    report = run(runner, job(case("a", "crash", exit_code=3), returns("b", 2)))
    assert outcomes(report) == [Crashed(3, ("crashed",)), Returned(2, 1000)]


def test_exit_without_bye_during_a_case_is_a_crash(runner):
    [outcome] = outcomes(run(runner, job(case("a", "crash", exit_code=0))))
    assert outcome == Crashed(0, ("crashed",))


def test_a_project_job_needs_a_runner_with_project_jobs(runner):
    project = replace(job(returns("a", 1)), kind=ProblemKind.PROJECT)
    with pytest.raises(RunnerStartError, match="does not support project problems"):
        run(runner, project)


def test_a_suite_result_in_a_test_job_is_a_protocol_error(runner):
    with pytest.raises(RunnerProtocolError, match="not a case result"):
        run(runner, job(case("a", "pass")))


def test_the_launch_environment_adds_to_the_cli_environment(runner, tmp_path):
    seen = tmp_path / "environment.json"
    script = tmp_path / "record_environment.py"
    script.write_text(
        "import json, os, pathlib, sys\n"
        f"pathlib.Path({str(seen)!r}).write_text(json.dumps(dict(os.environ)))\n"
        "sys.exit(1)\n"
    )
    environment = {"UV_NO_SYNC": "1"}
    launch = RunnerLaunch((sys.executable, str(script)), tmp_path, 5_000, environment=environment)
    with pytest.raises(RunnerStartError):
        runner.run(launch, RunRequest(()))
    recorded = json.loads(seen.read_text())
    assert (recorded["UV_NO_SYNC"], recorded["PATH"]) == ("1", os.environ["PATH"])


def test_cases_left_after_the_last_restart_are_not_run(runner):
    crashes = [case(f"c{index}", "crash", exit_code=1) for index in range(MAX_RESTARTS + 2)]
    assert [type(outcome) for outcome in outcomes(run(runner, job(*crashes)))] == [
        *([Crashed] * (MAX_RESTARTS + 1)),
        NotRun,
    ]


def test_runner_that_never_says_hello_is_an_environment_error(runner):
    with pytest.raises(RunnerStartError, match="did not say hello within 300 ms"):
        runner.run(launch("silent", hello_timeout_ms=300), RunRequest(()))


def test_runner_exiting_before_hello_reports_its_stderr(runner):
    with pytest.raises(RunnerStartError) as raised:
        run(runner, startup="exit-before-hello")
    assert raised.value.stderr_tail == ("cannot start",)


def test_missing_executable_is_an_environment_error(runner, tmp_path):
    missing = RunnerLaunch((str(tmp_path / "no-such-runner"),), tmp_path, 5_000)
    with pytest.raises(RunnerStartError, match="cannot start"):
        runner.run(missing, RunRequest(()))


def test_exit_code_2_outside_a_case_is_a_protocol_error(runner):
    with pytest.raises(RunnerProtocolError, match="rejected the request"):
        run(runner, job(returns("a", 1)), startup="bad-request")


def test_malformed_event_is_a_protocol_error(runner):
    with pytest.raises(RunnerProtocolError, match="not JSON"):
        run(runner, job(returns("a", 1)), startup="garbage")


def test_unsupported_protocol_version_is_a_protocol_error(runner):
    with pytest.raises(RunnerProtocolError, match="protocol 2"):
        run(runner, startup="protocol-2")


def test_events_for_unknown_jobs_are_protocol_errors(runner):
    with pytest.raises(RunnerProtocolError, match='unknown job "nope"'):
        run(runner, job(returns("a", 1)), startup="unknown-job")


def test_finishing_with_cases_not_run_is_a_protocol_error(runner):
    with pytest.raises(RunnerProtocolError, match="without running"):
        run(runner, job(returns("a", 1)), startup="skip-cases")


# A runner can exit between the liveness check in `_kill_group` and its signal. macOS then answers
# EPERM instead of ESRCH while the runner is exiting or an unreaped zombie.


def test_killing_a_runner_that_became_a_zombie_meanwhile_is_not_an_error(monkeypatch):
    process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT)
    poll = process.poll

    def poll_before_noticing_the_exit():
        monkeypatch.setattr(process, "poll", poll)

    monkeypatch.setattr(process, "poll", poll_before_noticing_the_exit)
    _kill_group(process)
    assert process.returncode == 0


def test_killing_a_runner_that_is_exiting_meanwhile_is_not_an_error(monkeypatch):
    process = subprocess.Popen(SLEEPING_COMMAND)

    def refuse_while_the_runner_exits(*_):
        process.terminate()
        raise PermissionError

    monkeypatch.setattr(subprocess_runner.os, "killpg", refuse_while_the_runner_exits)
    _kill_group(process)
    assert process.returncode is not None


def test_killing_a_runner_that_stays_alive_without_permission_is_an_error(monkeypatch):
    process = subprocess.Popen(SLEEPING_COMMAND)

    def refuse(*_):
        raise PermissionError

    monkeypatch.setattr(subprocess_runner.os, "killpg", refuse)
    monkeypatch.setattr(subprocess_runner, "EXIT_GRACE_SECONDS", 0.05)
    try:
        with pytest.raises(PermissionError):
            _kill_group(process)
    finally:
        process.send_signal(signal.SIGKILL)
        process.wait()


def test_writes_the_request_into_the_run_directory(runner, runs_directory):
    request = RunRequest((job(returns("a", 1)),))
    runner.run(launch(), request)
    [request_file] = runs_directory.glob("*/request-0.json")
    assert json.loads(request_file.read_text()) == encode_request(request)


def test_keeps_only_the_most_recent_runs(runner, runs_directory):
    for index in range(KEPT_RUNS + 5):
        (runs_directory / f"00000000-0000{index:02d}").mkdir(parents=True)
    run(runner)
    assert len(list(runs_directory.iterdir())) == KEPT_RUNS


# A launch's scratch directory (a private copy of the build output) goes when the run ends.


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    directory = tmp_path / "scratch"
    directory.mkdir()
    (directory / "Solution.class").write_text("bytecode")
    return directory


def test_removes_the_launch_scratch_directory_after_the_run(runner, scratch):
    runner.run(replace(launch(), scratch=scratch), RunRequest((job(returns("a", 1)),)))
    assert not scratch.exists()


def test_removes_the_launch_scratch_directory_after_crashes_ran_out(runner, scratch):
    crashes = [case(f"c{index}", "crash", exit_code=1) for index in range(MAX_RESTARTS + 1)]
    runner.run(replace(launch(), scratch=scratch), RunRequest((job(*crashes),)))
    assert not scratch.exists()


def test_removes_the_launch_scratch_directory_when_the_runner_does_not_start(runner, scratch):
    with pytest.raises(RunnerStartError):
        runner.run(replace(launch("exit-before-hello"), scratch=scratch), RunRequest(()))
    assert not scratch.exists()


def test_removes_the_launch_scratch_directory_when_interrupted(monkeypatch, runner, scratch):
    def interrupt(*_arguments: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess_runner._Attempt, "run", interrupt)
    with pytest.raises(KeyboardInterrupt):
        runner.run(replace(launch(), scratch=scratch), RunRequest(()))
    assert not scratch.exists()
