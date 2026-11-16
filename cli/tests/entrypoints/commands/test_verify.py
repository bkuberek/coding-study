import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.application.case_materialization import EXPECTED_VALUES_NOTICE
from coding_study.application.reference_runs import (
    ApproachResult,
    LanguageResult,
    LanguageVerifier,
)
from coding_study.application.verify_content import Coverage, ProblemVerification, VerifyReport
from coding_study.application.verify_projects import SuiteCheck
from coding_study.domain.clock_determinism import DeterminismVerdict
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import verify
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import FixedChangedFiles, make_environment, repository_root, without
from tests.helpers import REPOSITORY_ROOT

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"
PY = Language.PYTHON


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
    return environment


@dataclass(frozen=True)
class Run:
    exit_code: int
    report: list[str]
    """Output lines without progress notices."""


def invoke(*arguments: str) -> Run:
    result = runner.invoke(cli.app, ["verify", *arguments])
    lines = [line for line in result.output.splitlines() if line != EXPECTED_VALUES_NOTICE]
    return Run(result.exit_code, lines)


def test_static_report(environment):
    assert invoke("--static").report == [
        "lru-cache         static ok      draft (coverage 1/6)",
        "  warning: problems/lru-cache/solutions/explanation.md: "
        'approach ordered-dict: no "### Language notes"',
        "two-sum           static ok",
        "",
        "coverage  python 2/2 · typescript 0/2 · java 0/2 · kotlin 0/2 · go 0/2 · rust 0/2",
        "result    0 failed · 2 passed",
    ]


def test_passing_static_check_exits_0(environment):
    assert invoke("--static").exit_code == 0


def test_dynamic_report(environment):
    assert invoke("--lang", "python", "two-sum", "--oracle", "--oracle-cases", "10").report == [
        "two-sum           static ok · py 2/2 ok · oracle 10/10",
        "",
        "coverage  python 1/1",
        "result    0 failed · 1 passed",
    ]


def test_oracle_without_a_generator_is_not_applicable(environment):
    assert invoke("--lang", "python", "lru-cache", "--oracle").report[0] == (
        "lru-cache         static ok · py 1/1 ok · oracle n/a      draft (coverage 1/6)"
    )


def test_oracle_without_a_generator_passes(environment):
    assert invoke("--lang", "python", "lru-cache", "--oracle").exit_code == ExitCode.SUCCESS


def test_static_failures_exit_5(environment):
    problem_md = environment.root / "problems/two-sum/problem.md"
    problem_md.write_text(problem_md.read_text().replace("## Constraints", "## Limits"))
    result = invoke("--static", "two-sum")
    assert (result.exit_code, result.report[0]) == (
        ExitCode.CONTENT_ERROR,
        'two-sum           FAIL static: problems/two-sum/problem.md: missing "## Constraints"',
    )


def test_failing_reference_exits_1(environment):
    solution = environment.root / "problems/two-sum/solutions/brute-force.py"
    solution.write_text(solution.read_text().replace("return [i, j]", "return [j, j]"))
    result = invoke("--lang", "python", "two-sum")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "two-sum           static ok · py 1/2 FAIL",
            "  py brute-force: ex1 FAIL: expected [1, 2], got [2, 2]",
        ],
    )


def runner_that_cannot_start_for(monkeypatch, slug: str) -> None:
    stub_problem = LanguageVerifier.stub_problem

    def start(self, sample):
        if self._meta.slug == slug:
            raise RunnerStartError("cannot start runner py: Text file busy")
        return stub_problem(self, sample)

    monkeypatch.setattr(LanguageVerifier, "stub_problem", start)


def test_a_runner_that_cannot_start_fails_its_problem_and_the_run_goes_on(environment, monkeypatch):
    runner_that_cannot_start_for(monkeypatch, "two-sum")
    result = invoke("--lang", "python")
    assert (result.exit_code, result.report[2:4]) == (
        ExitCode.FAILURES,
        [
            "two-sum           static ok · py FAIL",
            "  py cannot start runner py: Text file busy",
        ],
    )
    assert result.report[0].startswith("lru-cache         static ok · py 1/1 ok")


def test_require_ready_lists_what_is_missing(environment):
    lines = invoke("--static", "--require-ready", "two-sum").report
    assert lines[:2] == [
        "two-sum           static ok · not ready",
        "  not ready: no optimal reference in typescript, java, kotlin, go, rust",
    ]


def test_oracle_cases_need_oracle(environment):
    assert invoke("--oracle-cases", "5").exit_code == ExitCode.USAGE_ERROR


def test_unknown_problem(environment):
    assert invoke("three-sum").exit_code == ExitCode.USAGE_ERROR


