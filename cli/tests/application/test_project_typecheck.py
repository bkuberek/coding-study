"""`cstudy test --typecheck` on a project problem: the folder's type check comes first, and a
failure runs no test (docs/specs/cli.md#project-problems)."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import BuildFailed
from coding_study.application.project_testing import ProjectTestRequest, run_project_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource
from coding_study.domain.problem import Language
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS, TYPESCRIPT_PROJECT_PROBLEMS
from tests.project_fakes import FakeProjectRunner, ScriptedProjectProcess

SLUG = "bank-project-typescript"
FOLDER = f"projects/{SLUG}"
TYPE_ERROR = f"{FOLDER}/src/bank.ts(3,5): error TS2322: Type 'number' is not 'boolean'."


@dataclass
class TypeCheckingRunner(FakeProjectRunner):
    """A project runner whose language type-checks a folder, as TypeScript's does."""

    failure: BuildFailed | None = None
    checked: list[Path] = field(default_factory=list[Path])

    def typecheck_project(self, root: Path) -> BuildFailed | None:
        self.checked.append(root)
        return self.failure


@pytest.fixture
def runner() -> TypeCheckingRunner:
    return TypeCheckingRunner()


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def environment(tmp_path, runner, process) -> Environment:
    toolchains = FakeToolchains(
        runners={Language.TYPESCRIPT: runner},
        project_test_generators={Language.TYPESCRIPT: TypeScriptTestGenerator()},
    )
    root = repository_root(tmp_path, TYPESCRIPT_PROJECT_PROBLEMS)
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    start_attempt(environment, StartRequest(SLUG))
    return environment


def type_checked(environment: Environment):
    return run_project_tests(environment, ProjectTestRequest(typecheck=True), [].append)


def test_the_type_check_reads_the_project_folder(environment, runner):
    type_checked(environment)
    assert runner.checked == [environment.workspace.absolute(FOLDER)]


def test_without_typecheck_the_folder_is_not_checked(environment, runner):
    run_project_tests(environment, ProjectTestRequest(), [].append)
    assert runner.checked == []


def test_a_folder_that_type_checks_runs_its_suite(environment, process):
    type_checked(environment)
    assert len(process.suites) == 1


def test_a_type_check_that_fails_runs_no_test(environment, runner, process):
    runner.failure = BuildFailed((TYPE_ERROR,))
    type_checked(environment)
    assert process.suites == []


def test_a_failed_type_check_keeps_the_checkers_report(environment, runner):
    runner.failure = BuildFailed((TYPE_ERROR,))
    assert type_checked(environment).build_failure == runner.failure


def test_a_failed_type_check_does_not_pass(environment, runner):
    runner.failure = BuildFailed((TYPE_ERROR,))
    assert not type_checked(environment).passed


def test_a_failed_type_check_is_a_typecheck_diagnostic_in_the_folder(environment, runner):
    runner.failure = BuildFailed((TYPE_ERROR,))
    assert type_checked(environment).diagnostics == (
        Diagnostic(
            message="Type 'number' is not 'boolean'.",
            source=DiagnosticSource.TYPECHECK,
            file="src/bank.ts",
            line=3,
            column=5,
            code="TS2322",
        ),
    )


def test_a_failed_type_check_is_stored_as_a_run_without_tests(environment, runner):
    runner.failure = BuildFailed((TYPE_ERROR,))
    result = type_checked(environment)
    stored = environment.progress.latest_test_run(result.attempt.id)
    assert stored is not None
    assert stored.tally.total == 0


def test_a_checker_without_a_parser_gives_each_line_as_a_diagnostic(tmp_path, process):
    checker = TypeCheckingRunner(failure=BuildFailed(("bank/bank.py:3: error: no",)))
    toolchains = FakeToolchains(
        runners={Language.PYTHON: checker},
        project_test_generators={Language.PYTHON: PythonTestGenerator()},
    )
    root = repository_root(tmp_path, PROJECT_PROBLEMS)
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    start_attempt(environment, StartRequest("bank-project-python"))
    assert type_checked(environment).diagnostics == (
        Diagnostic("bank/bank.py:3: error: no", DiagnosticSource.TYPECHECK),
    )
