"""`cstudy verify` on a project problem (docs/specs/authoring.md#project-problems): coverage from
the overlay, then D1 (the starter loads), D3 (the reference passes every case of every level), D9
(the reference passes its native suite) and, on the virtual clock, D10 (the reference gives the
same outputs in every run), each through a runner of its own."""

import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application import verify_projects
from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed, ProjectSuite
from coding_study.application.project_runs import compile_error
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
from coding_study.domain import virtual_clock
from coding_study.domain.cases import JsonValue
from coding_study.domain.clock_determinism import DETERMINISM_RUNS, DeterminismVerdict
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language
from coding_study.domain.runs import Crashed, Raised, Returned, UserError
from coding_study.domain.signature import ClassSignature
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Passed,
    Skipped,
    SuiteTest,
)
from tests.fakes import make_environment, repository_root
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS
from tests.project_fakes import (
    PROJECT_SLUG,
    FakeProjectRunner,
    FakeTestGenerator,
    ScriptedBuilds,
    ScriptedProjectProcess,
    project_toolchains,
    scripted_builds,
)

REFERENCE_BUILD = f"{PROJECT_BUILDS}/{PROJECT_SLUG}/reference"
STARTER_BUILD = f"{STARTER_BUILDS}/{PROJECT_SLUG}"
LEVEL_TESTS = ("tests/test_level_1.py::test_ex1", "tests/test_level_2.py::test_ex2")
OLD_NS = 1_000_000_000


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return repository_root(tmp_path, PROJECT_PROBLEMS)


@pytest.fixture
def process(root: Path) -> ScriptedBuilds:
    problem = make_environment(root).problems.load(PROJECT_SLUG)
    return scripted_builds(problem, passing=LEVEL_TESTS)


@pytest.fixture
def environment(root: Path, process: ScriptedBuilds) -> Environment:
    toolchains = project_toolchains(FakeTestGenerator())
    return make_environment(root, toolchains=toolchains, runner_process=process)


def verify(environment: Environment, **fields: object) -> ProblemVerification:
    request = VerifyRequest(**{"slugs": (PROJECT_SLUG,), **fields})  # type: ignore[arg-type]
    [problem] = verify_content(environment, request, lambda _line: None).problems
    return problem


def coverage(environment: Environment, language: Language) -> tuple[int, int]:
    request = VerifyRequest(slugs=(PROJECT_SLUG,), static_only=True)
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


def graded_levels(build: ScriptedProjectProcess) -> list[tuple[str, ...]]:
    return [
        tuple(method.name for method in job.signature.methods)
        for job in build.gradings
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
        f"# level 1 of {PROJECT_SLUG}\ntest ex1\n",
        f"# level 2 of {PROJECT_SLUG}\ntest ex2\n",
    )


def test_the_starter_build_is_the_starter_with_level_ones_tests(environment, root):
    verify(environment)
    starter = root / "problems" / BANK_PROJECT / "starter" / "bank" / "bank.py"
    files = build_files(root, STARTER_BUILD)
    assert (files["bank/bank.py"], "tests/test_level_1.py" in files) == (starter.read_text(), True)


def test_the_starter_build_has_no_later_levels_tests(environment, root):
    verify(environment)
    assert "tests/test_level_2.py" not in build_files(root, STARTER_BUILD)


@pytest.mark.parametrize("build", [REFERENCE_BUILD, STARTER_BUILD])
def test_a_build_removes_a_file_the_problem_no_longer_has(environment, root, build):
    stale = root / build / "bank" / "removed_helper.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("# left by an earlier build\n")
    verify(environment)
    assert "bank/removed_helper.py" not in build_files(root, build)


@pytest.mark.parametrize("build", [REFERENCE_BUILD, STARTER_BUILD])
def test_a_build_rewrites_a_file_that_differs_from_the_problems(environment, root, build):
    verify(environment)
    readme = root / build / "README.md"
    readme.write_text("# edited since\n")
    verify(environment)
    starter = root / "problems" / BANK_PROJECT / "starter" / "README.md"
    assert readme.read_text() == starter.read_text()


@pytest.mark.parametrize("path", ["README.md", "tests/test_level_1.py"])
@pytest.mark.parametrize("build", [REFERENCE_BUILD, STARTER_BUILD])
def test_a_build_keeps_the_timestamp_of_an_unchanged_file(environment, root, build, path):
    """Build tools that compare timestamps (Gradle, Cargo) then skip the file's work."""
    verify(environment)
    unchanged = root / build / path
    os.utime(unchanged, ns=(OLD_NS, OLD_NS))
    verify(environment)
    assert unchanged.stat().st_mtime_ns == OLD_NS


