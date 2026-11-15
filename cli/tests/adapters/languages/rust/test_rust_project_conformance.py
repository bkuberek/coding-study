"""The Rust project fixtures 9032, 9033, 9042, 9045 and 9046 through `cstudy verify --conformance`.

Marked `slow`: cargo builds each fixture's harness offline, 9045's and 9046's with the runner's
virtual clock on tokio, in a copy of the session's practice workspace over this checkout's content
(docs/specs/runners.md#conformance-suite).
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo is not installed"),
]

runner = CliRunner()
PROJECT_FIXTURES = (
    "conformance-project-rust",
    "conformance-suite-cargo",
    "conformance-project-stress-rust",
    "conformance-project-clock-rust",
    "conformance-project-stress-clock-rust",
)


def test_the_rust_runner_meets_the_project_expectations(
    practice_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(REPOSITORY_ROOT))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
    arguments = ["verify", "--conformance", "--lang", "rust", *PROJECT_FIXTURES]
    result = runner.invoke(cli.app, arguments)
    words = [line.split() for line in result.output.splitlines()]
    rows = [row for row in words if row[:1] and row[0] in PROJECT_FIXTURES]
    assert (result.exit_code, rows) == (
        ExitCode.SUCCESS,
        [[slug, "rs", "ok"] for slug in PROJECT_FIXTURES],
    )
