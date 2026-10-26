from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.ports import BuildFailed, UserCode
from coding_study.application.run_tests import RunTestsRequest, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import CaseStatus, Tally
from coding_study.domain.problem import Language
from coding_study.domain.runs import Returned, RunCase, RunJob, UserError
from tests.fakes import (
    NOW,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    two_sum,
)
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"


def wrong(job: RunJob, case: RunCase):
    return Returned([9, 9], 1000)


@pytest.fixture
def runner() -> FakeLanguageRunner:
    return FakeLanguageRunner()


def environment_with(tmp_path: Path, runner: FakeLanguageRunner, process: ScriptedRunnerProcess):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains({Language.PYTHON: runner}, {Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains, runner_process=process)


@pytest.fixture
def environment(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(two_sum))
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def run(environment, **fields):
    return run_tests(environment, RunTestsRequest(**fields), lambda _line: None)


def test_runs_the_active_attempt(environment):
    assert run(environment).meta.slug == "two-sum"


def test_every_case_passes_with_a_correct_solution(environment):
    assert run(environment).passed


def test_generated_cases_are_judged_too(environment):
    assert [case.id for case in run(environment).cases] == ["ex1", "ex2", "h1", "g1"]


def test_prepares_the_user_code(environment, runner):
    run(environment, typecheck=True)
    meta = environment.problems.load("two-sum").meta
    assert runner.scopes[-1] == UserCode(meta, typecheck=True)


def test_records_the_run(environment):
    result = run(environment)
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored.tally == Tally(total=4, passed=4)


def test_records_the_hash_of_the_user_file(environment):
    result = run(environment)
    expected = environment.workspace.content_hash("python/practice/two_sum.py")
    assert environment.progress.latest_test_run(result.attempt.id).code_hash == expected


def test_first_full_pass_is_recorded_on_the_attempt(environment):
    run(environment)
    assert environment.progress.active_attempt().first_pass_at == NOW


def test_failures_are_judged(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(wrong))
    start_attempt(environment, StartRequest("two-sum"))
    judgement = run(environment, case_ids=("ex1", "ex2", "h1")).judgement
    assert judgement is not None
    assert judgement.count(CaseStatus.FAIL) == 3


def test_failures_leave_first_pass_unset(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(wrong))
    start_attempt(environment, StartRequest("two-sum"))
    assert run(environment).attempt.first_pass_at is None


def test_selected_cases_only(environment):
    assert [case.id for case in run(environment, case_ids=("h1", "ex1")).cases] == ["ex1", "h1"]


def test_a_passing_subset_is_not_a_full_pass(environment):
    run(environment, case_ids=("ex1",))
    assert environment.progress.active_attempt().first_pass_at is None


def test_unknown_case_is_a_usage_error(environment):
    with pytest.raises(UsageError, match='no case "h9"'):
        run(environment, case_ids=("h9",))


def test_build_failure_is_reported_and_recorded(tmp_path):
    runner = FakeLanguageRunner(BuildFailed(("Solution.kt:3: error",)))
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(two_sum))
    start_attempt(environment, StartRequest("two-sum"))
    result = run(environment, case_ids=("ex1",))
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored is not None
    assert (result.build_failure, stored.tally) == (
        BuildFailed(("Solution.kt:3: error",)),
        Tally(total=1, errored=1),
    )


def test_load_error_is_reported(tmp_path, runner):
    process = ScriptedRunnerProcess(two_sum, {"two-sum": UserError("ImportError", "boom")})
    environment = environment_with(tmp_path, runner, process)
    start_attempt(environment, StartRequest("two-sum"))
    judgement = run(environment, case_ids=("ex1",)).judgement
    assert judgement is not None
    assert judgement.load_error == UserError("ImportError", "boom")


def test_no_active_attempt_is_a_usage_error(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(two_sum))
    with pytest.raises(UsageError, match="no attempt in progress"):
        run(environment)


def test_slug_without_an_attempt_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="cstudy start lru-cache"):
        run(environment, slug="lru-cache")


def test_language_without_an_attempt_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="kotlin"):
        run(environment, language=Language.KOTLIN)


def test_checker_problems_judge_with_checker_py(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(wrong))
    directory = environment.root / "problems" / "0001-two-sum"
    meta = directory / "meta.yaml"
    meta.write_text(meta.read_text().replace("{type: unordered}", "{type: checker}"))
    (directory / "checker.py").write_text(
        "def check(case_input, output, expected):\n    return None if output == [9, 9] else 'no'\n"
    )
    start_attempt(environment, StartRequest("two-sum"))
    assert run(environment, case_ids=("ex1", "h1")).passed


def test_result_carries_the_comparator_label(environment):
    assert run(environment).comparator.label == "unordered"


def test_durations_come_from_the_clock(environment):
    result = run(environment)
    assert result.duration_seconds > 0


def test_attempt_language_is_used(tmp_path, runner):
    environment = environment_with(tmp_path, runner, ScriptedRunnerProcess(two_sum))
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    environment = replace(environment)
    assert run(environment, slug="two-sum").language is Language.PYTHON
