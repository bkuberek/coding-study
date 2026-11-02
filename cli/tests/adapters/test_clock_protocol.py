"""The runner protocol of a project on the virtual clock (docs/specs/runners.md#virtual-clock-and-
stress-in-project-jobs): the request says so, a case can stall at an operation, and the runner
restarts after a case that left goroutines or threads behind."""

import sys
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.runner_protocol import CaseResult, decode_event, encode_request
from coding_study.adapters.subprocess_runner import MAX_RESTARTS, SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.cases import OperationSequence
from coding_study.domain.errors import RunnerProtocolError, RunnerStartError
from coding_study.domain.naming import ClassNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    CaseOutcome,
    CompiledTarget,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    Stalled,
    UserError,
)
from coding_study.domain.signature import ClassSignature, Method, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType
from coding_study.domain.virtual_clock import ProjectClock

FAKE = Path(__file__).resolve().parents[1] / "fixtures" / "fake_clock_runner.py"
RECEIVE = Method("receive", (), Returns(ScalarType(Scalar.STRING)))
SIGNATURE = ClassSignature("Log", (), (RECEIVE,))
NAMES = ClassNames("Log", {"receive": "Receive"}, "NewLog")
OPERATIONS = OperationSequence(
    ("Log", "@spawn", "@advance", "@join"), ((), ("r1", "receive"), (2000,), ("r1",))
)
DEADLOCK = Stalled(
    (),
    7,
    op_index=3,
    reason="op 3 (@join r1): deadlock at 2000 ms",
    partial_output=(None, None, None),
)


def case(case_id: str) -> RunCase:
    return RunCase(case_id, OPERATIONS, 5_000)


def job(*cases: RunCase, clock: ProjectClock | None = ProjectClock.VIRTUAL) -> RunJob:
    target = CompiledTarget("user")
    return RunJob("j", ProblemKind.PROJECT, target, NAMES, SIGNATURE, cases, clock=clock)


def run(tmp_path: Path, graded: RunJob, startup: str = "normal") -> RunReport:
    launch = RunnerLaunch((sys.executable, str(FAKE), "--startup", startup), FAKE.parent, 5_000)
    return SubprocessRunner(tmp_path / "runs").run(launch, RunRequest((graded,)))


def outcomes(report: RunReport) -> list[CaseOutcome]:
    return [case.outcome for case in report.job("j").cases]


def test_a_job_on_the_virtual_clock_says_so():
    encoded: Any = encode_request(RunRequest((job(case("ex1")),)))
    assert encoded["jobs"][0]["clock"] == "virtual"


def test_a_job_on_the_real_clock_names_no_clock():
    encoded: Any = encode_request(RunRequest((job(case("ex1"), clock=None),)))
    assert "clock" not in encoded["jobs"][0]


def test_async_methods_are_marked_in_the_signature():
    waiting = ClassSignature(
        "Log", (), (RECEIVE, Method("wait", (), RECEIVE.returns, is_async=True))
    )
    graded = RunJob("j", ProblemKind.PROJECT, CompiledTarget("user"), NAMES, waiting, ())
    encoded: Any = encode_request(RunRequest((graded,)))
    methods = encoded["jobs"][0]["signature"]["class"]["methods"]
    assert ["async" in method for method in methods] == [False, True]
    assert methods[1]["async"] is True


def test_a_deadlock_names_its_operation_its_reason_and_the_outputs_before_it():
    event = decode_event(
        '{"event": "case_result", "job_id": "j", "case_id": "c", "status": "stalled",'
        ' "op_index": 3, "reason": "op 3 (@join r1): deadlock at 2000 ms",'
        ' "partial_output": [null, null, null], "duration_ns": 7}'
    )
    assert event == CaseResult("j", "c", DEADLOCK)


def test_a_deadlock_is_reported_and_the_next_case_runs_in_a_fresh_runner(tmp_path):
    report = run(tmp_path, job(case("deadlock"), case("after")))
    assert (outcomes(report), report.job("j").restarted_after) == (
        [DEADLOCK, Returned([None, None, None, None], 9)],
        ("deadlock",),
    )


def test_a_stall_without_a_restart_lets_the_runner_go_on(tmp_path):
    report = run(tmp_path, job(case("stalled"), case("after")))
    assert (outcomes(report)[1], report.job("j").restarted_after) == (
        Returned([None, None, None, None], 9),
        (),
    )


def test_restarts_after_cases_on_the_clock_do_not_use_up_the_crash_budget(tmp_path):
    cases = [case(f"deadlock-{index}") for index in range(MAX_RESTARTS + 2)]
    report = run(tmp_path, job(*cases, case("after")))
    assert outcomes(report)[-1] == Returned([None, None, None, None], 9)


def test_a_case_that_failed_and_left_goroutines_restarts_the_runner(tmp_path):
    report = run(tmp_path, job(case("fails"), case("after")))
    assert outcomes(report)[0] == Raised(
        UserError("panic", "closed"), 7, op_index=3, partial_output=(None, None, None)
    )
    assert report.job("j").restarted_after == ("fails",)


def test_a_stall_on_the_real_clock_is_a_protocol_error(tmp_path):
    with pytest.raises(RunnerProtocolError, match="a stress run result for a case"):
        run(tmp_path, job(case("deadlock"), clock=None))


def test_a_restart_after_a_case_on_the_real_clock_is_a_protocol_error(tmp_path):
    with pytest.raises(RunnerProtocolError, match="restart_requested without a stress run"):
        run(tmp_path, job(case("restarts"), clock=None))


def test_a_runner_without_the_clock_feature_cannot_run_a_job_on_the_clock(tmp_path):
    with pytest.raises(
        RunnerStartError, match="runner fake does not support virtual-clock projects"
    ):
        run(tmp_path, job(case("ex1")), startup="no-clock")
