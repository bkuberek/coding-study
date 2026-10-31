"""`cstudy verify` on a Rust project problem through real cargo, offline: D1, D3 and D9.

Marked `slow`; skipped when `cargo` is not installed. The content root is temporary (the Rust
project fixture problem and a link to the real `runners/`), and the workspace is a copy of the
session's practice workspace that links its runner runtime.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.rust.runner import COLD_NOTICE
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import (
    REPOSITORY_ROOT,
    RUST_BANK_PROJECT,
    RUST_PROJECT_PROBLEMS,
    SCHEMAS_DIRECTORY,
)
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo is not installed"),
]

runner = CliRunner()
SLUG = "bank-project-rust"
NAME = "0001-bank-pro...  "


@pytest.fixture
def content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(RUST_PROJECT_PROBLEMS, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture
def problem(content: Path) -> Path:
    return content / "problems" / RUST_BANK_PROJECT


@pytest.fixture
def verify(content: Path, practice_workspace: Path, tmp_path: Path, monkeypatch):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))

    def invoke(*arguments: str) -> tuple[int, list[str]]:
        result = runner.invoke(cli.app, ["verify", SLUG, *arguments])
        return result.exit_code, reported(result.output)

    return invoke


def reported(output: str) -> list[str]:
    """The output without the notice of a workspace's first Rust build."""
    return [line for line in output.splitlines() if line != COLD_NOTICE]


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_a_correct_project_passes_its_cases_and_its_suite(verify):
    exit_code, lines = verify()
    assert (exit_code, lines[0]) == (
        ExitCode.SUCCESS,
        f"{NAME}static ok · rs 1/1 ok · suite 2/2",
    )


@pytest.fixture
def wrong_transfers(verify, problem):
    ledger = problem / "solutions" / "reference" / "src" / "ledger.rs"
    edit(ledger, "self.add(source_id, -amount)", "self.add(source_id, -2 * amount)")
    return verify()


def test_a_wrong_reference_fails_its_cases_and_its_tests(wrong_transfers):
    exit_code, lines = wrong_transfers
    assert (exit_code, lines[0]) == (
        ExitCode.FAILURES,
        f"{NAME}static ok · rs 0/1 FAIL · suite 1/2      draft (coverage 0/1)",
    )


def test_a_failing_case_of_the_reference_names_its_level(wrong_transfers):
    _, lines = wrong_transfers
    assert lines[1].startswith("  rs reference: level 2 ex2 FAIL: expected [null, true, true")


def test_a_failing_test_of_the_reference_names_the_test_and_its_assertion(wrong_transfers):
    _, lines = wrong_transfers
    assert lines[2].startswith("  suite: tests/level_2.rs::ex2 failed: assertion `left == right`")


def test_a_new_rust_project_verifies_once_its_placeholders_are_replaced(verify, content):
    created = runner.invoke(cli.app, ["new", "kv-project-rust", "--from-template", "project-rust"])
    assert created.exit_code == ExitCode.SUCCESS
    [directory] = (content / "problems").glob("*-kv-project-rust")
    for path in directory.rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "kv-project-rust"])
    assert (result.exit_code, reported(result.output)[0]) == (
        ExitCode.SUCCESS,
        f"{directory.name[:13]}...  static ok · rs 1/1 ok · suite 2/2",
    )


def test_a_starter_that_does_not_compile_fails_to_load_at_the_compilers_location(verify, problem):
    edit(problem / "starter" / "src" / "lib.rs", "pub struct Bank {}", "pub struct Bank {} oops")
    exit_code, lines = verify()
    assert (exit_code, lines[1].partition(": error: ")[0]) == (
        ExitCode.FAILURES,
        "  rs starter does not load: CompileError: the project does not compile: src/lib.rs:6:1",
    )
