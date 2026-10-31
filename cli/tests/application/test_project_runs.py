"""Running a project problem's native suite and grading job (docs/specs/runners.md#project-jobs)."""

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
    ProjectScope,
    ProjectSuite,
    RunnerLaunch,
    SuiteListener,
)
from coding_study.application.project_runs import (
    SUITE_FRAMEWORKS,
    GradingRun,
    SuiteRun,
    project_runner,
    run_grading,
    run_suite,
    suite_job,
)
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.naming import ClassNames
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS
from coding_study.domain.problem import Language, Problem, ProblemKind, ProblemMeta
from coding_study.domain.runs import (
    CaseOutcome,
    ProjectTarget,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunnerInfo,
    UserError,
)
from coding_study.domain.signature import ClassSignature
from coding_study.domain.suite_runs import SuiteFramework, SuiteJob, SuiteReport, SuiteTest
from tests.fakes import FakeToolchains, ScriptedRunnerProcess, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS

SLUG = "bank-project-python"
LAUNCH = RunnerLaunch(("python", "-P", "-m", "cs_runner"), Path("/ws/projects/bank"), 5_000)
REPORT = SuiteReport(RunnerInfo("python", 1, "3.13", ("project", "suite")))


COMPILER_LINES = ("Bank.java:3: error: ';' expected", "        int x", "             ^")
COMPILE_ERROR = UserError("CompileError", "the project does not compile", "\n".join(COMPILER_LINES))


@dataclass
class FakeProjectRunner:
    scopes: list[ProjectScope] = field(default_factory=list[ProjectScope])
    build_failure: BuildFailed | None = None

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("a project job is prepared with prepare_project")

    def prepare_project(
        self, scope: ProjectScope, notify: ProgressNotice
    ) -> RunnerLaunch | BuildFailed:
        self.scopes.append(scope)
        return self.build_failure or LAUNCH


class FileOnlyRunner:
    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("never prepared")


@dataclass
class RecordingSuiteProcess:
    suites: list[tuple[RunnerLaunch, SuiteJob]] = field(
        default_factory=list[tuple[RunnerLaunch, SuiteJob]]
    )
    listeners: list[SuiteListener | None] = field(default_factory=list[SuiteListener | None])

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        self.suites.append((launch, job))
        self.listeners.append(listener)
        return REPORT


@dataclass
class SilentTests:
    """A suite listener that keeps nothing."""

    def test_started(self, test_id: str) -> None:
        pass

    def test_finished(self, test: SuiteTest) -> None:
        pass


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
def problem(environment) -> Problem:
    return environment.problems.load(SLUG)


@pytest.fixture
def meta(problem) -> ProblemMeta:
    return problem.meta


def suite_run(meta: ProblemMeta, level: int = 1, **fields: object) -> SuiteRun:
    run = SuiteRun(meta, Language.PYTHON, Path("/ws/projects/bank"), level)
    return replace(run, **fields)  # type: ignore[arg-type]


def sent_job(environment: Environment, run: SuiteRun, process: RecordingSuiteProcess) -> SuiteJob:
    run_suite(environment, run, [].append)
    ((_, job),) = process.suites
    return job


def test_the_suite_runs_in_the_project_root(environment, meta, runner):
    run_suite(environment, suite_run(meta, level=2), [].append)
    assert runner.scopes == [ProjectSuite(Path("/ws/projects/bank"))]


def test_the_build_leaves_out_the_generated_files_of_locked_levels(environment, meta, runner):
    """A Java or Kotlin build compiles no test file the run leaves out: it may call methods that
    do not exist yet."""
    run_suite(environment, suite_run(meta, level=1), [].append)
    assert runner.scopes[0].exclude == ("tests/test_level_2.py",)


def test_a_suite_that_does_not_build_reports_the_compiler_lines(environment, meta, runner):
    runner.build_failure = BuildFailed(COMPILER_LINES)
    assert run_suite(environment, suite_run(meta), [].append).load_error == COMPILE_ERROR


