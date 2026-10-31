"""`cstudy test` on a project problem whose code does not compile: the compiler's report in the
run's compile error is read into diagnostics at the project's files
(docs/specs/cli.md#diagnostics).

Each compile error was captured from the real toolchain on the catalog's bank project with
broken code (tests/application/recorded); the process is a script that reports it.
"""

import json
from pathlib import Path

import pytest

from coding_study.adapters.languages.go.test_generator import GoTestGenerator
from coding_study.adapters.languages.jvm.test_generators import (
    JavaTestGenerator,
    KotlinTestGenerator,
)
from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.application.environment import Environment
from coding_study.application.ports import ProjectTestGenerator
from coding_study.application.project_testing import (
    ProjectTestRequest,
    ProjectTestResult,
    run_project_tests,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.submit_project import SubmitRequest, submit_project
from coding_study.domain.diagnostics import Diagnostic, DiagnosticSource, Severity
from coding_study.domain.problem import Language
from coding_study.domain.runs import Raised, UserError
from coding_study.domain.suite_runs import SuiteTest
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import RUST_PROJECT_PROBLEMS
from tests.project_fakes import FakeProjectRunner, ScriptedProjectProcess

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RECORDED = Path(__file__).parent / "recorded"
PROBLEMS: dict[Language, Path] = {
    Language.JAVA: FIXTURES / "jvm-projects" / "problems",
    Language.KOTLIN: FIXTURES / "jvm-projects" / "problems",
    Language.GO: FIXTURES / "project_go" / "problems",
    Language.RUST: RUST_PROJECT_PROBLEMS,
}
GENERATORS: dict[Language, ProjectTestGenerator] = {
    Language.JAVA: JavaTestGenerator(),
    Language.KOTLIN: KotlinTestGenerator(),
    Language.GO: GoTestGenerator(),
    Language.RUST: RustTestGenerator(),
}
FIRST_ERRORS: dict[Language, tuple[str, int, int | None, str | None]] = {
    Language.JAVA: ("src/main/java/bank/Bank.java", 15, 21, None),
    Language.KOTLIN: ("src/main/kotlin/bank/Bank.kt", 12, 24, None),
    Language.GO: ("bank.go", 17, 6, None),
    Language.RUST: ("src/bank.rs", 22, 30, "E0425"),
}
COMPILED = tuple(FIRST_ERRORS)


def compile_error(language: Language) -> tuple[UserError, str | None]:
    """The captured error, and the id of the test it is the result of; None for the suite's."""
    recorded = json.loads((RECORDED / f"project-compile-{language}.json").read_text("utf-8"))
    return UserError(**recorded["error"]), recorded["test_id"]


def run(tmp_path: Path, language: Language, error: UserError, test_id: str | None):
    """The project's tests run in `language` by a process that reports `error` as the suite's
    load error, or, with `test_id`, as that test's result."""
    toolchains = FakeToolchains(
        runners={language: FakeProjectRunner()},
        project_test_generators={language: GENERATORS[language]},
    )
    process = (
        ScriptedProjectProcess(tests=(SuiteTest(test_id, Raised(error, 0)),))
        if test_id
        else ScriptedProjectProcess(tests=(), suite_load_error=error)
    )
    root = repository_root(tmp_path, PROBLEMS[language])
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    start_attempt(environment, StartRequest(f"bank-project-{language}"))
    return project_result(environment)


def project_result(environment: Environment) -> ProjectTestResult:
    return run_project_tests(environment, ProjectTestRequest(), [].append)


@pytest.fixture
def recorded_run(tmp_path, language):
    error, test_id = compile_error(language)
    return run(tmp_path, language, error, test_id)


@pytest.fixture(params=COMPILED, ids=str)
def language(request: pytest.FixtureRequest) -> Language:
    return request.param


def test_the_first_error_is_at_its_line_and_column_of_the_projects_file(language, recorded_run):
    file, line, column, code = FIRST_ERRORS[language]
    first = recorded_run.diagnostics[0]
    assert (first.file, first.line, first.column, first.code) == (file, line, column, code)


def test_every_error_is_a_build_diagnostic(recorded_run):
    assert {d.source for d in recorded_run.diagnostics} == {DiagnosticSource.BUILD}


def test_every_error_of_the_report_is_a_diagnostic(language, recorded_run):
    counts = {Language.JAVA: 2, Language.KOTLIN: 3, Language.GO: 3, Language.RUST: 3}
    assert len(recorded_run.diagnostics) == counts[language]


def test_a_compile_error_is_one_diagnostic_for_each_error_not_one_for_the_run(recorded_run):
    assert "the project does not compile" not in {d.message for d in recorded_run.diagnostics}


def test_a_go_package_that_the_tests_import_gives_each_error_once(tmp_path):
    error, test_id = compile_error(Language.GO)
    assert test_id is not None
    toolchains = FakeToolchains(
        runners={Language.GO: FakeProjectRunner()},
        project_test_generators={Language.GO: GENERATORS[Language.GO]},
    )
    tests = (
        SuiteTest("bank-project-go", Raised(error, 0)),
        SuiteTest("bank-project-go/tests", Raised(error, 0)),
    )
    root = repository_root(tmp_path, PROBLEMS[Language.GO])
    environment = make_environment(
        root, toolchains=toolchains, runner_process=ScriptedProjectProcess(tests=tests)
    )
    start_attempt(environment, StartRequest("bank-project-go"))
    assert len(project_result(environment).diagnostics) == 3


def test_a_file_outside_the_project_folder_keeps_the_message_and_has_no_place(tmp_path):
    error = UserError(
        "CompileError", "the project does not compile", "/ws/other/Bank.java:3: error: x"
    )
    (found,) = run(tmp_path, Language.JAVA, error, None).diagnostics
    assert found == Diagnostic("x", DiagnosticSource.BUILD, Severity.ERROR)


def test_a_compile_error_the_parser_does_not_know_stays_the_load_diagnostic(tmp_path):
    error = UserError("CompileError", "error: failed to parse manifest at `Cargo.toml`")
    (found,) = run(tmp_path, Language.RUST, error, "src/lib.rs").diagnostics
    assert (found.source, found.code, found.message) == (
        DiagnosticSource.LOAD,
        "CompileError",
        "error: failed to parse manifest at `Cargo.toml`",
    )


def test_an_error_that_is_not_a_compile_error_stays_the_load_diagnostic(tmp_path):
    error = UserError("ImportError", "no module named bank", "src/bank.rs:1")
    (found,) = run(tmp_path, Language.RUST, error, "src/lib.rs").diagnostics
    assert (found.source, found.code, found.file) == (
        DiagnosticSource.LOAD,
        "ImportError",
        "src/bank.rs",
    )


def submission_diagnostics(tmp_path: Path, language: Language) -> tuple[Diagnostic, ...]:
    """What `cstudy submit` reports for the captured compile error, as the load error of the
    grading job."""
    error, _ = compile_error(language)
    toolchains = FakeToolchains(
        runners={language: FakeProjectRunner()},
        project_test_generators={language: GENERATORS[language]},
    )
    process = ScriptedProjectProcess(load_error=error)
    root = repository_root(tmp_path, PROBLEMS[language])
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    start_attempt(environment, StartRequest(f"bank-project-{language}"))
    return submit_project(environment, SubmitRequest(), [].append).diagnostics


def test_a_submission_that_does_not_compile_is_a_diagnostic_at_the_first_errors_place(
    tmp_path, language
):
    first = submission_diagnostics(tmp_path, language)[0]
    file, line, column, code = FIRST_ERRORS[language]
    assert (first.source, first.file, first.line, first.column, first.code) == (
        DiagnosticSource.BUILD,
        file,
        line,
        column,
        code,
    )


def test_a_submission_gives_a_diagnostic_for_each_error_of_the_report(tmp_path, language):
    counts = {Language.JAVA: 2, Language.KOTLIN: 3, Language.GO: 3, Language.RUST: 3}
    assert len(submission_diagnostics(tmp_path, language)) == counts[language]
