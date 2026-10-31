"""Playing a Go project problem from `cstudy start` to its last submission through the real Go
toolchain: `go test` for the suite and a grading binary per project root
(docs/specs/runners.md#go-project-jobs).

The fixture's starter panics with `not implemented`; the reference adds a package of its own. Your
own test files then add a panic, a hang and a package whose test file does not compile, which the
suite reports one by one while the other tests still run.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go import create_runner
from coding_study.adapters.languages.go.test_generator import GoTestGenerator
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.domain.config import Config, HangGuardSettings
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start, status, submit
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import REPOSITORY_ROOT

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed"),
]

SLUG = "bank-project-go"
PROBLEMS = Path(__file__).resolve().parents[2] / "fixtures" / "project_go" / "problems"
FIXTURE = PROBLEMS / "0001-bank-project-go"
FOLDER = Path("projects") / SLUG
COMMANDS = (start, test_command, submit, status)
HANG_GUARD_MS = 1000
YOUR_TESTS = {
    "extra/extra_test.go": """package extra

import (
	"testing"
	"time"
)

func TestPasses(t *testing.T) {}

func TestPanics(t *testing.T) {
	var accounts map[string]int
	accounts["ivy"] = 1
}

func TestAfterThePanic(t *testing.T) {}

func TestHangs(t *testing.T) {
	time.Sleep(time.Hour)
}
""",
    "broken/broken_test.go": """package broken

import "testing"

func TestBroken(t *testing.T) {
	notDeclaredAnywhere()
}
""",
}
runner = CliRunner()


@pytest.fixture(scope="module")
def environment(tmp_path_factory: pytest.TempPathFactory) -> Environment:
    root = repository_root(tmp_path_factory.mktemp("workspace"), PROBLEMS)
    go = create_runner(LanguageContext(root, REPOSITORY_ROOT / "runners"))
    toolchains = FakeToolchains(
        runners={Language.GO: go}, project_test_generators={Language.GO: GoTestGenerator()}
    )
    config = Config(hang_guard=HangGuardSettings(HANG_GUARD_MS))
    runs = SubprocessRunner(root / ".cs" / "runs")
    return make_environment(root, toolchains=toolchains, runner_process=runs, config=config)


@pytest.fixture(scope="module")
def cstudy(environment: Environment) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        for command in COMMANDS:
            patch.setattr(command, "load_environment", lambda *_: environment)
        yield


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


def write_files(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


@pytest.fixture(scope="module")
def played(environment: Environment, cstudy: None) -> dict[str, Result]:
    """Every step of one play-through, in order."""
    folder = environment.root / FOLDER
    steps = {"start": cs("start", SLUG, "--no-open"), "bare test": cs("test", "--json")}
    steps["bare submit"] = cs("submit")
    shutil.copytree(FIXTURE / "solutions" / "reference", folder, dirs_exist_ok=True)
    steps["solved test"] = cs("test")
    write_files(folder, YOUR_TESTS)
    steps["test of yours"] = cs("test", "--json")
    for name in YOUR_TESTS:
        shutil.rmtree((folder / name).parent)
    steps["submit for level 2"] = cs("submit")
    steps["level 2 test"] = cs("test")
    steps["last submit"] = cs("submit")
    return steps


def document(result: Result) -> dict[str, Any]:
    """The JSON report, after any progress line the runner's first build printed."""
    output = result.output
    return json.loads(output[output.index("{\n") :])


def statuses(result: Result) -> dict[str, str]:
    return {case["id"]: case["status"] for case in document(result)["cases"]}


def errors(result: Result) -> dict[str, dict[str, str]]:
    return {case["id"]: case["error"] for case in document(result)["cases"] if case.get("error")}


def test_start_writes_the_folder_with_its_go_work(environment, played):
    assert (environment.root / FOLDER / "go.work").read_text() == "go 1.24\n\nuse .\n"


def test_start_writes_level_1s_go_test_file(environment, played):
    assert (environment.root / FOLDER / "tests" / "level_1_test.go").is_file()


def test_the_bare_starters_test_panics_with_not_implemented(played):
    assert errors(played["bare test"])["tests/level_1_test.go::TestEx1"]["message"] == (
        "not implemented"
    )


def test_the_bare_starters_panic_points_at_the_starter(played):
    trace = errors(played["bare test"])["tests/level_1_test.go::TestEx1"]["trace"]
    assert trace.splitlines()[-1] == "bank.go:14 in Bank.CreateAccount"


def test_the_bare_starter_fails_its_submission(played):
    assert played["bare submit"].output.splitlines()[-1].startswith("0/2 passed")


def test_the_reference_passes_the_suite(played):
    assert played["solved test"].output.splitlines()[-1] == "all passed. Next: cstudy submit"


def test_your_tests_report_a_panic_a_hang_and_a_package_that_does_not_compile(played):
    assert statuses(played["test of yours"]) == {
        "tests/level_1_test.go::TestEx1": "pass",
        "extra/extra_test.go::TestPasses": "pass",
        "extra/extra_test.go::TestPanics": "error",
        "extra/extra_test.go::TestAfterThePanic": "pass",
        "extra/extra_test.go::TestHangs": "timeout",
        "bank-project-go/broken": "error",
    }


def test_a_test_file_that_does_not_compile_names_its_error(played):
    error = errors(played["test of yours"])["bank-project-go/broken"]
    assert (error["type"], error["message"]) == (
        "CompileError",
        "broken/broken_test.go:6:2: undefined: notDeclaredAnywhere",
    )


def test_a_nil_map_panic_names_its_runtime_error(played):
    error = errors(played["test of yours"])["extra/extra_test.go::TestPanics"]
    assert error["message"] == "assignment to entry in nil map"


def test_a_run_with_failures_exits_1(played):
    assert played["test of yours"].exit_code == ExitCode.FAILURES


def test_a_passing_submission_opens_level_2(played):
    assert "level 2 unlocked: Transfers and reports" in played["submit for level 2"].output


def test_level_2_gets_its_go_test_file(environment, played):
    assert (environment.root / FOLDER / "tests" / "level_2_test.go").is_file()


def test_the_reference_passes_level_2s_tests(played):
    assert played["level 2 test"].output.splitlines()[-1] == "all passed. Next: cstudy submit"


def test_the_last_submission_finishes_every_level(played):
    assert played["last submit"].output.splitlines()[-1].startswith("all passed · every level done")
