"""A TypeScript project problem's suite, grading job and type check
(docs/specs/runners.md#project-jobs, docs/specs/cli.md#project-problems)."""

from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.ports import (
    BuildFailed,
    BuildScope,
    PrepareResult,
    ProgressNotice,
    ProjectGrading,
    ProjectSuite,
    RunnerLaunch,
    SuiteListener,
)
from coding_study.application.project_runs import (
    GradingRun,
    SuiteRun,
    run_grading,
    run_suite,
    typecheck_project,
)
from coding_study.application.verify_content import problem_content
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language, Problem
from coding_study.domain.runs import FileTarget, Returned, RunJob, RunnerInfo
from coding_study.domain.signature import ClassSignature
from coding_study.domain.static_checks import static_checks
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob, SuiteReport
from tests.fakes import FakeToolchains, ScriptedRunnerProcess, make_environment, repository_root
from tests.helpers import TYPESCRIPT_PROJECT_PROBLEMS
from tests.project_fakes import FakeProjectRunner

SLUG = "bank-project-typescript"
ROOT = Path("/ws/projects/bank-project-typescript")
REPORT = SuiteReport(RunnerInfo("typescript", 1, "24.18.0", ("project", "suite")))
DIAGNOSTICS = BuildFailed(("projects/bank-project-typescript/src/bank.ts(3,5): error TS2322",))


@dataclass
class TypeCheckingRunner(FakeProjectRunner):
    """A project runner whose language type-checks a folder, as TypeScript's does."""

    failure: BuildFailed | None = None
    checked: list[Path] = field(default_factory=list[Path])

    def typecheck_project(self, root: Path) -> BuildFailed | None:
        self.checked.append(root)
        return self.failure


class FileOnlyRunner:
    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("never prepared")


@dataclass
class RecordingSuiteProcess:
    jobs: list[SuiteJob] = field(default_factory=list[SuiteJob])

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        self.jobs.append(job)
        return REPORT


@pytest.fixture
def runner() -> TypeCheckingRunner:
    return TypeCheckingRunner()


@pytest.fixture
def environment(tmp_path, runner) -> Environment:
    toolchains = FakeToolchains(runners={Language.TYPESCRIPT: runner})
    root = repository_root(tmp_path, TYPESCRIPT_PROJECT_PROBLEMS)
    return make_environment(root, toolchains=toolchains)


@pytest.fixture
def problem(environment) -> Problem:
    return environment.problems.load(SLUG)


def sent_suite(environment: Environment, problem: Problem, level: int) -> SuiteJob:
    process = RecordingSuiteProcess()
    run = SuiteRun(problem.meta, Language.TYPESCRIPT, ROOT, level)
    run_suite(replace(environment, runner_process=process), run, [].append)
    (job,) = process.jobs
    return job


def graded_job(environment: Environment, problem: Problem, level: int) -> RunJob:
    process = ScriptedRunnerProcess(lambda job, case: Returned([None], 1_000))
    run = GradingRun(problem, Language.TYPESCRIPT, ROOT, level)
    run_grading(replace(environment, runner_process=process), run, [].append)
    (request,) = process.requests
    (job,) = request.jobs
    return job


def test_the_typescript_fixture_passes_the_static_checks(environment, problem):
    content = problem_content(environment, SLUG, problem)
    assert [str(issue) for issue in static_checks(content).errors] == []


def test_a_typescript_suite_is_run_by_node_test(environment, problem):
    assert sent_suite(environment, problem, 1).framework is SuiteFramework.NODE_TEST


def test_a_typescript_suite_runs_in_the_project_root(environment, problem, runner):
    sent_suite(environment, problem, 1)
    assert runner.scopes == [ProjectSuite(ROOT)]


def test_a_typescript_suite_leaves_out_the_test_files_of_locked_levels(environment, problem):
    assert sent_suite(environment, problem, 1).exclude == ("tests/level-2.test.ts",)


def test_typescript_grading_runs_in_the_project_root(environment, problem, runner):
    graded_job(environment, problem, 1)
    assert runner.scopes == [ProjectGrading(ROOT)]


def test_typescript_grading_targets_the_entry_file_in_the_project_root(environment, problem):
    job = graded_job(environment, problem, 1)
    assert job.target == FileTarget(f"{ROOT}/src/bank.ts")


def test_typescript_grading_sends_only_the_methods_of_the_graded_levels(environment, problem):
    signature = graded_job(environment, problem, 1).signature
    assert isinstance(signature, ClassSignature)
    assert [method.name for method in signature.methods] == ["createAccount", "deposit"]


def test_the_type_check_runs_on_the_project_folder(environment, runner):
    typecheck_project(environment, Language.TYPESCRIPT, ROOT)
    assert runner.checked == [ROOT]


def test_a_folder_that_type_checks_has_no_build_failure(environment):
    assert typecheck_project(environment, Language.TYPESCRIPT, ROOT) is None


def test_type_errors_are_the_build_failure(environment, runner):
    runner.failure = DIAGNOSTICS
    assert typecheck_project(environment, Language.TYPESCRIPT, ROOT) == DIAGNOSTICS


def test_a_language_without_a_type_check_has_nothing_to_check(environment):
    toolchains = FakeToolchains(runners={Language.PYTHON: FakeProjectRunner()})
    python = replace(environment, toolchains=toolchains)
    assert typecheck_project(python, Language.PYTHON, ROOT) is None


def test_a_language_without_project_jobs_cannot_type_check_a_project(environment):
    toolchains = FakeToolchains(runners={Language.JAVA: FileOnlyRunner()})
    java = replace(environment, toolchains=toolchains)
    with pytest.raises(RunnerStartError, match="java"):
        typecheck_project(java, Language.JAVA, ROOT)
