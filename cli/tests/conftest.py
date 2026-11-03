import os
import shutil
from pathlib import Path

import pytest

from tests.helpers import FIXTURE_PROBLEMS, SCHEMAS_DIRECTORY
from tests.workspaces import set_up_workspace

GRADLE_DAEMON_IDLE_MS = 60_000
"""The slow tests start Gradle daemons that would otherwise idle for three hours after the run."""
os.environ["GRADLE_OPTS"] = (
    f"{os.environ.get('GRADLE_OPTS', '')} -Dorg.gradle.daemon.idletimeout={GRADLE_DAEMON_IDLE_MS}"
).strip()


@pytest.fixture
def content_root(tmp_path: Path) -> Path:
    """A content root holding the real schemas and copies of the fixture problems."""
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    shutil.copytree(FIXTURE_PROBLEMS, tmp_path / "problems")
    return tmp_path


@pytest.fixture(scope="session")
def practice_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real, set-up workspace outside the repository, shared by the slow tests."""
    return set_up_workspace(tmp_path_factory.mktemp("practice-workspace"))
