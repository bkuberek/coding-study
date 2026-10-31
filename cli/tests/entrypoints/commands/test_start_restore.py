"""`cstudy start <slug> --restore <path>` (docs/specs/cli.md#cstudy-start)."""

import pytest
from typer.testing import CliRunner, Result

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, FIXTURE_TRACKS, PROJECT_PROBLEMS
from tests.project_fakes import PROJECT_FOLDER, PROJECT_SLUG
from tests.project_locks import passing_environment

runner = CliRunner()
HEADER = f"{PROJECT_SLUG} · medium · practical · python · project"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = passing_environment(repository_root(tmp_path, PROJECT_PROBLEMS))
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    return environment


def cs_start(*arguments: str) -> Result:
    return runner.invoke(cli.app, ["start", PROJECT_SLUG, *arguments])


def test_restore_reports_a_starter_file(environment):
    assert cs_start("--restore", "bank/bank.py").output.splitlines() == [
        HEADER,
        "restored   bank/bank.py (starter)",
    ]


def test_restore_reports_a_generated_test_files_level(environment):
    assert cs_start("--restore", "tests/test_level_1.py").output.splitlines()[-1] == (
        "restored   tests/test_level_1.py (level 1 tests)"
    )


def test_restore_exits_0(environment):
    assert cs_start("--restore", "bank/bank.py").exit_code == ExitCode.SUCCESS


def test_restore_opens_no_editor(environment):
    cs_start("--restore", "bank/bank.py")
    assert environment.editor.opened == []


def test_restore_writes_the_file(environment):
    environment.workspace.write_text(f"{PROJECT_FOLDER}/bank/bank.py", "class Bank: pass\n")
    cs_start("--restore", "bank/bank.py")
    assert environment.workspace.read_text(f"{PROJECT_FOLDER}/bank/bank.py") != (
        "class Bank: pass\n"
    )


def test_restore_of_a_file_you_added_exits_3(environment):
    environment.workspace.write_text(f"{PROJECT_FOLDER}/bank/ledger.py", "LEDGER = []\n")
    assert cs_start("--restore", "bank/ledger.py").exit_code == ExitCode.USAGE_ERROR


def test_restore_of_a_path_outside_the_folder_exits_3(environment):
    result = cs_start("--restore", "../../progress.db")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: cannot restore ../../progress.db: leaves the folder\n",
    )


@pytest.mark.parametrize("flags", [["--fresh"], ["--timer", "25m"]])
def test_restore_excludes_starting_flags(environment, flags):
    result = cs_start("--restore", "bank/bank.py", *flags)
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: --restore excludes --fresh and --timer\n",
    )


def test_restore_of_an_item_exits_3(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, FIXTURE_PROBLEMS, FIXTURE_TRACKS))
    monkeypatch.setattr(start, "load_environment", lambda *_: environment)
    result = runner.invoke(cli.app, ["start", "url-shortener", "--restore", "notes.md"])
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: --restore is for project problems\n",
    )
