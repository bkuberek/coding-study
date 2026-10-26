"""Stress runs through the wire format and `SubprocessRunner` (runners.md#concurrent-jobs)."""

import sys
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.runner_protocol import (
    CaseResult,
    RestartRequested,
    decode_event,
    encode_request,
)
from coding_study.adapters.subprocess_runner import MAX_RESTARTS, SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.cases import OperationSequence
from coding_study.domain.concurrency import ConcurrencyModel, Perturbation, ThreadKind
from coding_study.domain.errors import RunnerProtocolError, RunnerStartError
from coding_study.domain.naming import ClassNames
from coding_study.domain.problem import ProblemKind
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    FileTarget,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    SectionCounters,
    Stalled,
    StressCompleted,
    StressFailure,
    StressPhase,
    StressRun,
    UserError,
    WorkerProgress,
)
from coding_study.domain.signature import ClassSignature, Method, Returns
from coding_study.domain.type_dsl import Scalar, ScalarType, VoidType

FAKE = Path(__file__).resolve().parents[1] / "fixtures" / "fake_stress_runner.py"
SIGNATURE = ClassSignature(
    "Fake",
    (),
    (Method("put", (), Returns(VoidType())), Method("size", (), Returns(ScalarType(Scalar.INT)))),
)
NAMES = ClassNames("Fake", {"put": "put", "size": "size"})
WORKERS = (OperationSequence(("put", "put"), ((), ())), OperationSequence(("size",), ((),)))


def stress(case_id: str, action: str) -> RunCase:
    run = StressRun(
        seed=1000,
        deadline_ms=200,
        perturb=Perturbation(),
        setup=OperationSequence(("Fake",), ((action,),)),
        workers=WORKERS,
        final=OperationSequence(("size",), ((),)),
        thread_kind=ThreadKind.PLATFORM,
    )
    return RunCase(case_id, run, 5_000)


def sequential(case_id: str) -> RunCase:
    return RunCase(case_id, OperationSequence(("Fake", "size"), ((), ())), 5_000)


def job(*cases: RunCase) -> RunJob:
    return RunJob(
        "j",
        ProblemKind.CONCURRENT,
        FileTarget("/w/fake.py"),
        NAMES,
        SIGNATURE,
        cases,
        ConcurrencyModel.THREADS,
    )


def run(tmp_path: Path, *cases: RunCase, startup: str = "normal") -> RunReport:
    launch = RunnerLaunch((sys.executable, str(FAKE), "--startup", startup), FAKE.parent, 5_000)
    return SubprocessRunner(tmp_path / "runs").run(launch, RunRequest((job(*cases),)))


def outcomes(report: RunReport) -> list[CaseOutcome]:
    return [case.outcome for case in report.job("j").cases]


def test_a_concurrent_job_sends_its_model():
    encoded: Any = encode_request(RunRequest((job(sequential("ex1")),)))
    assert encoded["jobs"][0]["model"] == "threads"


def test_a_stress_run_is_sent_fully_expanded():
    encoded: Any = encode_request(RunRequest((job(stress("s1:platform:0", "ok")),)))
    case = encoded["jobs"][0]["cases"][0]
    assert case == {
        "id": "s1:platform:0",
        "stress": {
            "seed": 1000,
            "deadline_ms": 200,
            "perturb": {"yield_probability": 0.05, "max_yields": 3, "python_granularity": "line"},
            "setup": {"ops": ["Fake"], "args": [["ok"]]},
            "workers": [{"ops": ["put", "put"], "args": [[], []]}, {"ops": ["size"], "args": [[]]}],
            "thread_kind": "platform",
            "final": {"ops": ["size"], "args": [[]]},
        },
    }


def test_blocking_methods_are_marked_in_the_signature():
    blocking = ClassSignature("Fake", (), (Method("take", (), Returns(VoidType()), blocking=True),))
    encoded: Any = encode_request(
        RunRequest((RunJob("j", ProblemKind.CONCURRENT, FileTarget("/f"), NAMES, blocking, ()),))
    )
    method = encoded["jobs"][0]["signature"]["class"]["methods"][0]
    assert method["blocking"] is True