def changed_files(monkeypatch, *paths: str) -> None:
    monkeypatch.setattr(verify, "GitChangedFiles", lambda _root: FixedChangedFiles(*paths))


def test_changed_verifies_only_the_changed_problems(environment, monkeypatch):
    changed_files(monkeypatch, "problems/lru-cache/tests.json", "README.md")
    report = invoke("--changed", "--static").report
    assert (report[0].split()[0], report[-1]) == ("lru-cache", "result    0 failed · 1 passed")


def test_changed_without_changed_problems_verifies_nothing(environment, monkeypatch):
    changed_files(monkeypatch, "README.md")
    result = invoke("--changed")
    assert (result.exit_code, result.report) == (0, ["no problems changed relative to main"])


def test_changed_reports_a_new_misnamed_directory(environment, monkeypatch):
    (environment.content_root / "problems" / "0099-foo").mkdir()
    changed_files(monkeypatch, "problems/0099-foo/meta.yaml")
    result = invoke("--changed", "--static")
    assert (result.exit_code, result.report[0], result.report[-1]) == (
        ExitCode.CONTENT_ERROR,
        "0099-foo          FAIL static: problems/0099-foo: the name is not a slug, so no problem "
        "loads from it; from the content root run `mv problems/0099-foo problems/foo`",
        "result    1 failed · 0 passed",
    )


def test_changed_reports_a_misnamed_directory_beside_the_changed_problems(environment, monkeypatch):
    (environment.content_root / "problems" / "0099-foo").mkdir()
    changed_files(monkeypatch, "problems/lru-cache/tests.json", "problems/0099-foo/meta.yaml")
    report = invoke("--changed", "--static").report
    assert [line.split()[0] for line in report[:1]] == ["lru-cache"]
    assert report[-1] == "result    1 failed · 1 passed"


def test_changed_with_slugs_is_a_usage_error(environment, monkeypatch):
    changed_files(monkeypatch)
    assert invoke("--changed", "two-sum").exit_code == ExitCode.USAGE_ERROR


def test_changed_with_conformance_is_a_usage_error(environment, monkeypatch):
    changed_files(monkeypatch)
    assert invoke("--changed", "--conformance").exit_code == ExitCode.USAGE_ERROR


@pytest.fixture
def conformance_root(tmp_path, monkeypatch):
    root = repository_root(tmp_path, PRACTICE)
    fixture = root / "runners" / "conformance" / "conformance-function"
    shutil.copytree(CONFORMANCE / fixture.name, fixture)
    (fixture / "solutions").mkdir(exist_ok=True)
    (fixture / "solutions" / "identity.py").write_text(
        "def echo_http_codes(first_value, second_value, third_flag):\n    return first_value\n"
    )
    expectations = json.loads((CONFORMANCE / "expectations.json").read_text())
    expectations["expectations"] = [
        entry
        for entry in expectations["expectations"]
        if entry["problem"] == "conformance-function"
    ]
    (fixture.parent / "expectations.json").write_text(json.dumps(expectations))
    environment = e2e_environment(root)
    monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
    return root


def test_conformance_report(conformance_root):
    assert invoke("--conformance", "--lang", "python").report == [
        "conformance-function  py ok",
        "",
        "result    0 failed · 1 passed",
    ]


def test_conformance_failures_exit_1(conformance_root):
    solution = conformance_root / "runners/conformance/conformance-function/solutions/identity.py"
    solution.write_text(
        "def echo_http_codes(first_value, second_value, third_flag):\n    return []\n"
    )
    result = invoke("--conformance", "--lang", "python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "conformance-function  py FAIL",
            "  py identity: values: expected pass, got FAIL",
        ],
    )


OTHER_LANGUAGES = ("--skip-lang", "java", "--skip-lang", "kotlin", "--skip-lang", "go")


def lacking(monkeypatch, *programs: str) -> None:
    """The machine has none of `programs`."""
    load = verify.load_environment
    monkeypatch.setattr(
        verify, "load_environment", lambda *a: replace(load(*a), toolchain_check=without(*programs))
    )


def test_a_missing_toolchain_skips_its_language_and_the_others_run(conformance_root, monkeypatch):
    lacking(monkeypatch, "node", "cargo")
    result = invoke("--conformance", *OTHER_LANGUAGES)
    assert (result.exit_code, result.report) == (
        ExitCode.SUCCESS,
        [
            "conformance-function  py ok · ts skipped · rs skipped",
            "  skipped  typescript: node was not found on PATH",
            "  skipped  rust: cargo was not found on PATH",
            "",
            "result    0 failed · 1 passed",
        ],
    )


