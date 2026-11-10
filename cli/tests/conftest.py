import os
import shutil
from pathlib import Path

import pytest

from coding_study.adapters import docker_sandbox
from tests.helpers import FIXTURE_PROBLEMS, SCHEMAS_DIRECTORY
from tests.sandbox_fakes import DockerMissing
from tests.workspaces import set_up_workspace

GRADLE_DAEMON_IDLE_MS = 600_000
"""The slow tests start Gradle daemons that would otherwise idle for three hours after the run.

Ten minutes outlasts the gaps between JVM tests on a loaded CI runner; a daemon that exits sooner
makes `cstudy` print its first-run warm-up notice in the middle of a test."""
os.environ["GRADLE_OPTS"] = (
    f"{os.environ.get('GRADLE_OPTS', '')} -Dorg.gradle.daemon.idletimeout={GRADLE_DAEMON_IDLE_MS}"
).strip()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "docker: drives a real Docker engine, and is also slow; CI runs these in a job of its own "
        "(-m 'docker and not docker_jvm')",
    )
    config.addinivalue_line(
        "markers",
        "docker_jvm: a docker test that builds a JVM project on a real engine, about ten minutes "
        "under load; also marked docker, and run locally only: CI deselects it to keep its sandbox "
        "job under 15 minutes",
    )


@pytest.fixture(autouse=True)
def no_real_docker(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a test marked `docker` reaches a real engine; to any other, Docker is not installed."""
    if "docker" not in request.keywords:
        monkeypatch.setattr(docker_sandbox, "default_docker_runner", DockerMissing)


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
