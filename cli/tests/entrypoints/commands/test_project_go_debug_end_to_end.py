"""`cstudy test --debug` on a Go project: the runner builds the package of the generated tests
without optimizations, runs it under a headless Delve and stops at a breakpoint in the project's
code (docs/specs/runners.md#go-project-jobs).

Marked `slow`, and skipped without Go or Delve: `cstudy test --debug` runs as a real process in a
copy of the session's practice workspace, and a DAP client attaches as VS Code's Go extension does.
"""

import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.debugging import DebugSession
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from tests.debug_clients import DapClient, free_port
from tests.entrypoints.commands.test_test_debug_end_to_end import NO_DELVE, DebuggedRun
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = [pytest.mark.slow, pytest.mark.skipif(NO_DELVE, reason="go or dlv is not installed")]

runner = CliRunner()
SLUG = "bank-project-go"
PROBLEMS = Path(__file__).resolve().parents[2] / "fixtures" / "project_go" / "problems"
REFERENCE = PROBLEMS / "0001-bank-project-go" / "solutions" / "reference"
BREAKPOINT_LINE = 23
"""`return b.ledger.Open(accountId)` in the reference's bank.go."""
PASSED_LINE = "all passed (debug run: not recorded; cstudy test records the run)"


@pytest.fixture
def folder(tmp_path: Path, practice_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The fixture started and solved with its reference in a workspace of its own."""
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(PROBLEMS, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path / "ws")
    for name, value in (
        ("CSTUDY_CONTENT", content),
        ("CSTUDY_WORKSPACE", root),
        ("CSTUDY_CONFIG", tmp_path / "absent-config.toml"),
    ):
        monkeypatch.setenv(name, str(value))
    started = runner.invoke(cli.app, ["start", SLUG, "--no-open"])
    assert started.exit_code == 0, started.output
    folder = root / "projects" / SLUG
    shutil.copytree(REFERENCE, folder, dirs_exist_ok=True)
    return folder


def test_a_go_project_stops_at_a_breakpoint_in_its_code_and_gives_a_verdict(folder, tmp_path):
    port = free_port()
    output = tmp_path / "run"
    output.mkdir()
    run = DebuggedRun([SLUG, "--debug", "--debug-port", str(port)], dict(os.environ), output)
    try:
        run.wait_for_ready_line(DebugSession(Language.GO, port).ready_line)
        client = DapClient(port, {"mode": "remote"})
        bank = folder / "bank.go"
        stopped_at = client.stop_at(bank, BREAKPOINT_LINE)
        client.run_to_end(bank)
        assert (Path(stopped_at[0]).resolve(), stopped_at[1], run.finish()) == (
            bank.resolve(),
            BREAKPOINT_LINE,
            0,
        )
        assert PASSED_LINE in run.stdout.splitlines()
    finally:
        run.stop()
