import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.application.case_materialization import EXPECTED_VALUES_NOTICE
from coding_study.application.reference_runs import ApproachResult, LanguageResult
from coding_study.application.verify_content import Coverage, ProblemVerification, VerifyReport
from coding_study.application.verify_projects import SuiteCheck
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import verify
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import FixedChangedFiles, make_environment, repository_root
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
        "0001-two-sum      static ok",
        "0002-lru-cache    static ok      draft (coverage 1/6)",
        "  warning: problems/0002-lru-cache/solutions/explanation.md: "
        'approach ordered-dict: no "### Language notes"',
        "",
        "coverage  python 2/2 · typescript 0/2 · java 0/2 · kotlin 0/2 · go 0/2 · rust 0/2",
        "result    0 failed · 2 passed",
    ]


def test_passing_static_check_exits_0(environment):
    assert invoke("--static").exit_code == 0


def test_dynamic_report(environment):
    assert invoke("--lang", "python", "two-sum", "--oracle", "--oracle-cases", "10").report == [
        "0001-two-sum      static ok · py 2/2 ok · oracle 10/10",
        "",
        "coverage  python 1/1",
        "result    0 failed · 1 passed",
    ]


def test_oracle_without_a_generator_is_not_applicable(environment):
    assert invoke("--lang", "python", "lru-cache", "--oracle").report[0] == (
        "0002-lru-cache    static ok · py 1/1 ok · oracle n/a      draft (coverage 1/6)"
    )


def test_oracle_without_a_generator_passes(environment):
    assert invoke("--lang", "python", "lru-cache", "--oracle").exit_code == ExitCode.SUCCESS


def test_static_failures_exit_5(environment):
    problem_md = environment.root / "problems/0001-two-sum/problem.md"
    problem_md.write_text(problem_md.read_text().replace("## Constraints", "## Limits"))
    result = invoke("--static", "two-sum")
    assert (result.exit_code, result.report[0]) == (
        ExitCode.CONTENT_ERROR,
        '0001-two-sum      FAIL static: problems/0001-two-sum/problem.md: missing "## Constraints"',
    )


def test_failing_reference_exits_1(environment):
    solution = environment.root / "problems/0001-two-sum/solutions/brute-force.py"
    solution.write_text(solution.read_text().replace("return [i, j]", "return [j, j]"))
    result = invoke("--lang", "python", "two-sum")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "0001-two-sum      static ok · py 1/2 FAIL",
            "  py brute-force: ex1 FAIL: expected [1, 2], got [2, 2]",
        ],
    )


def test_require_ready_lists_what_is_missing(environment):
    lines = invoke("--static", "--require-ready", "two-sum").report
    assert lines[:2] == [
        "0001-two-sum      static ok · not ready",
        "  not ready: no optimal reference in typescript, java, kotlin, go, rust",
    ]


def test_oracle_cases_need_oracle(environment):
    assert invoke("--oracle-cases", "5").exit_code == ExitCode.USAGE_ERROR


def test_unknown_problem(environment):
    assert invoke("three-sum").exit_code == ExitCode.USAGE_ERROR


def changed_files(monkeypatch, *paths: str) -> None:
    monkeypatch.setattr(verify, "GitChangedFiles", lambda _root: FixedChangedFiles(*paths))


def test_changed_verifies_only_the_changed_problems(environment, monkeypatch):
    changed_files(monkeypatch, "problems/0002-lru-cache/tests.json", "README.md")
    report = invoke("--changed", "--static").report
    assert (report[0].split()[0], report[-1]) == ("0002-lru-cache", "result    0 failed · 1 passed")


def test_changed_without_changed_problems_verifies_nothing(environment, monkeypatch):
    changed_files(monkeypatch, "README.md")
    result = invoke("--changed")
    assert (result.exit_code, result.report) == (0, ["no problems changed relative to main"])


def test_changed_with_slugs_is_a_usage_error(environment, monkeypatch):
    changed_files(monkeypatch)
    assert invoke("--changed", "two-sum").exit_code == ExitCode.USAGE_ERROR


def test_changed_with_conformance_is_a_usage_error(environment, monkeypatch):
    changed_files(monkeypatch)
    assert invoke("--changed", "--conformance").exit_code == ExitCode.USAGE_ERROR


@pytest.fixture
def conformance_root(tmp_path, monkeypatch):
    root = repository_root(tmp_path, PRACTICE)
    fixture = root / "runners" / "conformance" / "9002-conformance-function"
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
        "9002-conformance-function  py ok",
        "",
        "result    0 failed · 1 passed",
    ]


def test_conformance_failures_exit_1(conformance_root):
    solution = (
        conformance_root / "runners/conformance/9002-conformance-function/solutions/identity.py"
    )
    solution.write_text(
        "def echo_http_codes(first_value, second_value, third_flag):\n    return []\n"
    )
    result = invoke("--conformance", "--lang", "python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        [
            "9002-conformance-function  py FAIL",
            "  py identity: values: expected pass, got FAIL",
        ],
    )


PROJECT_DIRECTORY = "problems/0249-bank-project-python"


def project_report(languages: tuple[LanguageResult, ...], suite: SuiteCheck) -> VerifyReport:
    meta = FsProblemRepository(REPOSITORY_ROOT).load("bank-project-python").meta
    problem = ProblemVerification(
        PROJECT_DIRECTORY, meta, languages=languages, suite=suite, reference_languages=(PY,)
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
        "0249-bank-pro...  static ok · py 1/1 ok · suite 14/14"
    )


def test_a_failing_suite_lists_its_failures_and_exits_1(reported):
    failure = "tests/test_level_2.py::test_ex1 failed: assert -1 == 5"
    passing = (LanguageResult(PY, (ApproachResult("reference"),)),)
    reported(project_report(passing, SuiteCheck(13, 14, (failure,))))
    result = invoke("bank-project-python")
    assert (result.exit_code, result.report[:2]) == (
        ExitCode.FAILURES,
        ["0249-bank-pro...  static ok · py 1/1 ok · suite 13/14", f"  suite: {failure}"],
    )


def test_a_starter_that_does_not_load_is_a_language_problem(reported):
    problem = "starter does not load: SyntaxError: invalid syntax"
    languages = (LanguageResult(PY, (ApproachResult("reference"),), (problem,)),)
    reported(project_report(languages, SuiteCheck(14, 14)))
    assert invoke("bank-project-python").report[:2] == [
        "0249-bank-pro...  static ok · py 1/1 FAIL · suite 14/14",
        f"  py {problem}",
    ]
