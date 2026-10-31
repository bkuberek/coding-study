"""`cstudy verify` on a project problem (docs/specs/authoring.md#project-problems): coverage from
the overlay, then D1 (the starter loads), D3 (the reference passes every case of every level) and
D9 (the reference passes its native suite), each through a runner of its own."""

import shutil
from collections.abc import Callable, Mapping
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
    ProjectTestGenerator,
    RunnerLaunch,
)
from coding_study.application.verify_content import (
    ProblemVerification,
    SkippedCheck,
    VerifyRequest,
    verify_content,
)
from coding_study.application.verify_projects import (
    PROJECT_BUILDS,
    STARTER_BUILDS,
    SuiteCheck,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language
from coding_study.domain.project_tests import LevelTests
from coding_study.domain.runs import (
    CaseOutcome,
    CaseReport,
    Crashed,
    JobReport,
    Raised,
    Returned,
    RunCase,
    RunnerInfo,
    RunReport,
    RunRequest,
    UserError,
)
from coding_study.domain.signature import ClassSignature
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteJob,
    SuiteReport,
    SuiteTest,
)
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS

SLUG = "bank-project-python"
REFERENCE_BUILD = f"{PROJECT_BUILDS}/{SLUG}/reference"
STARTER_BUILD = f"{STARTER_BUILDS}/{SLUG}"
RUNNER = RunnerInfo("python", 1, "3.13", ("project", "suite"))
NOT_IMPLEMENTED = UserError("NotImplementedError", "")
LEVEL_TESTS = ("tests/test_level_1.py::test_ex1", "tests/test_level_2.py::test_ex2")


class FakeTestGenerator:
    """One line per visible case, so a test can tell what was generated."""

    def generate(self, tests: LevelTests) -> str:
        names = "".join(f"test {test.case_id}\n" for test in tests.tests)
        return f"# level {tests.level} of {tests.slug}\n{names}"


@dataclass
class ProjectToolchains(FakeToolchains):
    generators: dict[Language, ProjectTestGenerator] = field(
        default_factory=lambda: {Language.PYTHON: FakeTestGenerator()}
    )

    def project_test_generator(self, language: Language) -> ProjectTestGenerator:
        if language not in self.generators:
            raise LanguageNotSetUpError(language, "project test generator")
        return self.generators[language]


class LaunchInTheRoot:
    """A project runner whose launch starts in the project root it was prepared for."""

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise AssertionError("a project job is prepared with prepare_project")

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        return RunnerLaunch(("python",), scope.root, 1_000)


type Answer = Callable[[RunCase], CaseOutcome]


def raises_not_implemented(case: RunCase) -> CaseOutcome:
    return Raised(NOT_IMPLEMENTED, 1_000)


def passing_suite(*test_ids: str) -> SuiteReport:
    return SuiteReport(RUNNER, tuple(SuiteTest(test_id, Passed(1_000)) for test_id in test_ids))


@dataclass
class ProjectProcess:
    """Runs the starter's build as a starter (every call raises) and the reference's as a
    correct project; `answers`, `load_errors` and `suites` override either, by build name."""

    expected: Mapping[str, JsonValue]
    answers: dict[str, Answer] = field(default_factory=dict[str, Answer])
    load_errors: dict[str, UserError] = field(default_factory=dict[str, UserError])
    suites: dict[str, SuiteReport] = field(default_factory=dict[str, SuiteReport])
    graded: list[tuple[str, RunRequest]] = field(default_factory=list[tuple[str, RunRequest]])
    suite_jobs: list[tuple[str, SuiteJob]] = field(default_factory=list[tuple[str, SuiteJob]])

    def run(self, launch: RunnerLaunch, request: RunRequest) -> RunReport:
        build = _build_name(launch.cwd)
        self.graded.append((build, request))
        (job,) = request.jobs
        if build in self.load_errors:
            return RunReport(RUNNER, (JobReport(job.job_id, load_error=self.load_errors[build]),))
        answer = self.answers.get(build, self._default(build))
        cases = tuple(CaseReport(case.id, answer(case)) for case in job.cases)
        return RunReport(RUNNER, (JobReport(job.job_id, cases),))

    def run_suite(self, launch: RunnerLaunch, job: SuiteJob) -> SuiteReport:
        build = _build_name(launch.cwd)
        self.suite_jobs.append((build, job))
        return self.suites.get(build, passing_suite(*LEVEL_TESTS))

    def _default(self, build: str) -> Answer:
        if build == "starter":
            return raises_not_implemented
        return lambda case: Returned(self.expected[case.id], 1_000)


def _build_name(root: Path) -> str:
    return "starter" if STARTER_BUILDS in root.as_posix() else "reference"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PROJECT_PROBLEMS)


@pytest.fixture
def process(root: Path) -> ProjectProcess:
    problem = make_environment(root).problems.load(SLUG)
    expected = {case.id: case.expected.value for case in problem.cases if case.expected}
    return ProjectProcess(expected)


@pytest.fixture
def environment(root: Path, process: ProjectProcess) -> Environment:
    toolchains = ProjectToolchains(runners={Language.PYTHON: LaunchInTheRoot()})
    return make_environment(root, toolchains=toolchains, runner_process=process)


