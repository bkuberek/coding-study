"""SubprocessRunner running a project's native suite (docs/specs/runners.md#suite-job)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.subprocess_runner import MAX_RESTARTS, SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.errors import RunnerProtocolError, RunnerStartError
from coding_study.domain.runs import Crashed, Raised, TimedOut, UserError
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteFramework,
    SuiteJob,
    SuiteOutcome,
    SuiteReport,
)

FAKE_SUITE_RUNNER = Path(__file__).resolve().parents[1] / "fixtures" / "fake_suite_runner.py"
HANG_GUARD_MS = 200
IDLE_LIMIT_MS = 300


def launch(startup: str = "normal", environment: dict[str, str] | None = None) -> RunnerLaunch:
    command = (sys.executable, str(FAKE_SUITE_RUNNER), "--startup", startup)
    return RunnerLaunch(command, FAKE_SUITE_RUNNER.parent, 5_000, environment=environment or {})


def scripted(test_id: str, do: str, **fields: Any) -> dict[str, Any]:
    return {"id": test_id, "do": do, **fields}


@pytest.fixture
def runs_directory(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def runner(runs_directory: Path) -> SubprocessRunner:
    return SubprocessRunner(runs_directory, idle_limit_ms=IDLE_LIMIT_MS)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    directory = tmp_path / "project"
    directory.mkdir()
    return directory


def run_suite(
    runner: SubprocessRunner, root: Path, *tests: dict[str, Any], startup: str = "normal"
) -> SuiteReport:
    (root / "suite.json").write_text(json.dumps(list(tests)), encoding="utf-8")
    job = SuiteJob("bank/suite", SuiteFramework.PYTEST, str(root), HANG_GUARD_MS)
    return runner.run_suite(launch(startup), job)


def outcomes(report: SuiteReport) -> dict[str, SuiteOutcome]:
    return {result.test_id: result.outcome for result in report.tests}


def requests(runs_directory: Path) -> list[dict[str, Any]]:
    (run_directory,) = runs_directory.iterdir()
    files = sorted(run_directory.glob("request-*.json"))
    return [json.loads(path.read_text(encoding="utf-8"))["jobs"][0] for path in files]


def test_reports_each_test_with_its_outcome_in_order(runner, root):
    report = run_suite(
        runner,
        root,
        scripted("a", "pass"),
        scripted("b", "fail"),
        scripted("c", "raise"),
        scripted("d", "skip"),
    )
    assert outcomes(report) == {
        "a": Passed(1000),
        "b": AssertionFailed("assert 1 == 2", 1000),
        "c": Raised(UserError("KeyError", "'x'", "tests/test_a.py:3 in test"), 1000),
        "d": Skipped("later", 1000),
    }


def test_a_suite_that_ran_to_its_end_did_not_stop_early(runner, root):
    assert run_suite(runner, root, scripted("a", "pass")).stopped_early is None


def test_a_hang_times_out_its_test_and_the_suite_carries_on(runner, root):
    report = run_suite(
        runner, root, scripted("a", "pass"), scripted("b", "hang"), scripted("c", "pass")
    )
    assert outcomes(report) == {"a": Passed(1000), "b": TimedOut(HANG_GUARD_MS), "c": Passed(1000)}


def test_a_restart_skips_every_test_reported_and_the_one_that_hung(runner, root, runs_directory):
    run_suite(runner, root, scripted("a", "pass"), scripted("b", "hang"), scripted("c", "pass"))
    assert [request["skip"] for request in requests(runs_directory)] == [[], ["a", "b"]]


def test_a_crash_is_reported_on_its_test_with_stderr(runner, root):
    report = run_suite(runner, root, scripted("a", "crash"), scripted("b", "pass"))
    assert outcomes(report) == {"a": Crashed(9, ("crashed",)), "b": Passed(1000)}


def test_restarts_run_out_after_the_limit(runner, root):
    crashing = [scripted(f"t{index}", "crash") for index in range(MAX_RESTARTS + 1)]
    report = run_suite(runner, root, *crashing, scripted("last", "pass"))
    assert (len(report.tests), report.stopped_early) == (
        MAX_RESTARTS + 1,
        f"the runner was restarted {MAX_RESTARTS} times",
    )


def test_a_hang_between_tests_keeps_what_was_reported(runner, root):
    report = run_suite(runner, root, scripted("a", "pass"), scripted("b", "stall"))
    assert (outcomes(report), report.stopped_early is not None) == ({"a": Passed(1000)}, True)


def test_a_load_error_replaces_the_tests(runner, root):
    report = run_suite(runner, root, scripted("a", "pass"), startup="load-error")
    assert (report.load_error, report.tests) == (
        UserError("UsageError", "unrecognized arguments"),
        (),
    )


def test_reports_the_runner_from_hello(runner, root):
    assert run_suite(runner, root).runner.features == ("stress", "project", "suite")


def test_a_runner_without_suite_jobs_cannot_run_one(runner, root):
    with pytest.raises(RunnerStartError, match="does not support project problems"):
        run_suite(runner, root, scripted("a", "pass"), startup="no-suite")


def test_the_launch_environment_reaches_the_runner(runner, root):
    (root / "suite.json").write_text(
        json.dumps([scripted("a", "environment", variable="UV_NO_SYNC")]), encoding="utf-8"
    )
    job = SuiteJob("bank/suite", SuiteFramework.PYTEST, str(root), HANG_GUARD_MS)
    report = runner.run_suite(launch(environment={"UV_NO_SYNC": "1"}), job)
    assert report.tests[0].outcome == Passed(1000, "1")


def test_a_test_reported_twice_is_a_protocol_error(runner, root):
    with pytest.raises(RunnerProtocolError, match='"a"'):
        run_suite(runner, root, scripted("a", "pass"), scripted("a", "repeat"))


def test_a_test_with_an_output_is_a_protocol_error(runner, root):
    with pytest.raises(RunnerProtocolError, match="not a test result"):
        run_suite(runner, root, scripted("a", "output"))


def test_ending_the_job_during_a_test_is_a_protocol_error(runner, root):
    with pytest.raises(RunnerProtocolError, match="job_end"):
        run_suite(runner, root, scripted("a", "pass"), startup="early-end")
