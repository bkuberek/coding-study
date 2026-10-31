"""`cstudy test` on a project problem runs its native suite as feedback
(docs/specs/cli.md#project-problems)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.ports import ProjectSuite
from coding_study.application.project_testing import (
    ProjectTestRequest,
    is_project_attempt,
    run_project_tests,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.debugging import DebugRequest
from coding_study.domain.diagnostics import load_diagnostic
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.project_test_runs import SuiteOrigin
from coding_study.domain.runs import Raised, UserError
from coding_study.domain.suite_runs import AssertionFailed, Passed, SuiteTest
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS
from tests.project_fakes import FakeProjectRunner, ScriptedProjectProcess, project_environment

SLUG = "bank-project-python"
FOLDER = f"projects/{SLUG}"
LEVEL_1 = SuiteTest("tests/test_level_1.py::test_ex1", Passed(1000))
YOURS = SuiteTest("tests/test_mine.py::test_overdraft", AssertionFailed("assert -1 == 5", 1000))
STARTER = SuiteTest("README.md::test_doc", Passed(1000))


@pytest.fixture
def suites() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def environment(tmp_path, suites) -> Environment:
    environment = project_environment(tmp_path, suites)
    start_attempt(environment, StartRequest(SLUG))
    return environment


@pytest.fixture
def runner(environment) -> FakeProjectRunner:
    return environment.toolchains.runners[Language.PYTHON]


def run(environment: Environment, **fields: object):
    request = replace(ProjectTestRequest(), **fields)  # type: ignore[arg-type]
    return run_project_tests(environment, request, [].append)


def test_a_project_attempt_is_told_apart(environment):
    assert is_project_attempt(environment, None, None)


def test_another_kind_of_attempt_is_not_a_project(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    root = repository_root(tmp_path, FIXTURE_PROBLEMS)
    environment = make_environment(root, toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    assert not is_project_attempt(environment, None, None)


def test_the_suite_runs_in_the_project_folder(environment, suites):
    run(environment)
    assert suites.suites[0].root == str(environment.workspace.absolute(FOLDER))


def test_the_runner_launches_in_the_project_folder(environment, runner):
    run(environment)
    assert runner.scopes == [ProjectSuite(environment.workspace.absolute(FOLDER))]


def test_the_generated_files_of_locked_levels_are_left_out(environment, suites):
    run(environment)
    assert suites.suites[0].exclude == ("tests/test_level_2.py",)


def test_case_selects_tests(environment, suites):
    run(environment, case_ids=("test_ex1",))
    assert suites.suites[0].select == ("test_ex1",)


def test_a_case_that_matches_no_test_is_a_usage_error(environment):
    with pytest.raises(UsageError, match="no test matches --case test_zz"):
        run(environment, case_ids=("test_ex1", "test_zz"))


def test_a_case_that_matches_no_test_records_nothing(environment):
    with pytest.raises(UsageError):
        run(environment, case_ids=("test_zz",))
    attempt = environment.progress.active_attempt()
    assert environment.progress.latest_test_run(attempt.id) is None


def test_a_locked_level_is_a_usage_error(environment):
    with pytest.raises(
        UsageError, match="level 2 is locked; pass level 1 with cstudy submit first"
    ):
        run(environment, level=2)


def test_each_test_gets_its_origin(environment, suites):
    suites.tests = (LEVEL_1, YOURS, STARTER)
    assert [verdict.origin for verdict in run(environment).verdicts] == [
        SuiteOrigin.LEVEL,
        SuiteOrigin.YOURS,
        SuiteOrigin.STARTER,
    ]


def test_the_run_is_stored_with_the_suites_tally(environment, suites):
    suites.tests = (LEVEL_1, YOURS)
    result = run(environment)
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored.tally == Tally(total=2, passed=1, failed=1)


def test_the_stored_run_hashes_the_project_folder(environment):
    result = run(environment)
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored.code_hash == environment.workspace.content_hash(FOLDER)


def test_a_passing_suite_opens_no_level(environment):
    assert run(environment).attempt.level_unlocked == 1


def test_a_passing_suite_is_not_a_full_pass(environment):
    run(environment)
    assert environment.progress.active_attempt().first_pass_at is None


def test_a_debug_run_is_not_recorded(environment):
    result = run(environment, debug=DebugRequest())
    assert environment.progress.latest_test_run(result.attempt.id) is None


def test_a_full_run_covers_every_case(environment):
    assert run(environment).every_case


def test_a_case_selection_is_not_every_case(environment):
    assert not run(environment, case_ids=("test_ex1",)).every_case


def test_the_run_reports_the_framework(environment):
    assert run(environment).framework == "pytest"


def test_a_run_without_tests_has_not_passed(environment, suites):
    suites.tests = ()
    assert not run(environment).passed


def test_a_run_whose_tests_all_passed_has_passed(environment):
    assert run(environment).passed


def test_the_project_folder_is_watched(environment):
    assert run(environment).watched == FOLDER


def test_a_project_attempt_in_another_language_is_refused(environment):
    with pytest.raises(UsageError):
        run(environment, language=Language.KOTLIN)


def test_the_suite_root_is_absolute(environment, suites):
    run(environment)
    assert Path(suites.suites[0].root).is_absolute()


def test_a_test_file_that_does_not_import_is_a_diagnostic(environment, suites):
    broken = UserError("SyntaxError", "invalid syntax", "bank/bank.py:5")
    suites.tests = (SuiteTest("tests/test_level_1.py", Raised(broken, 0)),)
    assert run(environment).diagnostics == (load_diagnostic(broken),)


def test_a_suite_that_imports_has_no_diagnostics(environment):
    assert run(environment).diagnostics == ()