@pytest.mark.parametrize(
    "output",
    [
        "build/classes/java/main/bank/Bank.class",
        ".gradle/configuration-cache/entry.bin",
        ".kotlin/sessions/daemon.salive",
        "target/debug/libbank.rlib",
    ],
)
@pytest.mark.parametrize("build", [REFERENCE_BUILD, STARTER_BUILD])
def test_a_build_keeps_what_the_build_tools_wrote(environment, root, build, output):
    cached = root / build / output
    cached.parent.mkdir(parents=True)
    cached.write_text("cached\n")
    verify(environment)
    assert cached.read_text() == "cached\n"


@pytest.mark.parametrize("build", [REFERENCE_BUILD, STARTER_BUILD])
def test_a_build_never_deletes_through_a_link(environment, root, build):
    outside = root / "elsewhere"
    outside.mkdir()
    (outside / "kept.txt").write_text("not a build file\n")
    link = root / build / ".venv"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    verify(environment)
    assert (outside / "kept.txt").is_file()


def test_verify_needs_the_project_test_generator(environment):
    toolchains = replace(environment.toolchains, project_test_generators={})
    with pytest.raises(LanguageNotSetUpError, match="project test generator"):
        verify(replace(environment, toolchains=toolchains))


@pytest.fixture
def inexpressible_case(monkeypatch):
    """`level_tests` refuses a case, as it does one a generated test cannot express."""

    def refuse(*_: object) -> object:
        raise ValueError("a generated test cannot compare getBalance with checker")

    monkeypatch.setattr(verify_projects, "level_tests", refuse)


def test_a_case_without_a_generated_test_fails_the_build(environment, inexpressible_case):
    [result] = verify(environment).languages
    assert result.approaches[0].failures == (
        "does not build: a generated test cannot compare getBalance with checker",
    )


def test_a_reference_that_does_not_build_runs_nothing(environment, process, inexpressible_case):
    problem = verify(environment)
    builds = (process.starter, process.reference)
    jobs_run = [job for build in builds for job in (*build.gradings, *build.suites)]
    assert (problem.suite, jobs_run) == (
        SuiteCheck(0, 0, ("not run: the reference does not build",)),
        [],
    )


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
    process.reference.tests = (*process.reference.tests, skipped)
    assert verify(environment).suite == SuiteCheck(3, 3)


def test_the_reference_is_graded_at_its_last_level(environment, process):
    verify(environment)
    assert graded_levels(process.reference) == [("createAccount", "deposit", "transfer")]


def test_the_reference_suite_runs_every_levels_tests(environment, process):
    verify(environment)
    [job] = process.reference.suites
    assert job.exclude == ()


def test_the_starter_is_graded_at_level_one(environment, process):
    verify(environment)
    assert graded_levels(process.starter) == [("createAccount", "deposit")]


def test_every_project_job_gets_a_runner_of_its_own(environment, process):
    verify(environment)
    requests = [*process.starter.requests, *process.reference.requests]
    assert [len(request.jobs) for request in requests] == [1, 1]


def test_oracle_and_ladder_do_not_apply_to_a_project(environment):
    problem = verify(environment, oracle_cases=20, ladder=True)
    assert problem.skipped == (SkippedCheck.ORACLE, SkippedCheck.LADDER)


def test_another_language_leaves_the_project_out(environment):
    request = VerifyRequest(slugs=(PROJECT_SLUG,), language=Language.TYPESCRIPT)
    assert verify_content(environment, request, lambda _line: None).problems == ()


# D3: the reference


def test_a_failing_case_names_its_level(environment, process):
    correct = process.reference.answer
    process.reference.answer = lambda job, case: (
        Returned([None, True, 0], 1_000) if case.id == "h3" else correct(job, case)
    )
    [result] = verify(environment).languages
    [failure] = result.approaches[0].failures
    assert failure.startswith("level 2 h3 FAIL: expected [null, true, -1], got [null, true, 0]")


def test_a_reference_that_does_not_load_fails(environment, process):
    process.reference.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    [result] = verify(environment).languages
    assert result.approaches[0].failures == (
        "does not load: SymbolNotFound: bank.bank has no class Bank",
    )


def test_a_reference_that_does_not_compile_names_the_first_compiler_line(environment, process):
    lines = ("src/main/java/bank/Bank.java:3: error: ';' expected", "        int x")
    process.reference.load_error = compile_error(BuildFailed(lines))
    [result] = verify(environment).languages
    assert result.approaches[0].failures == (
        "does not load: CompileError: the project does not compile: "
        "src/main/java/bank/Bank.java:3: error: ';' expected",
    )


