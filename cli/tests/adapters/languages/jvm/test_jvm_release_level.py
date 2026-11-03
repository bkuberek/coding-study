"""Java and Kotlin compile with the selected JDK, with no toolchain, at one release level: the
feature release of that JDK, capped at the newest supported one, unless `cs.release` names another
(docs/specs/runners.md#the-jdk-and-the-release-level).

Marked `slow`: real Gradle builds on the JDK this process selects. Run them once per JDK to cover
the range: on JDK 21 the classes are of major version 65, on JDK 26 of 70, and on a JDK above the
range of 70 still.
"""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.jdk_locator import shell_jdk
from coding_study.adapters.languages.jvm.gradle import (
    GradleOutcome,
    WrapperGradle,
    default_gradle_user_home,
)
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.domain.jdk import SUPPORTED_JDKS
from coding_study.domain.problem import Language
from tests.workspaces import workspace_like

pytestmark = [pytest.mark.slow, pytest.mark.jvm]

JVM_LANGUAGES = (Language.JAVA, Language.KOTLIN)
CLASS_FILE_MAJOR_OF_RELEASE_0 = 44
"""A class file of release N has major version N + 44: 65 for 21, 70 for 26."""
PROBE = "release_probe"
SOURCES = {
    Language.JAVA: (
        "java/src/main/java/practice/release_probe/Solution.java",
        "package practice.release_probe;\n\npublic class Solution {\n}\n",
    ),
    Language.KOTLIN: (
        "kotlin/src/main/kotlin/practice/release_probe/Solution.kt",
        "package practice.release_probe\n\nclass Solution\n",
    ),
}
NEWER_API_SOURCES = {
    Language.JAVA: (
        "package practice.release_probe;\n\nimport java.util.stream.Gatherers;\n\n"
        "public class Solution {\n    Object windows = Gatherers.windowFixed(2);\n}\n"
    ),
    Language.KOTLIN: (
        "package practice.release_probe\n\nimport java.util.stream.Gatherers\n\n"
        "class Solution {\n    val windows = Gatherers.windowFixed<Int>(2)\n}\n"
    ),
}
"""Stream gatherers became final in JDK 24."""
CLASS_DIRECTORIES = {Language.JAVA: "classes/java/main", Language.KOTLIN: "classes/kotlin/main"}
WARMUP_PROJECTS = Path("jvm") / "project-warmup"
WARMUP_CLASS = "warmup/Counter.class"
SUPPORT_CLASS = Path("jvm/support/build/classes/java/main/cs/support/ListNode.class")
GRADLE_FLAGS = ("-q", "--console=plain", "--no-watch-fs")


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("release-level") / "ws")


@pytest.fixture(params=JVM_LANGUAGES, ids=str)
def language(request: pytest.FixtureRequest) -> Language:
    return request.param


def gradle(root: Path) -> WrapperGradle:
    return WrapperGradle(root / "jvm", default_gradle_user_home(), shell_jdk())


def selected_jdks_level() -> int:
    selected = shell_jdk().selected()
    assert selected is not None, "these tests need a JDK: set JAVA_HOME or put java on PATH"
    return min(selected.feature, SUPPORTED_JDKS.maximum)


def major_version(class_file: Path) -> int:
    return int.from_bytes(class_file.read_bytes()[6:8], "big")


def build_probe(root: Path, language: Language, source: str, *properties: str) -> GradleOutcome:
    relative, _ = SOURCES[language]
    path = root / "jvm" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    task = f":{language}:csClasspath"
    return gradle(root).run([*GRADLE_FLAGS, task, f"-Pcs.only={PROBE}", *properties])


def probe_class(root: Path, language: Language) -> Path:
    build = root / "jvm" / str(language) / "build" / CLASS_DIRECTORIES[language]
    return build / "practice" / PROBE / "Solution.class"


def built_probe(root: Path, language: Language, *properties: str) -> Path:
    outcome = build_probe(root, language, SOURCES[language][1], *properties)
    assert outcome.exit_code == 0, outcome.output
    return probe_class(root, language)


def test_practice_code_compiles_at_the_selected_jdks_level(root, language):
    expected = selected_jdks_level() + CLASS_FILE_MAJOR_OF_RELEASE_0
    assert major_version(built_probe(root, language)) == expected


def test_cs_release_sets_the_level(root, language):
    minimum = SUPPORTED_JDKS.minimum
    class_file = built_probe(root, language, f"-Pcs.release={minimum}")
    assert major_version(class_file) == minimum + CLASS_FILE_MAJOR_OF_RELEASE_0


def test_an_api_newer_than_the_level_does_not_compile(root, language):
    release = f"-Pcs.release={SUPPORTED_JDKS.minimum}"
    outcome = build_probe(root, language, NEWER_API_SOURCES[language], release)
    assert "Gatherers" in outcome.output


def test_a_release_outside_the_supported_range_is_refused(root):
    outcome = build_probe(root, Language.JAVA, SOURCES[Language.JAVA][1], "-Pcs.release=17")
    assert "cs.release must be a JDK release from 21 to 26, not 17" in outcome.output


def test_a_project_folder_compiles_at_the_selected_jdks_level(root, language):
    """The warm-up project, a project folder built by the `cs.project` plugin, copied into the
    workspace so that its build is its own."""
    folder = root / "projects" / f"release-probe-{language}"
    shutil.copytree(
        root / RUNTIME_RUNNERS / WARMUP_PROJECTS / str(language),
        folder,
        ignore=shutil.ignore_patterns("build", ".gradle", ".kotlin"),
        dirs_exist_ok=True,
    )
    outcome = gradle(root).run(["-p", str(folder), *GRADLE_FLAGS, "--offline", "csClasspath"])
    assert outcome.exit_code == 0, outcome.output
    class_file = folder / "build" / CLASS_DIRECTORIES[language] / WARMUP_CLASS
    assert major_version(class_file) == selected_jdks_level() + CLASS_FILE_MAJOR_OF_RELEASE_0


def test_the_runner_classes_compile_at_the_supported_minimum(root):
    """So they load on every JDK the range or an opt-in reaches."""
    built_probe(root, Language.JAVA)
    expected = SUPPORTED_JDKS.minimum + CLASS_FILE_MAJOR_OF_RELEASE_0
    assert major_version(root / RUNTIME_RUNNERS / SUPPORT_CLASS) == expected
