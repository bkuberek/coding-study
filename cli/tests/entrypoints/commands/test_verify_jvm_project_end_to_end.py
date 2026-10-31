"""`cstudy verify` on a Java project problem through real Gradle: the builds it keeps in
`.cs/build/projects/` and `.cs/build/stubs/projects/` stay incremental between runs
(docs/specs/runners.md#reference-materialization).

Marked `slow`. The content root is temporary (the Java project fixture problem and a link to the
real `runners/`), and the workspace is a copy of the session's practice workspace, whose Gradle
daemon and cached project libraries it shares.
"""

import os
import shutil
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "jvm-projects" / "problems"
SLUG = "bank-project-java"
INCREMENTAL_SHARE = 0.75
"""A second run may take at most this share of the first. Rebuilt from empty folders, a second run
measured about 0.8 of the first (the Gradle daemon is warmer by then); synced, under 0.5."""


@pytest.fixture
def content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(FIXTURES, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture
def verify(
    content: Path, practice_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], float]:
    """Runs `cstudy verify` on the project, which must pass; returns the seconds it took."""
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))

    def timed() -> float:
        started = time.perf_counter()
        result = runner.invoke(cli.app, ["verify", SLUG])
        seconds = time.perf_counter() - started
        assert result.exit_code == ExitCode.SUCCESS, result.output
        return seconds

    return timed


def test_a_second_verify_builds_incrementally(verify):
    first = verify()
    second = verify()
    load = ", ".join(f"{average:.1f}" for average in os.getloadavg())
    timings = f"first {first:.1f} s, second {second:.1f} s, load averages {load}"
    print(timings)
    assert second < first * INCREMENTAL_SHARE, timings
