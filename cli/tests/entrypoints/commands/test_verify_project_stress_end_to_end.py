"""`cstudy verify` on a project with stress cases through the real Python runner: D6 (the
reference passes every stress case in 10 of 10 runs) and D7 (its broken overlay, whose race sits
in a module the entry imports, fails `s1` in at least 9 of 10).

Marked `slow`: it runs the workspace venv's Python and pytest. The content root is temporary (the
stress project fixture and a link to the real `runners/`), and the workspace is a copy of the
session's practice workspace that links its venv and runner runtime.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import PROJECT_STRESS_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
SLUG = "tally-project-python"


@pytest.fixture
def verify(tmp_path: Path, practice_workspace: Path, monkeypatch):
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(PROJECT_STRESS_PROBLEMS, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))

    def invoke(*arguments: str) -> tuple[int, list[str]]:
        result = runner.invoke(cli.app, ["verify", SLUG, *arguments])
        return result.exit_code, result.output.splitlines()

    return invoke


def test_the_reference_passes_its_stress_cases_and_the_broken_overlay_is_caught(verify):
    exit_code, lines = verify()
    parts = lines[0].split(" · ")
    assert (exit_code, parts[1], parts[3]) == (ExitCode.SUCCESS, "py 1/1 ok", "stress 10/10")
    assert parts[-1].startswith("broken caught 1/1"), lines
