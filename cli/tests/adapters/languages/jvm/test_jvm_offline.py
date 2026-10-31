"""Java and Kotlin build offline once `cstudy doctor --fix` has run on a fresh Gradle home (NFR-6):
single-file problems, and project folders, whose libraries the warm-up projects cache.

Marked `slow`: the warm-up downloads what an empty Gradle home lacks, so it needs the network once.
The Gradle distribution is linked from the user's Gradle home, since the wrapper would download
that same one, and the module stops its own daemon at the end.
"""

import os
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from coding_study.adapters.languages.jvm.gradle import default_gradle_user_home
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.application.doctor import JVM_FIX, JVM_PROJECT_WARMUPS
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import TEST_VERSION

pytestmark = pytest.mark.slow

DISTRIBUTIONS = Path("wrapper") / "dists"
PROJECTS = Path(__file__).resolve().parents[3] / "fixtures" / "jvm-projects" / "problems"
OFFLINE_SLUG = "offline_check"
"""Names no practice package, and differs from the warm-up's, so the build resolves again."""


@dataclass(frozen=True, slots=True)
class OfflineWorkspace:
    root: Path
    environment: dict[str, str]
    """The process environment with `GRADLE_USER_HOME` set to the fresh home."""

    def gradle(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("./gradlew", *arguments),
            cwd=self.root / "jvm",
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )


@pytest.fixture(scope="module")
def warmed_up(tmp_path_factory: pytest.TempPathFactory) -> Iterator[OfflineWorkspace]:
    """A new workspace whose JVM projects ran the doctor's warm-up on an empty Gradle home."""
    root = tmp_path_factory.mktemp("offline-workspace")
    home = tmp_path_factory.mktemp("gradle-home")
    (home / DISTRIBUTIONS).parent.mkdir()
    shared = default_gradle_user_home() / DISTRIBUTIONS
    (home / DISTRIBUTIONS).symlink_to(shared, target_is_directory=True)
    setup = FsWorkspaceSetup(REPOSITORY_ROOT / "runners", TEST_VERSION)
    setup.write_missing(root)
    setup.refresh_runtime(root)
    workspace = OfflineWorkspace(root, {**os.environ, "GRADLE_USER_HOME": str(home)})
    for step in (JVM_FIX, *JVM_PROJECT_WARMUPS):
        subprocess.run(
            step.command,
            cwd=root / step.project,
            env=workspace.environment,
            capture_output=True,
            check=True,
        )
    yield workspace
    workspace.gradle("--stop")


@pytest.mark.parametrize("language", ["java", "kotlin"])
def test_a_single_file_problem_builds_offline_after_the_warm_up(
    warmed_up: OfflineWorkspace, language: str
):
    built = warmed_up.gradle(
        "--offline", "-q", f":{language}:csClasspath", f"-Pcs.only={OFFLINE_SLUG}"
    )
    assert built.returncode == 0, built.stdout + built.stderr


@pytest.mark.parametrize("problem", ["0001-bank-project-java", "0002-bank-project-kotlin"])
def test_a_project_folder_builds_offline_after_the_warm_up(warmed_up: OfflineWorkspace, problem):
    """Its main and test classes, against JUnit and kotlin-test, with no network."""
    folder = warmed_up.root / "projects" / problem
    shutil.copytree(PROJECTS / problem / "starter", folder)
    built = warmed_up.gradle("-p", str(folder), "--offline", "-q", "csClasspath")
    assert built.returncode == 0, built.stdout + built.stderr
