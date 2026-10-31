"""`cstudy verify` on a project problem through the real Python runner: D1, D3 and D9.

Marked `slow`: it runs the workspace venv's Python and pytest. The content root is temporary (the
project fixture problem and a link to the real `runners/`), and the workspace is a copy of the
session's practice workspace that links its venv and runner runtime.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
SLUG = "bank-project-python"
NAME = "0001-bank-pro...  "


@pytest.fixture
def content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(PROJECT_PROBLEMS, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture
def problem(content: Path) -> Path:
    return content / "problems" / BANK_PROJECT


@pytest.fixture
def verify(content: Path, practice_workspace: Path, tmp_path: Path, monkeypatch):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))

    def invoke(*arguments: str) -> tuple[int, list[str]]:
        result = runner.invoke(cli.app, ["verify", SLUG, *arguments])
        return result.exit_code, result.output.splitlines()

    return invoke


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_a_correct_project_passes_its_cases_and_its_suite(verify):
    exit_code, lines = verify()
    assert (exit_code, lines[0]) == (
        ExitCode.SUCCESS,
        f"{NAME}static ok · py 1/1 ok · suite 2/2",
    )


@pytest.fixture
def wrong_transfers(verify, problem):
    bank = problem / "solutions" / "reference" / "bank" / "bank.py"
    edit(bank, "balances[source_id] -= amount", "balances[source_id] -= 2 * amount")
    return verify()


def test_a_wrong_reference_fails_its_cases_and_its_tests(wrong_transfers):
    exit_code, lines = wrong_transfers
    assert (exit_code, lines[0]) == (
        ExitCode.FAILURES,
        f"{NAME}static ok · py 0/1 FAIL · suite 1/2      draft (coverage 0/1)",
    )


def test_a_failing_case_of_the_reference_names_its_level(wrong_transfers):
    _, lines = wrong_transfers
    assert lines[1].startswith("  py reference: level 2 ex2 FAIL: expected [null, true, true")


def test_a_failing_test_of_the_reference_names_the_test(wrong_transfers):
    _, lines = wrong_transfers
    assert lines[2].startswith("  suite: tests/test_level_2.py::test_ex2 failed: assert ")


def test_a_new_python_project_verifies_once_its_placeholders_are_replaced(verify, content):
    created = runner.invoke(
        cli.app, ["new", "kv-project-python", "--from-template", "project-python"]
    )
    assert created.exit_code == ExitCode.SUCCESS
    [directory] = (content / "problems").glob("*-kv-project-python")
    for path in directory.rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "kv-project-python"])
    assert (result.exit_code, result.output.splitlines()[0]) == (
        ExitCode.SUCCESS,
        f"{directory.name[:13]}...  static ok · py 1/1 ok · suite 2/2",
    )


def test_a_starter_that_does_not_import_fails_to_load(verify, problem):
    edit(
        problem / "starter" / "bank" / "bank.py",
        "class Bank:",
        "import missing_module\n\n\nclass Bank:",
    )
    exit_code, lines = verify()
    assert (exit_code, lines[1]) == (
        ExitCode.FAILURES,
        "  py starter does not load: ModuleNotFoundError: No module named 'missing_module'",
    )
