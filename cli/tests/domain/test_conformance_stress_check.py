"""Stress expectations of the conformance suite (runners/conformance/expectations.json)."""

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, OperationSequence
from coding_study.domain.concurrency import StressVariant
from coding_study.domain.conformance import ExpectedOutcome, ExpectedStatus
from coding_study.domain.conformance_check import stress_mismatch
from coding_study.domain.runs import (
    Raised,
    SectionCounters,
    Stalled,
    StressFailure,
    StressPhase,
    UserError,
    WorkerProgress,
)
from coding_study.domain.stress import StressScenario
from coding_study.domain.stress_record import StressRecord
from coding_study.domain.stress_verdict import StressRunResult, StressVerdict

CASE = Case("s1", StressScenario(OperationSequence(("C",), ((),)), ()))
PASSED = StressRunResult(0, 1, CaseStatus.PASS)
FAILED = StressRunResult(0, 1, CaseStatus.FAIL, ("distinct increment: 5 (2 times)",))


def verdict(*runs: StressRunResult) -> StressVerdict:
    numbered = tuple(
        StressRunResult(
            index,
            1000 + index,
            run.status,
            run.reasons,
            run.duration_ns,
            run.record,
            outcome=run.outcome,
        )
        for index, run in enumerate(runs)
    )
    return StressVerdict(CASE, StressVariant.PLATFORM, numbered, 5000)


def mismatch(expected: ExpectedOutcome, checked: StressVerdict, restarted=()) -> str | None:
    return stress_mismatch(expected, checked, restarted)


def test_pass_needs_every_run_to_pass():
    found = mismatch(ExpectedOutcome(ExpectedStatus.PASS), verdict(PASSED, FAILED))
    assert found == (
        "s1 platform: 1/2 runs failed (at most 0); run 1 seed 1001: distinct increment: 5 (2 times)"
    )


def test_fail_counts_the_failing_runs():
    expected = ExpectedOutcome(ExpectedStatus.FAIL, min_failed=2)
    assert mismatch(expected, verdict(FAILED, FAILED, PASSED)) is None


def test_too_few_failing_runs_are_reported():
    expected = ExpectedOutcome(ExpectedStatus.FAIL, min_failed=2)
    found = mismatch(expected, verdict(FAILED, PASSED, PASSED))
    assert found == "s1 platform: expected fail in at least 2/3 runs, got 1 FAIL, 2 PASS"


def test_without_min_failed_every_run_must_fail():
    assert mismatch(ExpectedOutcome(ExpectedStatus.FAIL), verdict(FAILED, PASSED)) is not None


def test_an_error_names_its_phase_and_op():
    raised = Raised(
        UserError("IllegalStateException", "failed at 100"),
        1,
        op_index=100,
        stress=StressFailure(StressPhase.WORKER, 100, 0),
    )
    run = StressRunResult(0, 1, CaseStatus.ERROR, outcome=raised)
    expected = ExpectedOutcome(
        ExpectedStatus.ERROR, message="failed at 100", op_index=100, phase="worker"
    )
    assert mismatch(expected, verdict(run)) is None


def test_a_wrong_phase_is_reported():
    raised = Raised(UserError("E", "m"), 1, op_index=0, stress=StressFailure(StressPhase.SETUP, 0))
    run = StressRunResult(0, 1, CaseStatus.ERROR, outcome=raised)
    found = mismatch(ExpectedOutcome(ExpectedStatus.ERROR, phase="worker"), verdict(run))
    assert found == "s1 platform: run 0: expected phase worker, got setup"


def test_a_stall_must_name_waiting_workers():
    run = StressRunResult(0, 1, CaseStatus.STALLED, outcome=Stalled((), 1))
    found = mismatch(ExpectedOutcome(ExpectedStatus.STALLED), verdict(run))
    assert found == "s1 platform: run 0: a stall must name the workers waiting inside an op"


def test_a_stall_with_waiting_workers_matches():
    stalled = Stalled((WorkerProgress(0, 0, True),), 1)
    run = StressRunResult(0, 1, CaseStatus.STALLED, outcome=stalled)
    assert mismatch(ExpectedOutcome(ExpectedStatus.STALLED), verdict(run)) is None


def test_a_restart_is_matched_by_run_id():
    expected = ExpectedOutcome(ExpectedStatus.PASS, restart_requested=True)
    assert mismatch(expected, verdict(PASSED), ("s1:platform:0",)) is None


def test_a_missing_restart_is_reported():
    expected = ExpectedOutcome(ExpectedStatus.PASS, restart_requested=True)
    found = mismatch(expected, verdict(PASSED))
    assert found == "s1 platform: expected restart_requested after a run"


def record(value: int) -> StressRecord:
    return StressRecord(0, 1, "async", (), (), (), {"x": SectionCounters(value, 0, 1)})


def completed(value: int) -> StressRunResult:
    return StressRunResult(0, 1, CaseStatus.PASS, record=record(value))


def test_determinism_needs_the_repeated_seed_to_match():
    expected = ExpectedOutcome(ExpectedStatus.PASS, deterministic=True)
    found = mismatch(expected, verdict(completed(1), completed(2), completed(3)))
    assert found == "s1 platform: seed 1000 gave two different run records"


def test_determinism_needs_seeds_to_differ():
    expected = ExpectedOutcome(ExpectedStatus.PASS, deterministic=True)
    found = mismatch(expected, verdict(completed(1), completed(1), completed(1)))
    assert found == "s1 platform: 2 seeds gave 1 distinct run record"


def test_deterministic_runs_that_differ_by_seed_match():
    expected = ExpectedOutcome(ExpectedStatus.PASS, deterministic=True)
    assert mismatch(expected, verdict(completed(1), completed(2), completed(1))) is None
