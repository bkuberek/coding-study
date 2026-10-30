"""`cstudy verify` D6 and D7 on the concurrent fixture with scripted runs
(docs/specs/authoring.md)."""

import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.ports import RunnerLaunch
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.bench_records import MachineState, PowerSource
from coding_study.domain.problem import Language
from coding_study.domain.runs import (
    CaseOutcome,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    StressCompleted,
    StressRun,
)
from tests.concurrency_fakes import duplicating, queue
from tests.fakes import (
    QUIET_MACHINE,
    FakeLanguageRunner,
    FakeMachine,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)
from tests.helpers import CONCURRENCY_PROBLEMS

SLUG = "bounded-blocking-queue"
STRESS_RUN_SECONDS = 0.05
"""Long enough for runners started side by side to overlap."""
BUSY_MACHINE = MachineState("Test CPU", PowerSource.AC, 13.4, 11)
BUSY_NOTE = "load 13.4 is above half of 11 cores"


def caught(job: RunJob, case: RunCase) -> CaseOutcome:
    """The correct reference is correct; every broken one loses a value in every stress run."""
    return duplicating(job, case) if "/broken-" in job.job_id else queue(job, case)


def environment_with(tmp_path: Path, answer, machine: MachineState = QUIET_MACHINE):
    process = ScriptedRunnerProcess(answer)
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    root = repository_root(tmp_path, CONCURRENCY_PROBLEMS)
    environment = make_environment(
        root, toolchains=toolchains, runner_process=process, machine=FakeMachine(machine)
    )
    return environment, process


def verify(environment, **fields):
    request = VerifyRequest(slugs=(SLUG,), language=Language.PYTHON, **fields)
    return verify_content(environment, request, lambda _line: None).problems[0]


def python(problem):
    return problem.languages[0]


def test_a_caught_broken_reference_passes_d7(tmp_path):
    environment, _ = environment_with(tmp_path, caught)
    assert verify(environment).passed


def test_every_stress_case_runs_ten_times_per_variant(tmp_path):
    environment, _ = environment_with(tmp_path, caught)
    checks = python(verify(environment)).stress
    assert {len(check.verdict.runs) for check in checks} == {10}


def test_broken_references_run_only_their_caught_by_cases(tmp_path):
    environment, _ = environment_with(tmp_path, caught)
    checks = python(verify(environment)).stress
    broken = {(check.target_id, check.verdict.case_id) for check in checks if check.is_broken}
    assert broken == {("no-lock", "s1"), ("if-not-while", "s2")}


def test_stress_flag_changes_the_runs(tmp_path):
    environment, _ = environment_with(tmp_path, caught)
    checks = python(verify(environment, stress_runs=3)).stress
    assert {len(check.verdict.runs) for check in checks} == {3}


def test_a_broken_reference_that_is_never_caught_fails_d7(tmp_path):
    environment, _ = environment_with(tmp_path, queue)
    broken = python(verify(environment)).broken
    assert broken[0].failures == ("s1 thread caught in 0/10 runs (needs 9)",)


def test_d7_needs_ninety_percent_of_runs(tmp_path):
    def caught_once(job: RunJob, case: RunCase) -> CaseOutcome:
        is_first_run = case.id.endswith(":0")
        return caught(job, case) if is_first_run else queue(job, case)

    environment, _ = environment_with(tmp_path, caught_once)
    assert not verify(environment).passed


def test_a_broken_reference_must_pass_the_sequential_cases(tmp_path):
    def wrong_sequence(job: RunJob, case: RunCase) -> CaseOutcome:
        outcome = caught(job, case)
        if "/broken-no-lock" in job.job_id and case.id == "ex1":
            return Returned([None, None, None, 9, 5, 7, 0], 1000)
        return outcome

    environment, _ = environment_with(tmp_path, wrong_sequence)
    failures = python(verify(environment)).broken[0].failures
    assert failures[0].startswith("sequential ex1 FAIL")