def test_a_failure_still_fails_beside_a_skipped_language(conformance_root, monkeypatch):
    lacking(monkeypatch, "cargo")
    solution = conformance_root / "runners/conformance/conformance-function/solutions/identity.py"
    solution.write_text("def echo_http_codes(a, b, c):\n    return []\n")
    assert invoke("--conformance", *OTHER_LANGUAGES, "--skip-lang", "typescript").exit_code == (
        ExitCode.FAILURES
    )


def test_the_ready_gate_counts_a_missing_toolchain_as_not_passed(conformance_root, monkeypatch):
    lacking(monkeypatch, "cargo")
    result = invoke(
        "--conformance", *OTHER_LANGUAGES, "--skip-lang", "typescript", "--require-ready"
    )
    assert (result.exit_code, result.report[:3]) == (
        ExitCode.FAILURES,
        [
            "conformance-function  py ok · rs skipped",
            "  not ready: rust skipped: cargo was not found on PATH",
            "  skipped  rust: cargo was not found on PATH",
        ],
    )


def test_skip_lang_leaves_a_language_out_without_counting_it(conformance_root, monkeypatch):
    lacking(monkeypatch, "cargo")
    result = invoke(
        "--conformance",
        *OTHER_LANGUAGES,
        "--skip-lang",
        "typescript",
        "--skip-lang",
        "rust",
        "--require-ready",
    )
    assert (result.exit_code, result.report) == (
        ExitCode.SUCCESS,
        ["conformance-function  py ok", "", "result    0 failed · 1 passed"],
    )


def test_the_content_gate_names_a_skipped_language_and_still_exits_0(environment, monkeypatch):
    lacking(monkeypatch, "node")
    result = invoke("two-sum", *OTHER_LANGUAGES, "--skip-lang", "rust")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.SUCCESS,
        [
            "two-sum           static ok · py 2/2 ok · ts skipped",
            "  skipped  typescript: node was not found on PATH",
        ],
    )


def test_the_content_gate_with_require_ready_exits_1_and_names_the_language(
    environment, monkeypatch
):
    lacking(monkeypatch, "node")
    result = invoke("two-sum", *OTHER_LANGUAGES, "--skip-lang", "rust", "--require-ready")
    assert result.exit_code == ExitCode.FAILURES
    assert "  not ready: typescript skipped: node was not found on PATH" in result.report


def test_the_content_gate_does_not_name_a_language_that_skip_lang_left_out(
    environment, monkeypatch
):
    lacking(monkeypatch, "node")
    result = invoke("two-sum", *OTHER_LANGUAGES, "--skip-lang", "rust", "--skip-lang", "typescript")
    assert (result.exit_code, result.report[0]) == (
        ExitCode.SUCCESS,
        "two-sum           static ok · py 2/2 ok",
    )


def test_skip_lang_leaves_the_language_out_of_the_coverage_line(environment):
    result = invoke("--static", "two-sum", *OTHER_LANGUAGES, "--skip-lang", "rust")
    assert "coverage  python 1/1 · typescript 0/1" in result.report


def test_skip_lang_and_lang_for_one_language_are_a_usage_error(conformance_root):
    result = invoke("--conformance", "--lang", "rust", "--skip-lang", "rust")
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_skip_lang_with_another_language_than_lang_is_allowed(conformance_root):
    assert invoke("--conformance", "--lang", "python", "--skip-lang", "rust").exit_code == 0


def test_skip_lang_names_a_language(conformance_root):
    assert invoke("--conformance", "--skip-lang", "cobol").exit_code == ExitCode.USAGE_ERROR


PROJECT_DIRECTORY = "problems/bank-project-python"


def project_report(
    languages: tuple[LanguageResult, ...],
    suite: SuiteCheck,
    determinism: DeterminismVerdict | None = None,
) -> VerifyReport:
    meta = FsProblemRepository(REPOSITORY_ROOT).load("bank-project-python").meta
    problem = ProblemVerification(
        PROJECT_DIRECTORY,
        meta,
        languages=languages,
        suite=suite,
        determinism=determinism,
        reference_languages=(PY,),
    )
    return VerifyReport((problem,), (Coverage(PY, 1 if problem.passed else 0, 1),))


@pytest.fixture
def reported(tmp_path, monkeypatch):
    """Prints the report it is given instead of verifying."""
    environment = make_environment(repository_root(tmp_path, PRACTICE))

    def report_with(report: VerifyReport) -> None:
        monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
        monkeypatch.setattr(verify, "verify_content", lambda *_: report)

    return report_with


def test_a_project_line_shows_its_language_and_its_suite(reported):
    reported(
        project_report((LanguageResult(PY, (ApproachResult("reference"),)),), SuiteCheck(14, 14))
    )
    assert invoke("bank-project-python").report[0] == (
        "bank-project-...  static ok · py 1/1 ok · suite 14/14"
    )


