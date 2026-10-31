"""`cstudy start` output for a project problem (docs/specs/cli.md#cstudy-start)."""

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import PROJECT_PROBLEMS

runner = CliRunner()
SLUG = "bank-project-python"
FOLDER = f"projects/{SLUG}"
STATEMENT = f".statements/{SLUG}.md"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    toolchains = FakeToolchains(project_test_generators={Language.PYTHON: PythonTestGenerator()})
    environment = make_environment(
        repository_root(tmp_path, PROJECT_PROBLEMS), toolchains=toolchains
    )
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    return environment


def cs_start(*arguments: str):
    return runner.invoke(cli.app, ["start", SLUG, *arguments])


def test_start_reports_the_folder_its_entry_and_its_tests(environment):
    assert cs_start("--no-open").output.splitlines() == [
        f"{SLUG} · medium · practical · python · project",
        f"project    {FOLDER} (4 files)",
        "entry      bank/bank.py: Bank",
        "tests      tests/test_level_1.py (1 test)",
        f"statement  {STATEMENT}",
        "level      1 of 2: Accounts and deposits",
        "next       cstudy test --watch, then cstudy submit",
    ]


def test_a_resumed_project_says_so(environment):
    cs_start("--no-open")
    assert "attempt    resumed" in cs_start("--no-open").output.splitlines()


def test_start_opens_the_folder_and_the_statement(environment):
    cs_start()
    assert environment.editor.opened == [
        [environment.workspace.absolute(FOLDER), environment.workspace.absolute(STATEMENT)]
    ]


def test_another_language_exits_3(environment):
    result = cs_start("--lang", "kotlin", "--no-open")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        f"error: {SLUG} is solved in python only\n",
    )
