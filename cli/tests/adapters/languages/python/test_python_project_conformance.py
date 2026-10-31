"""The Python project fixtures 9022 and 9024 through `cstudy verify --conformance`.

Marked `slow`: the workspace venv's Python runs the grading jobs and hosts pytest for the suite
job, as for a user's project, in a copy of the session's practice workspace over this checkout's
content (docs/specs/runners.md#conformance-suite).
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
PROJECT_FIXTURES = ("conformance-project-python", "conformance-suite-pytest")


def test_the_python_runner_meets_the_project_expectations(
    practice_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(REPOSITORY_ROOT))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
    arguments = ["verify", "--conformance", "--lang", "python", *PROJECT_FIXTURES]
    result = runner.invoke(cli.app, arguments)
    assert (result.exit_code, result.output.splitlines()[:2]) == (
        ExitCode.SUCCESS,
        [
            "9022-conformance-project-python  py ok",
            "9024-conformance-suite-pytest    py ok",
        ],
    )