# D9: the reference's suite


def test_a_failing_test_fails_the_suite(environment, process):
    failed = SuiteTest(LEVEL_TESTS[1], AssertionFailed("assert -1 == 300\n where ...", 1_000))
    process.reference.tests = (SuiteTest(LEVEL_TESTS[0], Passed(1_000)), failed)
    problem = verify(environment)
    assert (problem.suite, problem.passed) == (
        SuiteCheck(1, 2, (f"{LEVEL_TESTS[1]} failed: assert -1 == 300",)),
        False,
    )


def test_a_test_that_raises_names_the_exception(environment, process):
    raised = SuiteTest(LEVEL_TESTS[0], Raised(UserError("KeyError", "'ivy'"), 1_000))
    process.reference.tests = (raised,)
    assert verify(environment).suite == SuiteCheck(
        0, 1, (f"{LEVEL_TESTS[0]} error: KeyError: 'ivy'",)
    )


def test_a_suite_that_does_not_run_fails(environment, process):
    usage = UserError("UsageError", "unrecognized arguments: --bad")
    process.reference.tests = ()
    process.reference.suite_load_error = usage
    assert verify(environment).suite == SuiteCheck(
        0, 0, ("does not run: UsageError: unrecognized arguments: --bad",)
    )


def test_a_suite_that_stopped_early_fails(environment, process):
    crashed = SuiteTest(LEVEL_TESTS[0], Crashed(1))
    process.reference.tests = (crashed,)
    process.reference.stopped_early = "the runner crashed 3 times"
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
    process.starter.load_error = UserError("SyntaxError", "invalid syntax (bank.py, line 3)")
    [result] = verify(environment).languages
    assert result.problems == (
        "starter does not load: SyntaxError: invalid syntax (bank.py, line 3)",
    )


def test_a_starter_that_crashes_the_runner_fails(environment, process):
    process.starter.answer = lambda job, case: Crashed(1)
    [result] = verify(environment).languages
    assert result.problems == ("starter runner crashed with exit code 1",)


def test_a_starter_whose_cases_fail_still_loads(environment):
    [result] = verify(environment).languages
    assert result.problems == ()


def test_a_starter_suite_that_crashes_the_runner_fails(environment, process):
    process.starter.tests = (SuiteTest(LEVEL_TESTS[0], Crashed(1)),)
    [result] = verify(environment).languages
    assert result.problems == (f"starter suite: {LEVEL_TESTS[0]} runner crashed with exit code 1",)


def test_a_starter_suite_that_does_not_run_fails(environment, process):
    usage = UserError("UsageError", "no such option")
    process.starter.tests = ()
    process.starter.suite_load_error = usage
    [result] = verify(environment).languages
    assert result.problems == ("starter suite does not run: UsageError: no such option",)


def test_the_starter_suite_runs_in_the_starters_build(environment, process, root):
    verify(environment)
    [job] = process.starter.suites
    assert job.root == str(root / STARTER_BUILD)


def test_the_suite_runs_in_the_reference_build(environment, process, root):
    verify(environment)
    [job] = process.reference.suites
    assert job.root == str(root / REFERENCE_BUILD)


def test_a_project_suite_is_prepared_as_a_suite(environment, root):
    runner = FakeProjectRunner()
    toolchains = project_toolchains(FakeTestGenerator(), runner)
    verify(replace(environment, toolchains=toolchains))
    assert ProjectSuite(root / REFERENCE_BUILD) in runner.scopes


# D10: the virtual clock

MS = 1_000_000