def test_hello_features_are_read():
    event = decode_event(
        '{"event": "hello", "runner": "jvm", "protocol": 1, "runtime": "21",'
        ' "features": ["stress"]}'
    )
    assert event.features == ("stress",)  # type: ignore[union-attr]


def test_a_stalled_result_lists_the_waiting_workers():
    event = decode_event(
        '{"event": "case_result", "job_id": "j", "case_id": "s", "status": "stalled",'
        ' "progress": [{"worker": 3, "completed": 12, "in_op": true}], "duration_ns": 5}'
    )
    assert event == CaseResult("j", "s", Stalled((WorkerProgress(3, 12, True),), 5))


def test_a_stress_result_carries_its_sections():
    event = decode_event(
        '{"event": "case_result", "job_id": "j", "case_id": "s", "status": "ok",'
        ' "output": {"setup": [null], "workers": [[1], []], "final": [0]},'
        ' "sections": {"data": {"entries": 4, "violations": 1, "max_occupancy": 2}},'
        ' "duration_ns": 5}'
    )
    assert event == CaseResult(
        "j",
        "s",
        StressCompleted((None,), ((1,), ()), (0,), {"data": SectionCounters(4, 1, 2)}, 5),
    )


def test_restart_requested_is_an_event():
    assert decode_event('{"event": "restart_requested", "reason": "x"}') == RestartRequested("x")


def test_an_unknown_phase_is_a_protocol_error():
    with pytest.raises(RunnerProtocolError):
        decode_event(
            '{"event": "case_result", "job_id": "j", "case_id": "s", "status": "error",'
            ' "phase": "teardown", "op_index": 0, "error": {"type": "E", "message": ""},'
            ' "duration_ns": 5}'
        )


def test_a_completed_stress_run_is_reported(tmp_path):
    [outcome] = outcomes(run(tmp_path, stress("s1:platform:0", "ok")))
    assert outcome == StressCompleted((None,), ((None, None), (None,)), (None,), {}, 9)


def test_a_worker_failure_names_its_phase_worker_and_op(tmp_path):
    [outcome] = outcomes(run(tmp_path, stress("s1:platform:0", "error")))
    assert outcome == Raised(
        UserError("IndexError", "empty"),
        500,
        op_index=0,
        stress=StressFailure(StressPhase.WORKER, 0, 1, (WorkerProgress(0, 1, True),)),
    )


def test_a_stall_is_reported(tmp_path):
    [outcome] = outcomes(run(tmp_path, stress("s1:platform:0", "stall")))
    assert outcome == Stalled((WorkerProgress(0, 0, True),), 7)


def test_sequential_and_stress_cases_share_a_job(tmp_path):
    report = run(tmp_path, sequential("ex1"), stress("s1:platform:0", "ok"))
    assert isinstance(outcomes(report)[0], Returned)


def test_a_restart_request_runs_the_remaining_cases(tmp_path):
    report = run(tmp_path, stress("s1:platform:0", "restart"), stress("s1:platform:1", "ok"))
    assert isinstance(outcomes(report)[1], StressCompleted)


def test_restart_requests_are_recorded_per_job(tmp_path):
    report = run(tmp_path, stress("s1:platform:0", "restart"), stress("s1:platform:1", "ok"))
    assert report.job("j").restarted_after == ("s1:platform:0",)


def test_requested_restarts_do_not_use_up_the_crash_budget(tmp_path):
    cases = [stress(f"s1:platform:{run}", "restart") for run in range(MAX_RESTARTS + 2)]
    report = run(tmp_path, *cases, sequential("after"))
    assert outcomes(report)[-1] == Returned(2, 1000)


def test_exit_code_3_without_a_request_is_a_crash(tmp_path):
    report = run(tmp_path, stress("s1:platform:0", "exit-3"), stress("s1:platform:1", "ok"))
    assert isinstance(outcomes(report)[1], Crashed)


def test_outputs_that_do_not_match_the_scripts_are_a_protocol_error(tmp_path):
    with pytest.raises(RunnerProtocolError, match="outputs do not match"):
        run(tmp_path, stress("s1:platform:0", "mismatch"))


def test_a_runner_without_the_stress_feature_cannot_run_concurrent_jobs(tmp_path):
    with pytest.raises(RunnerStartError, match="runner fake does not support concurrent problems"):
        run(tmp_path, sequential("ex1"), startup="no-stress")
