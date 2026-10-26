"""`cstudy test` on the concurrent fixture with a scripted runner (cli.md#concurrent-problems)."""

from pathlib import Path

import pytest

from coding_study.application.run_tests import RunTestsRequest, RunTestsResult, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.concurrency import ConcurrencyModel
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.stress_runs import StressSelection
from coding_study.domain.stress_verdict import StressVerdict
from tests.concurrency_fakes import duplicating, queue
from tests.fakes import (
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)
from tests.helpers import CONCURRENCY_PROBLEMS, FIXTURE_PROBLEMS


def environment_with(
    tmp_path: Path, process: ScriptedRunnerProcess, problems: Path = CONCURRENCY_PROBLEMS
):
    root = repository_root(tmp_path, problems)
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    return make_environment(root, toolchains=toolchains, runner_process=process)


@pytest.fixture
def process() -> ScriptedRunnerProcess:
    return ScriptedRunnerProcess(queue)


@pytest.fixture
def environment(tmp_path, process):
    environment = environment_with(tmp_path, process)
    start_attempt(environment, StartRequest("bounded-blocking-queue", Language.PYTHON))
    return environment


def run(environment, **fields):
    return run_tests(environment, RunTestsRequest(**fields), lambda _line: None)


def stress_of(result: RunTestsResult) -> tuple[StressVerdict, ...]:
    assert result.judgement is not None
    return result.judgement.stress


def test_a_correct_queue_passes_every_case(environment):
    assert run(environment).passed


def test_each_stress_case_and_variant_is_one_verdict(environment):
    stress = stress_of(run(environment))
    assert [(verdict.case_id, verdict.variant.value) for verdict in stress] == [
        ("s1", "thread"),
        ("s2", "thread"),
    ]


def test_stress_verdicts_count_as_cases(environment):
    assert run(environment).tally == Tally(total=8, passed=8)


def test_sequential_cases_run_before_the_stress_runs(environment, process):
    run(environment)
    ids = [case.id for case in process.requests[-1].jobs[0].cases]
    assert ids[:7] == ["ex1", "ex2", "h1", "h2", "h3", "h4", "s1:thread:0"]


def test_the_job_names_the_languages_model(environment, process):
    run(environment)
    assert process.requests[-1].jobs[0].model is ConcurrencyModel.THREADS


def test_runs_default_to_the_problems_runs(environment):
    assert [len(verdict.runs) for verdict in stress_of(run(environment))] == [3, 3]


def test_stress_flag_sets_the_runs_per_variant(environment):
    result = run(environment, stress=StressSelection(runs=5))
    assert [len(verdict.runs) for verdict in stress_of(result)] == [5, 5]


def test_seed_flag_replaces_the_base_seed(environment):
    result = run(environment, stress=StressSelection(runs=2, seed=7))
    assert [run_.seed for run_ in stress_of(result)[0].runs] == [7, 8]


def test_case_selects_one_stress_case(environment, process):
    run(environment, case_ids=("s2",))
    ids = [case.id for case in process.requests[-1].jobs[0].cases]
    assert ids == ["s2:thread:0", "s2:thread:1", "s2:thread:2"]


def test_a_race_fails_its_stress_cases(tmp_path):
    environment = environment_with(tmp_path, ScriptedRunnerProcess(duplicating))
    start_attempt(environment, StartRequest("bounded-blocking-queue", Language.PYTHON))
    statuses = [verdict.status for verdict in stress_of(run(environment))]
    assert statuses == [CaseStatus.FAIL, CaseStatus.FAIL]


def test_stress_on_another_problem_needs_a_generator_for_oracle_inputs(tmp_path):
    environment = environment_with(tmp_path, ScriptedRunnerProcess(queue), FIXTURE_PROBLEMS)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    with pytest.raises(UsageError, match=r"has no generator\.py"):
        run(environment, stress=StressSelection(runs=2))
