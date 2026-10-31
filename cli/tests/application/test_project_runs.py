"""Running a project problem's native suite (docs/specs/runners.md#project-jobs)."""

from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildScope,
    PrepareResult,
    ProgressNotice,
    ProjectScope,
    ProjectSuite,
    RunnerLaunch,
)
from coding_study.application.project_runs import SuiteRun, project_runner, run_suite
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import RunnerInfo
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob, SuiteReport
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS

SLUG = "bank-project-python"
LAUNCH = RunnerLaunch(("python", "-P", "-m", "cs_runner"), Path("/ws/projects/bank"), 5_000)
REPORT = SuiteReport(RunnerInfo("python", 1, "3.13", ("project", "suite")))


@dataclass
class FakeProjectRunner:
    scopes: list[ProjectScope] = field(default_factory=list[ProjectScope])

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("a project job is prepared with prepare_project")

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        self.scopes.append(scope)
        return LAUNCH


class FileOnlyRunner:
    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("never prepared")


@dataclass
class RecordingSuiteProcess:
    suites: list[tuple[RunnerLaunch, SuiteJob]] = field(
        default_factory=list[tuple[RunnerLaunch, SuiteJob]]
    )

    def run_suite(self, launch: RunnerLaunch, job: SuiteJob) -> SuiteReport:
        self.suites.append((launch, job))
        return REPORT


@pytest.fixture
def runner() -> FakeProjectRunner:
    return FakeProjectRunner()


@pytest.fixture
def process() -> RecordingSuiteProcess:
    return RecordingSuiteProcess()


@pytest.fixture
def environment(tmp_path, runner, process) -> Environment:
    toolchains = FakeToolchains(runners={Language.PYTHON: runner})
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    return make_environment(root, toolchains=toolchains, runner_process=process)


@pytest.fixture
def meta(environment) -> ProblemMeta:
    return environment.problems.load(SLUG).meta


def suite_run(meta: ProblemMeta, level: int = 1, **fields: object) -> SuiteRun:
    run = SuiteRun(meta, Language.PYTHON, Path("/ws/projects/bank"), level)
    return replace(run, **fields)  # type: ignore[arg-type]


def sent_job(environment: Environment, run: SuiteRun, process: RecordingSuiteProcess) -> SuiteJob:
    run_suite(environment, run, [].append)
    ((_, job),) = process.suites
    return job


def test_the_suite_runs_in_the_project_root(environment, meta, runner):
    run_suite(environment, suite_run(meta), [].append)
    assert runner.scopes == [ProjectSuite(Path("/ws/projects/bank"))]


def test_the_suite_runs_through_the_prepared_launch(environment, meta, process):
    run_suite(environment, suite_run(meta), [].append)
    assert process.suites[0][0] == LAUNCH


def test_the_report_is_the_runners(environment, meta):
    assert run_suite(environment, suite_run(meta), [].append) == REPORT


def test_a_python_suite_is_run_by_pytest_under_the_problems_job_id(environment, meta, process):
    job = sent_job(environment, suite_run(meta), process)
    assert (job.job_id, job.framework, job.root) == (
        f"{SLUG}/suite",
        SuiteFramework.PYTEST,
        "/ws/projects/bank",
    )


def test_the_generated_files_of_levels_above_the_run_are_left_out(environment, meta, process):
    assert sent_job(environment, suite_run(meta, level=1), process).exclude == (
        "tests/test_level_2.py",
    )


def test_a_run_of_the_last_level_leaves_out_no_file(environment, meta, process):
    assert sent_job(environment, suite_run(meta, level=2), process).exclude == ()


def test_the_selected_tests_are_sent(environment, meta, process):
    run = suite_run(meta, select=("test_ex1",))
    assert sent_job(environment, run, process).select == ("test_ex1",)


def test_the_hang_guard_defaults_to_the_runner_limit(environment, meta, process):
    assert sent_job(environment, suite_run(meta), process).hang_guard_ms == DEFAULT_HANG_GUARD_MS


def test_the_problems_hang_guard_applies_to_each_test(environment, meta, process):
    run = suite_run(replace(meta, hang_guard_ms=2_500))
    assert sent_job(environment, run, process).hang_guard_ms == 2_500


def test_the_configured_hang_guard_wins(environment, meta, process):
    configured = replace(environment, config=Config(hang_guard=HangGuardSettings(ms=700)))
    run = suite_run(replace(meta, hang_guard_ms=2_500))
    assert sent_job(configured, run, process).hang_guard_ms == 700


def test_a_debug_session_reaches_the_launch(environment, meta, runner):
    session = DebugSession(Language.PYTHON, 5678)
    run_suite(environment, suite_run(meta, debug=session), [].append)
    assert runner.scopes == [ProjectSuite(Path("/ws/projects/bank"), session)]


def test_a_runner_without_project_jobs_cannot_run_a_project(environment):
    toolchains = FakeToolchains(runners={Language.JAVA: FileOnlyRunner()})
    with pytest.raises(RunnerStartError, match="java"):
        project_runner(toolchains, Language.JAVA)