@pytest.fixture
def on_the_clock(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The fixture project on the virtual clock, whose runner is the Python one that the fakes
    stand in for; its hang guard is one second."""
    meta = root / "problems" / BANK_PROJECT / "meta.yaml"
    text = meta.read_text()
    text = text.replace("  entry: bank.bank\n", "  entry: bank.bank\n  clock: virtual\n")
    meta.write_text(text.replace("comparator:", "limits: {hang_guard_ms: 1000}\ncomparator:"))
    monkeypatch.setattr(virtual_clock, "GRADED_CLOCK_LANGUAGES", frozenset({Language.PYTHON}))


def vary(process: ScriptedBuilds, case_id: str, *, in_call: int, output: JsonValue) -> None:
    """The reference answers `case_id` with `output` the `in_call`th time it is asked, counting
    from 1, and correctly otherwise."""
    correct = process.reference.answer
    asked: list[str] = []

    def answer(job, case):
        if case.id == case_id:
            asked.append(case_id)
            if len(asked) == in_call:
                return Returned(output, 1_000)
        return correct(job, case)

    process.reference.answer = answer


def slow(process: ScriptedBuilds, case_id: str, milliseconds: int) -> None:
    correct = process.reference.answer

    def answer(job, case):
        found = correct(job, case)
        if case.id == case_id and isinstance(found, Returned):
            return Returned(found.output, milliseconds * MS)
        return found

    process.reference.answer = answer


def determined(problem: ProblemVerification) -> DeterminismVerdict:
    assert problem.determinism is not None
    return problem.determinism


def determinism(environment: Environment) -> DeterminismVerdict:
    return determined(verify(environment))


def test_a_project_on_the_real_clock_has_no_determinism_check(environment, process):
    problem = verify(environment)
    assert (problem.determinism, len(process.reference.gradings)) == (None, 1)


def test_the_reference_of_a_virtual_clock_project_is_graded_ten_more_times(
    environment, process, on_the_clock
):
    verify(environment)
    assert len(process.reference.gradings) == 1 + DETERMINISM_RUNS


def test_the_determinism_runs_order_ties_by_seeds_0_to_9(environment, process, on_the_clock):
    """The first grading is D3's, with the seed of `cstudy submit`."""
    verify(environment)
    assert [job.clock_seed for job in process.reference.gradings] == [0, *range(DETERMINISM_RUNS)]


def test_every_determinism_run_gets_a_runner_of_its_own(environment, process, on_the_clock):
    verify(environment)
    assert [len(request.jobs) for request in process.reference.requests] == [1] * 11


def test_every_determinism_run_grades_every_case_of_every_level(environment, process, on_the_clock):
    verify(environment)
    last = process.reference.gradings[-1]
    assert [case.id for case in last.cases] == [
        case.id for case in process.reference.gradings[0].cases
    ]


def test_runs_that_agree_pass_d10(environment, on_the_clock):
    problem = verify(environment)
    verdict = determined(problem)
    assert (problem.passed, verdict.passed, verdict.agreeing) == (True, True, DETERMINISM_RUNS)


def test_d10_counts_its_runs_and_reports_the_slowest_share_of_the_hang_guard(
    environment, process, on_the_clock
):
    slow(process, "h1", 100)
    verdict = determinism(environment)
    assert (verdict.runs, verdict.slowest_share) == (10, pytest.approx(0.1))


def test_a_case_that_gives_another_output_in_one_run_fails_the_problem(
    environment, process, on_the_clock
):
    vary(process, "h3", in_call=5, output=[None, True, 0])
    problem = verify(environment)
    verdict = determined(problem)
    assert (problem.passed, verdict.agreeing, verdict.failures) == (
        False,
        9,
        (
            "level 2 h3: outputs differ between runs: returned [null, true, -1] in 9 of 10 "
            "runs, returned [null, true, 0] in 1 of 10 runs",
        ),
    )


def test_a_run_over_a_quarter_of_the_hang_guard_fails_the_problem(
    environment, process, on_the_clock
):
    slow(process, "ex1", 300)
    problem = verify(environment)
    assert (problem.passed, determined(problem).failures) == (
        False,
        (
            "level 1 ex1: the slowest run took 300 ms, 30% of its hang guard of 1000 ms; "
            "at most 25%",
        ),
    )


def test_a_case_with_a_hang_guard_of_its_own_is_held_to_it(
    environment, process, root, on_the_clock
):
    tests = root / "problems" / BANK_PROJECT / "tests.json"
    tests.write_text(
        tests.read_text().replace('"id": "ex1",', '"id": "ex1", "hang_guard_ms": 4000,')
    )
    slow(process, "ex1", 300)
    assert determinism(environment).passed


def test_d10_does_not_run_when_the_reference_does_not_load(environment, process, on_the_clock):
    process.reference.load_error = UserError("SymbolNotFound", "bank.bank has no class Bank")
    problem = verify(environment)
    assert (problem.determinism, len(process.reference.gradings)) == (None, 1)


def test_d10_does_not_run_when_the_reference_does_not_build(
    environment, process, on_the_clock, inexpressible_case
):
    assert verify(environment).determinism is None


def test_d10_does_not_run_with_static_checks_only(environment, process, on_the_clock):
    problem = verify(environment, static_only=True)
    assert (problem.determinism, process.reference.gradings) == (None, [])
