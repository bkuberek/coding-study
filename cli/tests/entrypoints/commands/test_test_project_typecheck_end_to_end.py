"""`cstudy test --typecheck` on the TypeScript fixture project through the workspace's real `tsc`
and the real TypeScript runner (docs/specs/cli.md#project-problems).

The fixture's reference type-checks and passes its tests; the same folder with a deliberate type
error in `src/bank.ts` fails to build, with the error as a structured `typecheck` diagnostic in the
event stream and in `--json`.
"""

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker, TypeScriptRunner
from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import (
    REPOSITORY_ROOT,
    SCHEMAS_DIRECTORY,
    TYPESCRIPT_BANK_PROJECT,
    TYPESCRIPT_PROJECT_PROBLEMS,
)

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

SLUG = "bank-project-typescript"
FIXTURE = TYPESCRIPT_PROJECT_PROBLEMS / TYPESCRIPT_BANK_PROJECT
FOLDER = Path("projects") / SLUG
TYPE_ERROR = """\
export class Bank {
  createAccount(timestamp: number, accountId: string): boolean {
    return accountId.length;
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    return amount;
  }
}
"""
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)
runner = CliRunner()


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


def events(result: Result) -> list[dict]:
    return [json.loads(line) for line in result.stdout.splitlines()]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> dict[str, Result]:
    """The reference type-checked, then the same folder with a type error, by step."""
    workspace = repository_root(tmp_path_factory.mktemp("workspace"), TYPESCRIPT_PROJECT_PROBLEMS)
    typescript = workspace / "typescript"
    typescript.mkdir()
    shutil.copyfile(practice_workspace / "typescript" / "package.json", typescript / "package.json")
    (typescript / "node_modules").symlink_to(practice_workspace / "typescript" / "node_modules")
    toolchains = FakeToolchains(
        runners={
            Language.TYPESCRIPT: TypeScriptRunner(
                workspace, REPOSITORY_ROOT / "runners", PnpmTypeChecker()
            )
        },
        project_test_generators={Language.TYPESCRIPT: TypeScriptTestGenerator()},
    )
    process = SubprocessRunner(workspace / ".cs" / "runs")
    environment = make_environment(workspace, toolchains=toolchains, runner_process=process)
    folder = workspace / FOLDER
    steps: dict[str, Result] = {}
    with pytest.MonkeyPatch.context() as patch:
        for command in (start, test_command):
            patch.setattr(command, "load_environment", lambda *_: environment)
        cs("start", SLUG, "--no-open")
        shutil.copytree(FIXTURE / "solutions" / "reference", folder, dirs_exist_ok=True)
        steps["reference"] = cs("test", "--typecheck", "--json")
        (folder / "src" / "bank.ts").write_text(TYPE_ERROR, encoding="utf-8")
        steps["type error"] = cs("test", "--typecheck", "--json")
        steps["type error events"] = cs("test", "--typecheck", "--events")
        steps["type error report"] = cs("test", "--typecheck")
    return steps


def test_a_folder_that_type_checks_runs_its_tests_and_passes(runs):
    document = json.loads(runs["reference"].stdout)
    assert (document["outcome"], document["diagnostics"]) == ("passed", [])


def test_a_type_error_fails_to_build_and_exits_2(runs):
    document = json.loads(runs["type error"].stdout)
    assert (runs["type error"].exit_code, document["outcome"], document["cases"]) == (
        ExitCode.USER_CODE_ERROR,
        "build_failed",
        [],
    )


def test_a_type_error_is_a_typecheck_diagnostic_at_its_place(runs):
    (diagnostic,) = json.loads(runs["type error"].stdout)["diagnostics"]
    assert {key: diagnostic[key] for key in ("source", "file", "line", "column", "code")} == {
        "source": "typecheck",
        "file": "src/bank.ts",
        "line": 3,
        "column": 5,
        "code": "TS2322",
    }


def test_the_event_stream_of_a_type_error_names_it_and_ends_build_failed(runs):
    found = events(runs["type error events"])
    assert [(event["type"], event.get("file"), event.get("outcome")) for event in found] == [
        ("run_start", None, None),
        ("diagnostic", "src/bank.ts", None),
        ("run_end", None, "build_failed"),
    ]


def test_every_event_of_a_type_error_matches_the_schema(runs):
    found = events(runs["type error events"])
    assert [event for event in found if not VALIDATOR.is_valid(event)] == []


def test_the_report_of_a_type_error_says_the_build_failed(runs):
    assert "BUILD FAILED" in runs["type error report"].output