def test_a_suite_that_does_not_build_starts_no_runner(environment, meta, runner, process):
    runner.build_failure = BuildFailed(COMPILER_LINES)
    run_suite(environment, suite_run(meta), [].append)
    assert process.suites == []


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_jvm_suite_is_run_by_the_junit_platform(meta, language):
    job = suite_job(replace(suite_run(meta), language=language), Config())
    assert job.framework is SuiteFramework.JUNIT_PLATFORM


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
    run_suite(environment, suite_run(meta, level=2, debug=session), [].append)
    assert runner.scopes == [ProjectSuite(Path("/ws/projects/bank"), session)]


def test_a_runner_without_project_jobs_cannot_run_a_project(environment):
    toolchains = FakeToolchains(runners={Language.JAVA: FileOnlyRunner()})
    with pytest.raises(RunnerStartError, match="java"):
        project_runner(toolchains, Language.JAVA)


ROOT = Path("/ws/projects/bank")
SESSION_ERROR = UserError("KeyError", "ann")


def correct_answers(problem: Problem):
    """The expected output of every case, as a correct project would return it."""
    expected = {case.id: case.expected for case in problem.cases}

    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        wanted = expected[case.id]
        assert wanted is not None
        return Returned(wanted.value, 1_000)

    return answer


@pytest.fixture
def grading_process(problem) -> ScriptedRunnerProcess:
    return ScriptedRunnerProcess(correct_answers(problem))


@pytest.fixture
def grading_environment(environment, grading_process) -> Environment:
    return replace(environment, runner_process=grading_process)


def grading_run(problem: Problem, level: int = 2) -> GradingRun:
    return GradingRun(problem, Language.PYTHON, ROOT, level)


def graded_job(environment: Environment, run: GradingRun, process: ScriptedRunnerProcess) -> RunJob:
    run_grading(environment, run, [].append)
    (request,) = process.requests
    (job,) = request.jobs
    return job


def graded_methods(job: RunJob) -> tuple[str, ...]:
    assert isinstance(job.signature, ClassSignature)
    return tuple(method.name for method in job.signature.methods)


def test_grading_runs_in_the_project_root(grading_environment, problem, runner):
    run_grading(grading_environment, grading_run(problem), [].append)
    assert runner.scopes == [ProjectGrading(ROOT)]


def test_grading_tells_the_runner_the_problem_and_the_graded_level(
    grading_environment, problem, runner
):
    run_grading(grading_environment, grading_run(problem, level=1), [].append)
    (scope,) = runner.scopes
    assert (scope.meta, getattr(scope, "level", None)) == (problem.meta, 1)


def test_the_suite_tells_the_runner_the_problem(environment, meta, runner):
    run_suite(environment, suite_run(meta), [].append)
    assert runner.scopes[0].meta == meta


def test_a_go_suite_is_run_by_go_test():
    assert SUITE_FRAMEWORKS[Language.GO] is SuiteFramework.GO_TEST


def test_grading_is_one_class_job_of_the_project_kind_under_the_slug(
    grading_environment, grading_process, problem
):
    job = graded_job(grading_environment, grading_run(problem), grading_process)
    assert (job.job_id, job.kind) == (SLUG, ProblemKind.PROJECT)


def test_grading_targets_the_project_folder_and_its_entry_module(
    grading_environment, grading_process, problem
):
    job = graded_job(grading_environment, grading_run(problem), grading_process)
    assert job.target == ProjectTarget(str(ROOT), "bank.bank")


def test_grading_sends_only_the_methods_of_the_graded_levels(
    grading_environment, grading_process, problem
):
    job = graded_job(grading_environment, grading_run(problem, level=1), grading_process)
    assert graded_methods(job) == ("createAccount", "deposit")


def test_grading_names_only_the_methods_of_the_graded_levels(
    grading_environment, grading_process, problem
):
    job = graded_job(grading_environment, grading_run(problem, level=1), grading_process)
    assert isinstance(job.names, ClassNames)
    assert set(job.names.methods) == {"createAccount", "deposit"}


def test_grading_sends_the_cases_of_levels_one_to_the_graded_level(
    grading_environment, grading_process, problem
):
    job = graded_job(grading_environment, grading_run(problem, level=1), grading_process)
    assert [case.id for case in job.cases] == ["ex1", "h1", "h2"]