def test_a_failing_suite_lists_its_failures_and_exits_1(reported):
    failure = "tests/test_level_2.py::test_ex1 failed: assert -1 == 5"
    passing = (LanguageResult(PY, (ApproachResult("reference"),)),)
    reported(project_report(passing, SuiteCheck(13, 14, (failure,))))
    result = invoke("bank-project-python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        ["bank-project-...  static ok · py 1/1 ok · suite 13/14", f"  suite: {failure}"],
    )


def test_a_virtual_clock_project_line_shows_its_agreeing_runs_and_its_slowest_share(reported):
    passing = (LanguageResult(PY, (ApproachResult("reference"),)),)
    reported(project_report(passing, SuiteCheck(14, 14), DeterminismVerdict(10, 10, 0.0021)))
    assert invoke("bank-project-python").report[0] == (
        "bank-project-...  static ok · py 1/1 ok · suite 14/14 · clock 10/10 · slowest 0.2%"
    )


def test_a_clock_without_a_measured_run_shows_no_share(reported):
    passing = (LanguageResult(PY, (ApproachResult("reference"),)),)
    reported(project_report(passing, SuiteCheck(14, 14), DeterminismVerdict(10, 10, None)))
    assert invoke("bank-project-python").report[0].endswith("suite 14/14 · clock 10/10")


def test_runs_that_differ_list_their_failures_and_exit_1(reported):
    failure = "level 2 h3: outputs differ between runs: returned 1 in 9 of 10 runs, returned 2 in 1"
    passing = (LanguageResult(PY, (ApproachResult("reference"),)),)
    reported(
        project_report(passing, SuiteCheck(14, 14), DeterminismVerdict(10, 9, 0.01, (failure,)))
    )
    result = invoke("bank-project-python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "bank-project-...  static ok · py 1/1 ok · suite 14/14 · clock 9/10 · slowest 1.0%",
            f"  clock: {failure}",
        ],
    )


def test_a_starter_that_does_not_load_is_a_language_problem(reported):
    problem = "starter does not load: SyntaxError: invalid syntax"
    languages = (LanguageResult(PY, (ApproachResult("reference"),), (problem,)),)
    reported(project_report(languages, SuiteCheck(14, 14)))
    assert invoke("bank-project-python").report[:2] == [
        "bank-project-...  static ok · py 1/1 FAIL · suite 14/14",
        f"  py {problem}",
    ]


SKIP_REASON = "runs on JDK 24 to 26; JAVA_HOME selects JDK 21"
JVM_SKIPS = (
    LanguageResult(Language.JAVA, skipped=SKIP_REASON),
    LanguageResult(Language.KOTLIN, skipped=SKIP_REASON),
)


def test_skipped_languages_show_on_the_line_and_in_a_skipped_line(reported):
    ran = LanguageResult(PY, (ApproachResult("reference"),))
    reported(project_report((ran, *JVM_SKIPS), SuiteCheck(14, 14)))
    result = invoke("bank-project-python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.SUCCESS,
        [
            "bank-project-...  static ok · py 1/1 ok · java skipped · kt skipped · suite 14/14",
            f"  skipped  java, kotlin: {SKIP_REASON}",
        ],
    )


def test_a_skip_is_not_a_failure(reported):
    reported(project_report(JVM_SKIPS, SuiteCheck(0, 0)))
    assert invoke("bank-project-python").exit_code == ExitCode.SUCCESS


def test_the_ready_gate_lists_a_skip_as_not_ready(reported):
    problem = ProblemVerification(
        PROJECT_DIRECTORY,
        FsProblemRepository(REPOSITORY_ROOT).load("bank-project-python").meta,
        languages=JVM_SKIPS,
        ready_errors=(f"java, kotlin skipped: {SKIP_REASON}",),
    )
    reported(VerifyReport((problem,), (Coverage(PY, 0, 1),)))
    result = invoke("bank-project-python", "--require-ready")
    assert (result.exit_code, result.report[:3]) == (
        ExitCode.FAILURES,
        [
            "bank-project-...  static ok · java skipped · kt skipped · not ready",
            f"  skipped  java, kotlin: {SKIP_REASON}",
            f"  not ready: java, kotlin skipped: {SKIP_REASON}",
        ],
    )


def test_a_runner_that_cannot_start_fails_its_fixture_in_conformance(conformance_root, monkeypatch):
    runner_that_cannot_start_for(monkeypatch, "conformance-function")
    result = invoke("--conformance", "--lang", "python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "conformance-function  py FAIL",
            "  py cannot start runner py: Text file busy",
        ],
    )