def verify(environment: Environment, **fields: object) -> ProblemVerification:
    request = VerifyRequest(**{"slugs": (SLUG,), **fields})  # type: ignore[arg-type]
    [problem] = verify_content(environment, request, lambda _line: None).problems
    return problem


def coverage(environment: Environment, language: Language) -> tuple[int, int]:
    request = VerifyRequest(slugs=(SLUG,), static_only=True)
    report = verify_content(environment, request, lambda _line: None)
    [entry] = (entry for entry in report.coverage if entry.language is language)
    return entry.covered, entry.listed


def build_files(root: Path, build: str) -> dict[str, str]:
    folder = root / build
    return {
        path.relative_to(folder).as_posix(): path.read_text()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def graded_levels(process: ProjectProcess, build: str) -> list[tuple[str, ...]]:
    return [
        tuple(method.name for method in job.signature.methods)
        for graded, request in process.graded
        if graded == build
        for job in request.jobs
        if isinstance(job.signature, ClassSignature)
    ]


# coverage


def test_a_projects_reference_language_is_its_overlays(environment):
    assert verify(environment, static_only=True).reference_languages == (Language.PYTHON,)


def test_a_project_without_an_overlay_has_no_reference_language(environment, root):
    shutil.rmtree(root / "problems" / BANK_PROJECT / "solutions" / "reference")
    assert verify(environment, static_only=True).reference_languages == ()


def test_a_project_counts_towards_the_coverage_of_its_language(environment):
    assert coverage(environment, Language.PYTHON) == (1, 1)


def test_a_project_is_not_listed_under_other_languages(environment):
    assert coverage(environment, Language.TYPESCRIPT) == (0, 0)


# the builds


def test_the_reference_build_is_the_starter_with_its_overlay(environment, root):
    verify(environment)
    overlay = root / "problems" / BANK_PROJECT / "solutions" / "reference" / "bank" / "bank.py"
    files = build_files(root, REFERENCE_BUILD)
    assert (files["bank/bank.py"], "README.md" in files) == (overlay.read_text(), True)


def test_the_reference_build_holds_the_generated_tests_of_every_level(environment, root):
    verify(environment)
    files = build_files(root, REFERENCE_BUILD)
    assert (files["tests/test_level_1.py"], files["tests/test_level_2.py"]) == (
        f"# level 1 of {SLUG}\ntest ex1\n",
        f"# level 2 of {SLUG}\ntest ex2\n",
    )


def test_the_starter_build_is_the_starter_with_level_ones_tests(environment, root):
    verify(environment)
    starter = root / "problems" / BANK_PROJECT / "starter" / "bank" / "bank.py"
    files = build_files(root, STARTER_BUILD)
    assert (files["bank/bank.py"], "tests/test_level_1.py" in files) == (starter.read_text(), True)


def test_the_starter_build_has_no_later_levels_tests(environment, root):
    verify(environment)
    assert "tests/test_level_2.py" not in build_files(root, STARTER_BUILD)


def test_verify_needs_the_project_test_generator(environment):
    toolchains = ProjectToolchains(runners={Language.PYTHON: LaunchInTheRoot()}, generators={})
    with pytest.raises(LanguageNotSetUpError, match="project test generator"):
        verify(replace(environment, toolchains=toolchains))


# a project that passes


def test_a_correct_project_passes(environment):
    assert verify(environment).passed


def test_the_reference_is_the_projects_one_passing_approach(environment):
    [result] = verify(environment).languages
    assert (result.language, result.passing, len(result.approaches)) == (Language.PYTHON, 1, 1)


def test_the_suite_counts_the_tests_that_passed(environment):
    assert verify(environment).suite == SuiteCheck(2, 2)


def test_a_skipped_test_counts_as_passing(environment, process):
    skipped = SuiteTest("tests/test_mine.py::test_later", Skipped("not today", 1_000))
    report = passing_suite(*LEVEL_TESTS)
    process.suites["reference"] = replace(report, tests=(*report.tests, skipped))
    assert verify(environment).suite == SuiteCheck(3, 3)


def test_the_reference_is_graded_at_its_last_level(environment, process):
    verify(environment)
    assert graded_levels(process, "reference") == [("createAccount", "deposit", "transfer")]


def test_the_reference_suite_runs_every_levels_tests(environment, process):
    verify(environment)
    [job] = [job for build, job in process.suite_jobs if build == "reference"]
    assert job.exclude == ()


def test_the_starter_is_graded_at_level_one(environment, process):
    verify(environment)
    assert graded_levels(process, "starter") == [("createAccount", "deposit")]


def test_every_project_job_gets_a_runner_of_its_own(environment, process):
    verify(environment)
    assert [len(request.jobs) for _, request in process.graded] == [1, 1]


def test_oracle_and_ladder_do_not_apply_to_a_project(environment):
    problem = verify(environment, oracle_cases=20, ladder=True)
    assert problem.skipped == (SkippedCheck.ORACLE, SkippedCheck.LADDER)


def test_another_language_leaves_the_project_out(environment):
    request = VerifyRequest(slugs=(SLUG,), language=Language.TYPESCRIPT)
    assert verify_content(environment, request, lambda _line: None).problems == ()


# D3: the reference


def test_a_failing_case_names_its_level(environment, process):
    process.answers["reference"] = lambda case: Returned(
        [None, True, 0] if case.id == "h3" else process.expected[case.id], 1_000
    )
    [result] = verify(environment).languages
    [failure] = result.approaches[0].failures
    assert failure.startswith("level 2 h3 FAIL: expected [null, true, -1], got [null, true, 0]")


def test_a_reference_that_does_not_load_fails(environment, process):
    process.load_errors["reference"] = UserError("SymbolNotFound", "bank.bank has no class Bank")
    [result] = verify(environment).languages
    assert result.approaches[0].failures == (
        "does not load: SymbolNotFound: bank.bank has no class Bank",
    )


# D9: the reference's suite


def test_a_failing_test_fails_the_suite(environment, process):
    failed = SuiteTest(LEVEL_TESTS[1], AssertionFailed("assert -1 == 300\n where ...", 1_000))
    process.suites["reference"] = SuiteReport(
        RUNNER, (SuiteTest(LEVEL_TESTS[0], Passed(1_000)), failed)
    )
    problem = verify(environment)
    assert (problem.suite, problem.passed) == (
        SuiteCheck(1, 2, (f"{LEVEL_TESTS[1]} failed: assert -1 == 300",)),
        False,
    )


def test_a_test_that_raises_names_the_exception(environment, process):
    raised = SuiteTest(LEVEL_TESTS[0], Raised(UserError("KeyError", "'ivy'"), 1_000))
    process.suites["reference"] = SuiteReport(RUNNER, (raised,))
    assert verify(environment).suite == SuiteCheck(
        0, 1, (f"{LEVEL_TESTS[0]} error: KeyError: 'ivy'",)
    )


def test_a_suite_that_does_not_run_fails(environment, process):
    usage = UserError("UsageError", "unrecognized arguments: --bad")
    process.suites["reference"] = SuiteReport(RUNNER, load_error=usage)
    assert verify(environment).suite == SuiteCheck(
        0, 0, ("does not run: UsageError: unrecognized arguments: --bad",)
    )


def test_a_suite_that_stopped_early_fails(environment, process):
    crashed = SuiteTest(LEVEL_TESTS[0], Crashed(1))
    process.suites["reference"] = SuiteReport(
        RUNNER, (crashed,), stopped_early="the runner crashed 3 times"
    )
    assert verify(environment).suite == SuiteCheck(
        0,
        1,
        (
            f"{LEVEL_TESTS[0]} runner crashed with exit code 1",
            "stopped early: the runner crashed 3 times",
        ),
    )


# D1: the starter


def test_a_starter_that_does_not_load_fails(environment, process):
    process.load_errors["starter"] = UserError("SyntaxError", "invalid syntax (bank.py, line 3)")
    [result] = verify(environment).languages
    assert result.problems == (
        "starter does not load: SyntaxError: invalid syntax (bank.py, line 3)",
    )


def test_a_starter_that_crashes_the_runner_fails(environment, process):
    process.answers["starter"] = lambda case: Crashed(1)
    [result] = verify(environment).languages
    assert result.problems == ("starter runner crashed with exit code 1",)


def test_a_starter_whose_cases_fail_still_loads(environment):
    [result] = verify(environment).languages
    assert result.problems == ()


def test_a_starter_suite_that_crashes_the_runner_fails(environment, process):
    process.suites["starter"] = SuiteReport(RUNNER, (SuiteTest(LEVEL_TESTS[0], Crashed(1)),))
    [result] = verify(environment).languages
    assert result.problems == (f"starter suite: {LEVEL_TESTS[0]} runner crashed with exit code 1",)


def test_a_starter_suite_that_does_not_run_fails(environment, process):
    usage = UserError("UsageError", "no such option")
    process.suites["starter"] = SuiteReport(RUNNER, load_error=usage)
    [result] = verify(environment).languages
    assert result.problems == ("starter suite does not run: UsageError: no such option",)


def test_the_starter_suite_runs_in_the_starters_build(environment, process, root):
    verify(environment)
    [job] = [job for build, job in process.suite_jobs if build == "starter"]
    assert job.root == str(root / STARTER_BUILD)


def test_the_suite_runs_in_the_reference_build(environment, process, root):
    verify(environment)
    [job] = [job for build, job in process.suite_jobs if build == "reference"]
    assert job.root == str(root / REFERENCE_BUILD)


def test_a_project_suite_is_prepared_as_a_suite(environment, root):
    prepared: list[ProjectScope] = []

    class Recording(LaunchInTheRoot):
        def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
            prepared.append(scope)
            return super().prepare_project(scope, notify)

    toolchains = ProjectToolchains(runners={Language.PYTHON: Recording()})
    verify(replace(environment, toolchains=toolchains))
    assert ProjectSuite(root / REFERENCE_BUILD) in prepared