def test_a_correct_reference_must_pass_every_run(tmp_path):
    def flaky(job: RunJob, case: RunCase) -> CaseOutcome:
        if job.job_id.endswith("/monitor") and case.id == "s2:thread:4":
            return duplicating(job, case)
        return caught(job, case)

    environment, _ = environment_with(tmp_path, flaky)
    failures = python(verify(environment)).approaches[0].failures
    assert failures[0].startswith("s2 thread 9/10 runs passed; run 4 seed 2004: ")


def test_ready_needs_the_slowest_correct_run_within_a_quarter_of_the_deadline(tmp_path):
    def slow(job: RunJob, case: RunCase) -> CaseOutcome:
        outcome = caught(job, case)
        if isinstance(outcome, StressCompleted) and job.job_id.endswith("/monitor"):
            return replace(outcome, duration_ns=2_000_000_000)
        return outcome

    environment, _ = environment_with(tmp_path, slow)
    problem = verify(environment, require_ready=True)
    assert any("uses 40% of its deadline" in error for error in problem.ready_errors)


def test_stress_runs_get_the_stress_hang_guard(tmp_path):
    environment, process = environment_with(tmp_path, caught)
    verify(environment, stress_runs=1)
    cases = [case for request in process.requests for job in request.jobs for case in job.cases]
    stress = [case for case in cases if isinstance(case.input, StressRun)]
    assert {case.hang_guard_ms for case in stress} == {10_000}


class OverlapRecordingProcess(ScriptedRunnerProcess):
    """Each run with stress cases lasts a moment; records how many of them ran at once."""

    def __init__(self, answer) -> None:
        super().__init__(answer)
        self._lock = threading.Lock()
        self._running = 0
        self.most_at_once = 0

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        if not any(isinstance(case.input, StressRun) for job in request.jobs for case in job.cases):
            return super().run(launch, request)
        with self._lock:
            self._running += 1
            self.most_at_once = max(self.most_at_once, self._running)
        time.sleep(STRESS_RUN_SECONDS)
        with self._lock:
            self._running -= 1
        return super().run(launch, request)


def test_the_languages_stress_runs_take_turns(tmp_path):
    process = OverlapRecordingProcess(caught)
    languages = (Language.JAVA, Language.KOTLIN, Language.PYTHON, Language.TYPESCRIPT)
    toolchains = FakeToolchains(
        {language: FakeLanguageRunner() for language in languages},
        {language: FakeStubGenerator() for language in languages},
    )
    root = repository_root(tmp_path, CONCURRENCY_PROBLEMS)
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    request = VerifyRequest(slugs=(SLUG,), stress_runs=1)
    verify_content(environment, request, lambda _line: None)
    assert process.most_at_once == 1


def test_a_stress_failure_on_a_busy_machine_names_the_load(tmp_path):
    environment, _ = environment_with(tmp_path, queue, BUSY_MACHINE)
    warnings = verify(environment).warnings
    assert any(BUSY_NOTE in warning for warning in warnings)


def test_a_deadline_margin_failure_on_a_busy_machine_names_the_load(tmp_path):
    def slow(job: RunJob, case: RunCase) -> CaseOutcome:
        outcome = caught(job, case)
        if isinstance(outcome, StressCompleted) and job.job_id.endswith("/monitor"):
            return replace(outcome, duration_ns=2_000_000_000)
        return outcome

    environment, _ = environment_with(tmp_path, slow, BUSY_MACHINE)
    warnings = verify(environment, require_ready=True).warnings
    assert any(BUSY_NOTE in warning for warning in warnings)


def test_a_stress_failure_on_a_quiet_machine_has_no_load_note(tmp_path):
    environment, _ = environment_with(tmp_path, queue)
    assert not any("load" in warning for warning in verify(environment).warnings)


def test_stress_that_passes_on_a_busy_machine_has_no_load_note(tmp_path):
    environment, _ = environment_with(tmp_path, caught, BUSY_MACHINE)
    assert not any("load" in warning for warning in verify(environment).warnings)


@pytest.mark.parametrize("field", ["approaches", "broken"])
def test_results_are_reported_per_reference(tmp_path, field):
    environment, _ = environment_with(tmp_path, caught)
    results = getattr(python(verify(environment)), field)
    assert all(result.passed for result in results)
