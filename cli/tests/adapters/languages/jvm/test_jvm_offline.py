"""Java and Kotlin build offline once `cstudy doctor --fix` has run on a fresh Gradle home (NFR-6):
single-file problems, and project folders, whose libraries the warm-up projects cache, the coroutine
libraries of a Kotlin project on the virtual clock included.

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
from coding_study.domain.problem import Language
from coding_study.domain.project_checks import jvm_build_files
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import TEST_VERSION

pytestmark = [pytest.mark.slow, pytest.mark.jvm]

DISTRIBUTIONS = Path("wrapper") / "dists"
PROJECTS = Path(__file__).resolve().parents[3] / "fixtures" / "jvm-projects" / "problems"
OFFLINE_SLUG = "offline_check"
"""Names no practice package, and differs from the warm-up's, so the build resolves again."""
CLOCK_PROJECT = "clock-project-kotlin"
CLOCK_SOURCES = {
    "src/main/kotlin/clock/Timer.kt": """\
package clock

import kotlinx.coroutines.delay

class Timer {
    suspend fun wait(ms: Long): Long {
        delay(ms)
        return ms
    }
}
""",
    "src/test/kotlin/clock/TimerTest.kt": """\
package clock

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.test.runTest

class TimerTest {
    @Test
    fun waits() = runTest {
        assertEquals(5L, Timer().wait(5))
    }
}
""",
}
COROUTINE_LIBRARIES = (
    "kotlinx-coroutines-core-jvm-1.11.0.jar",
    "kotlinx-coroutines-test-jvm-1.11.0.jar",
)


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


def test_a_kotlin_project_on_the_virtual_clock_builds_offline_after_the_warm_up(
    warmed_up: OfflineWorkspace,
):
    """Its code suspends and its test runs on `runTest`: the `cs.coroutines` plugin's libraries,
    which the Kotlin warm-up project cached."""
    folder = warmed_up.root / "projects" / CLOCK_PROJECT
    files = {**jvm_build_files(CLOCK_PROJECT, Language.KOTLIN, virtual_clock=True), **CLOCK_SOURCES}
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    built = warmed_up.gradle("-p", str(folder), "--offline", "-q", "csClasspath")
    assert built.returncode == 0, built.stdout + built.stderr
    classpath = (folder / "build" / "cs" / "test-classpath.txt").read_text()
    names = {Path(entry).name for entry in classpath.strip().split(os.pathsep)}
    assert set(COROUTINE_LIBRARIES) <= names
