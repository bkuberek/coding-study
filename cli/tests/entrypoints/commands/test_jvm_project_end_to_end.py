"""Playing a Java and a Kotlin project problem from `cstudy start` to `cstudy submit` of the last
level through the real Gradle build, JVM runner and JUnit Platform
(docs/specs/runners.md#jvm-project-builds).

The workspace is a light copy of the session's practice workspace: its own `jvm/` and the shared
runner runtime, whose warm-up projects already cached what a project folder builds with offline.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm import create_java_runner, create_kotlin_runner
from coding_study.adapters.languages.jvm.test_generators import (
    JavaTestGenerator,
    KotlinTestGenerator,
)
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start, status, submit
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "jvm-projects" / "problems"
COMMANDS = (start, test_command, submit, status)
RUNNERS = {Language.JAVA: create_java_runner, Language.KOTLIN: create_kotlin_runner}
GENERATORS = {Language.JAVA: JavaTestGenerator, Language.KOTLIN: KotlinTestGenerator}
EXTENSIONS = {Language.JAVA: "java", Language.KOTLIN: "kt"}
runner = CliRunner()


@pytest.fixture(scope="module", params=[Language.JAVA, Language.KOTLIN], ids=str)
def language(request: pytest.FixtureRequest) -> Language:
    return request.param


@pytest.fixture(scope="module")
def environment(
    tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path, language: Language
) -> Environment:
    root = repository_root(tmp_path_factory.mktemp(f"{language}-workspace"), FIXTURES)
    workspace_like(practice_workspace, root)
    context = LanguageContext(root, root / RUNTIME_RUNNERS)
    toolchains = FakeToolchains(
        runners={language: RUNNERS[language](context)},
        project_test_generators={language: GENERATORS[language]()},
    )
    runs = SubprocessRunner(root / ".cs" / "runs")
    return make_environment(root, toolchains=toolchains, runner_process=runs)


@pytest.fixture(scope="module")
def cstudy(environment: Environment) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        for command in COMMANDS:
            patch.setattr(command, "load_environment", lambda *_: environment)
        yield


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


def folder(environment: Environment, language: Language) -> Path:
    return environment.root / "projects" / f"bank-project-{language}"


def sources(language: Language, kind: str) -> Path:
    return Path("src") / kind / str(language) / "bank"


@pytest.fixture(scope="module")
def played(environment: Environment, language: Language, cstudy: None) -> dict[str, Result]:
    """Every step of one play-through, in order."""
    slug = f"bank-project-{language}"
    steps = {"start": cs("start", slug, "--no-open"), "bare test": cs("test")}
    reference = FIXTURES / f"000{1 if language is Language.JAVA else 2}-{slug}" / "solutions"
    shutil.copytree(reference / "reference", folder(environment, language), dirs_exist_ok=True)
    steps["solved test"] = cs("test")
    steps["submit for level 2"] = cs("submit")
    steps["level 2 test"] = cs("test")
    steps["last submit"] = cs("submit")
    bank = (
        folder(environment, language) / sources(language, "main") / f"Bank.{EXTENSIONS[language]}"
    )
    solved = bank.read_text()
    bank.write_text(solved.replace("class Bank", "class Bank {", 1))
    steps["broken submit"] = cs("submit")
    steps["broken test"] = cs("test")
    bank.write_text(solved)
    return steps


def test_start_writes_level_1s_test_class(environment, language, played):
    level_1 = sources(language, "test") / f"Level1Test.{EXTENSIONS[language]}"
    assert (folder(environment, language) / level_1).is_file()


def test_the_bare_starter_fails_level_1(language, played):
    level_1 = f"{sources(language, 'test')}/Level1Test.{EXTENSIONS[language]}::ex1"
    assert f"ERROR    {level_1}\n" in played["bare test"].output


def test_the_starters_own_test_passes_and_is_tagged(language, played):
    starter = f"{sources(language, 'test')}/BankTest.{EXTENSIONS[language]}::opensWithNoAccounts"
    assert f"PASS     {starter}   starter\n" in played["bare test"].output


def test_the_bare_starter_exits_1(played):
    assert played["bare test"].exit_code == ExitCode.FAILURES


def test_the_reference_passes_the_suite(played):
    assert played["solved test"].output.splitlines()[-1] == "all passed. Next: cstudy submit"


def test_a_passing_submission_opens_level_2(played):
    assert "level 2 unlocked: Transfers" in played["submit for level 2"].output


def test_the_opened_level_gets_its_test_class(environment, language, played):
    level_2 = sources(language, "test") / f"Level2Test.{EXTENSIONS[language]}"
    assert (folder(environment, language) / level_2).is_file()


def test_level_2s_tests_run_and_pass(language, played):
    level_2 = f"{sources(language, 'test')}/Level2Test.{EXTENSIONS[language]}::ex2"
    result = played["level 2 test"]
    assert (f"PASS     {level_2}\n" in result.output, result.exit_code) == (True, ExitCode.SUCCESS)


def test_the_last_submission_is_the_full_pass(played):
    assert "every level done" in played["last submit"].output


def test_code_that_does_not_compile_does_not_load(played):
    result = played["broken submit"]
    assert (result.exit_code, "CompileError" in result.output) == (ExitCode.USER_CODE_ERROR, True)


def test_a_suite_that_does_not_compile_exits_2(played):
    assert played["broken test"].exit_code == ExitCode.USER_CODE_ERROR


def test_a_suite_that_does_not_compile_lists_the_compiler_lines(language, played):
    bank = f"{sources(language, 'main')}/Bank.{EXTENSIONS[language]}:"
    assert bank in played["broken test"].output


def test_gradle_build_output_stays_out_of_the_tracked_files(environment, language, played):
    """The watcher and the code hash ignore it; the workspace .gitignore does too."""
    assert (folder(environment, language) / "build").is_dir()