def test_grading_the_last_level_sends_every_case(grading_environment, grading_process, problem):
    job = graded_job(grading_environment, grading_run(problem, level=2), grading_process)
    assert len(job.cases) == len(problem.cases)


def test_grading_resolves_each_cases_hang_guard(grading_environment, grading_process, problem):
    job = graded_job(grading_environment, grading_run(problem), grading_process)
    assert {case.hang_guard_ms for case in job.cases} == {DEFAULT_HANG_GUARD_MS}


def test_a_correct_project_passes_every_graded_case(grading_environment, grading_process, problem):
    judgement = run_grading(grading_environment, grading_run(problem), [].append)
    assert (judgement.passed, judgement.case_count) == (True, len(problem.cases))


def test_a_case_that_raises_is_judged_an_error(environment, problem):
    raising = ScriptedRunnerProcess(lambda job, case: Raised(SESSION_ERROR, 1_000))
    judgement = run_grading(
        replace(environment, runner_process=raising), grading_run(problem), [].append
    )
    assert judgement.count(CaseStatus.ERROR) == len(problem.cases)


def test_a_project_that_does_not_load_has_a_load_error(environment, problem):
    broken = ScriptedRunnerProcess(correct_answers(problem), {SLUG: SESSION_ERROR})
    judgement = run_grading(
        replace(environment, runner_process=broken), grading_run(problem), [].append
    )
    assert judgement.load_error == SESSION_ERROR


def test_a_project_that_does_not_build_has_a_load_error(grading_environment, problem, runner):
    runner.build_failure = BuildFailed(COMPILER_LINES)
    judgement = run_grading(grading_environment, grading_run(problem), [].append)
    assert (judgement.load_error, judgement.case_count) == (COMPILE_ERROR, len(problem.cases))


def test_a_project_that_does_not_build_starts_no_runner(
    grading_environment, grading_process, problem, runner
):
    runner.build_failure = BuildFailed(COMPILER_LINES)
    run_grading(grading_environment, grading_run(problem), [].append)
    assert grading_process.requests == []


def test_a_problem_without_a_project_block_cannot_be_graded(
    grading_environment, grading_process, problem
):
    plain = replace(problem, meta=replace(problem.meta, project=None))
    with pytest.raises(ValueError, match="not a project problem"):
        run_grading(grading_environment, grading_run(plain), [].append)


def test_a_runner_without_project_jobs_cannot_grade(environment, problem):
    toolchains = FakeToolchains(runners={Language.PYTHON: FileOnlyRunner()})
    with pytest.raises(RunnerStartError, match="python"):
        run_grading(replace(environment, toolchains=toolchains), grading_run(problem), [].append)


@dataclass
class HeardVerdicts:
    """What a grading's listener heard, in order: each case started, then each verdict."""

    heard: list[tuple[str, CaseStatus | None]] = field(
        default_factory=list[tuple[str, CaseStatus | None]]
    )

    def case_started(self, case: RunnableCase) -> None:
        self.heard.append((case.id, None))

    def case_judged(self, verdict: CaseVerdict) -> None:
        self.heard.append((verdict.case.id, verdict.status))


def test_a_suite_tells_the_runs_listener_of_each_test(environment, meta, process):
    listener = SilentTests()
    run_suite(environment, suite_run(meta, listener=listener), [].append)
    assert process.listeners == [listener]


def test_grading_judges_each_case_for_the_listener_as_it_ends(environment, problem):
    wrong_on_h1 = correct_answers(problem)
    answers = ScriptedRunnerProcess(
        lambda job, case: Returned(["wrong"], 1) if case.id == "h1" else wrong_on_h1(job, case)
    )
    listener = HeardVerdicts()
    run = replace(grading_run(problem, level=1), listener=listener)
    run_grading(replace(environment, runner_process=answers), run, [].append)
    assert listener.heard == [
        ("ex1", None),
        ("ex1", CaseStatus.PASS),
        ("h1", None),
        ("h1", CaseStatus.FAIL),
        ("h2", None),
        ("h2", CaseStatus.PASS),
    ]
