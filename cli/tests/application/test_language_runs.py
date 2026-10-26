from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.language_runs import LanguageRun
from coding_study.application.ports import BuildFailed, Prepared, ReferenceSource
from coding_study.domain.cases import Expected, FunctionInput
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.judging import RunnableCase
from coding_study.domain.naming import FunctionNames
from coding_study.domain.problem import Language
from coding_study.domain.runs import (
    CaseReport,
    FileTarget,
    JobReport,
    Returned,
    RunCase,
    RunnerInfo,
    RunReport,
)
from tests.fakes import (
    FAKE_LAUNCH,
    FakeLanguageRunner,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
CASE = RunnableCase("ex1", FunctionInput({"nums": [1, 2], "target": 3}), Expected([0, 1]))


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PRACTICE)


def language_run(root: Path, **overrides) -> LanguageRun:
    environment = make_environment(root, **overrides)
    return LanguageRun(environment, environment.problems.load("two-sum").meta, Language.PYTHON)


def test_user_job_is_named_after_the_slug(root):
    assert language_run(root).user_job([CASE]).job_id == "two-sum"


def test_user_job_targets_the_stub(root):
    target = language_run(root).user_job([CASE]).target
    assert target == FileTarget(f"{root}/python/practice/two_sum.py")


def test_user_job_uses_the_language_names(root):
    names = language_run(root).user_job([CASE]).names
    assert names == FunctionNames("two_sum", {"nums": "nums", "target": "target"})


def test_cases_get_the_default_hang_guard(root):
    assert language_run(root).user_job([CASE]).cases == (RunCase("ex1", CASE.input, 10_000),)


def test_case_hang_guard_overrides_the_default(root):
    case = replace(CASE, hang_guard_ms=30_000)
    assert language_run(root).user_job([case]).cases[0].hang_guard_ms == 30_000


def test_config_hang_guard_overrides_the_case(root):
    config = Config(hang_guard=HangGuardSettings(ms=500))
    case = replace(CASE, hang_guard_ms=30_000)
    assert language_run(root, config=config).user_job([case]).cases[0].hang_guard_ms == 500


def test_reference_job_is_named_after_slug_and_approach(root):
    assert language_run(root).reference_job("hash-map", [CASE]).job_id == "two-sum/hash-map"


def test_reference_job_targets_the_materialized_copy(root):
    target = language_run(root).reference_job("hash-map", [CASE]).target
    assert target == FileTarget(f"{root}/.cs/build/python/ref/two_sum/hash_map.py")


def test_references_point_at_the_solution_files(root):
    scope = language_run(root).references(["hash-map"])
    assert scope.sources == (
        ReferenceSource("hash-map", root / "problems/0001-two-sum/solutions/hash-map.py"),
    )


def test_run_prepares_then_runs_the_jobs(root):
    process = ScriptedRunnerProcess(lambda job, case: Returned([0, 1], 5))
    runner = FakeLanguageRunner()
    run = language_run(
        root, runner_process=process, toolchains=FakeToolchains({Language.PYTHON: runner})
    )
    result = run.run(run.references(["hash-map"]), [run.user_job([CASE])], print)
    assert result.report == RunReport(
        RunnerInfo("fake", 1, "0"),
        (JobReport("two-sum", (CaseReport("ex1", Returned([0, 1], 5)),)),),
    )


def test_run_reports_the_build_time_and_note(root):
    runner = FakeLanguageRunner(Prepared(FAKE_LAUNCH, "gradle, warm"))
    process = ScriptedRunnerProcess(lambda job, case: Returned([0, 1], 5))
    run = language_run(
        root, runner_process=process, toolchains=FakeToolchains({Language.PYTHON: runner})
    )
    result = run.run(run.references(["hash-map"]), [run.user_job([CASE])], print)
    assert (result.build_seconds, result.build_note) == (0.25, "gradle, warm")


def test_build_failure_skips_the_run(root):
    process = ScriptedRunnerProcess(lambda job, case: Returned([0, 1], 5))
    runner = FakeLanguageRunner(BuildFailed(("Solution.kt:3: error",)))
    run = language_run(
        root, runner_process=process, toolchains=FakeToolchains({Language.PYTHON: runner})
    )
    result = run.run(run.references(["hash-map"]), [run.user_job([CASE])], print)
    assert (result.build_failure, process.requests) == (BuildFailed(("Solution.kt:3: error",)), [])


def test_references_scope_names_the_problem(root):
    assert language_run(root).references(["hash-map"]).meta.slug == "two-sum"
