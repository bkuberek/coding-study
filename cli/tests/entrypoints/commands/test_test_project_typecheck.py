"""`cstudy test --typecheck` on a project problem: a type error prints the checker's report, runs
no test and exits 2 (docs/specs/cli.md#project-problems)."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.application.ports import BuildFailed
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import SCHEMAS_DIRECTORY, TYPESCRIPT_PROJECT_PROBLEMS
from tests.project_fakes import FakeProjectRunner, ScriptedProjectProcess

SLUG = "bank-project-typescript"
TYPE_ERROR = f"projects/{SLUG}/src/bank.ts(3,5): error TS2322: Type 'number' is not 'boolean'."
TIMING = re.compile(r"\d+\.\d+s")
runner = CliRunner()


@dataclass
class TypeCheckingRunner(FakeProjectRunner):
    """A project runner whose language type-checks a folder, as TypeScript's does."""

    failure: BuildFailed | None = None
    checked: list[Path] = field(default_factory=list[Path])

    def typecheck_project(self, root: Path) -> BuildFailed | None:
        self.checked.append(root)
        return self.failure


@pytest.fixture
def checker() -> TypeCheckingRunner:
    return TypeCheckingRunner(failure=BuildFailed((TYPE_ERROR,)))


@pytest.fixture
def environment(tmp_path, monkeypatch, checker):
    toolchains = FakeToolchains(
        runners={Language.TYPESCRIPT: checker},
        project_test_generators={Language.TYPESCRIPT: TypeScriptTestGenerator()},
    )
    root = repository_root(tmp_path, TYPESCRIPT_PROJECT_PROBLEMS)
    process = ScriptedProjectProcess()
    environment = make_environment(root, toolchains=toolchains, runner_process=process)
    start_attempt(environment, StartRequest(SLUG))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    return environment


def cs_test(*arguments: str) -> Result:
    return runner.invoke(cli.app, ["test", "--typecheck", *arguments])


def test_the_flag_reaches_the_type_check(environment, checker):
    cs_test()
    assert checker.checked == [environment.workspace.absolute(f"projects/{SLUG}")]


def test_a_type_error_prints_the_checkers_report_and_no_test(environment):
    lines = [TIMING.sub("T", line) for line in cs_test().output.splitlines()]
    assert lines == [
        f"{SLUG} · typescript · level 1 of 2",
        "",
        "BUILD FAILED",
        TYPE_ERROR,
        "",
        "no tests ran · total T",
    ]


def test_a_type_error_exits_2(environment):
    assert cs_test().exit_code == ExitCode.USER_CODE_ERROR


def test_a_folder_that_type_checks_runs_its_suite_and_exits_as_it_does(environment, checker):
    checker.failure = None
    assert cs_test().exit_code == ExitCode.SUCCESS


def test_the_document_of_a_type_error_failed_to_build(environment):
    document = json.loads(cs_test("--json").stdout)
    assert (document["outcome"], document["exit_code"], document["cases"]) == (
        "build_failed",
        ExitCode.USER_CODE_ERROR,
        [],
    )


def test_the_document_keeps_the_checkers_report_as_the_build_diagnostics(environment):
    assert json.loads(cs_test("--json").stdout)["build"]["diagnostics"] == [TYPE_ERROR]


def test_the_document_lists_the_type_error_as_a_typecheck_diagnostic(environment):
    assert json.loads(cs_test("--json").stdout)["diagnostics"] == [
        {
            "source": "typecheck",
            "severity": "error",
            "file": "src/bank.ts",
            "line": 3,
            "column": 5,
            "code": "TS2322",
            "message": "Type 'number' is not 'boolean'.",
        }
    ]


def test_the_event_stream_of_a_type_error_has_its_diagnostic_and_ends_build_failed(environment):
    events = [json.loads(line) for line in cs_test("--events").stdout.splitlines()]
    assert [(event["type"], event.get("source"), event.get("outcome")) for event in events] == [
        ("run_start", None, None),
        ("diagnostic", "typecheck", None),
        ("run_end", None, "build_failed"),
    ]


def test_the_event_stream_of_a_type_error_matches_the_schema(environment):
    schema = json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    events = [json.loads(line) for line in cs_test("--events").stdout.splitlines()]
    assert [event for event in events if not validator.is_valid(event)] == []
