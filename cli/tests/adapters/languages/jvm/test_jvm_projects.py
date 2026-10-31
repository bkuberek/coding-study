"""Building and launching a Java or Kotlin project folder
(docs/specs/runners.md#jvm-project-builds).

A fake Gradle builds like the `cs.project` plugin; test_jvm_project_end_to_end.py drives the real
one. Separate `JvmRunner`s on one workspace root stand in for separate `cstudy` processes.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import GradleOutcome
from coding_study.adapters.languages.jvm.runner import (
    COLD_DAEMON_NOTICE,
    JDWP_LISTENING_MARKER,
    MAIN_CLASS,
    MISSING_LIBRARIES,
    WARMUP_CLASSPATH,
    JvmRunner,
)
from coding_study.application.ports import (
    BuildFailed,
    ProjectGrading,
    ProjectScope,
    ProjectSuite,
    RunnerLaunch,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.project_checks import jvm_build_files
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.adapters.languages.jvm.fake_gradle import LIBRARY, ProjectGradle
from tests.helpers import REPOSITORY_ROOT

GRADLE_FLAGS = ["-q", "--console=plain", "--offline"]
OFFLINE_FAILURE = """\
* What went wrong:
Could not resolve all dependencies for configuration ':testRuntimeClasspath'.
   > No cached version of org.junit:junit-bom:5.14.4 available for offline mode.
"""


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    project = tmp_path / "projects" / "bank-project-java"
    project.mkdir(parents=True)
    return project


def runner_on(root: Path, gradle: ProjectGradle, language: Language = Language.JAVA) -> JvmRunner:
    return JvmRunner(LanguageContext(root, root / "runners"), language, gradle)


def prepare(
    runner: JvmRunner, scope: ProjectScope, notices: list[str] | None = None
) -> RunnerLaunch | BuildFailed:
    return runner.prepare_project(scope, (notices if notices is not None else []).append)


def launched(result: RunnerLaunch | BuildFailed) -> RunnerLaunch:
    assert isinstance(result, RunnerLaunch), result
    return result


def classpath(launch: RunnerLaunch) -> list[str]:
    command = list(launch.command)
    return command[command.index("-cp") + 1].split(os.pathsep)


def compile_failure(*lines: str) -> GradleOutcome:
    return GradleOutcome(1, "\n".join(("> Task :compileJava FAILED", *lines, "BUILD FAILED")))


# the build


def test_a_suite_builds_the_folder_offline_with_its_test_classes(tmp_path, folder):
    gradle = ProjectGradle()
    prepare(runner_on(tmp_path, gradle), ProjectSuite(folder))
    assert gradle.builds == [("-p", str(folder), *GRADLE_FLAGS, "csClasspath")]


def test_grading_builds_the_main_classes_only(tmp_path, folder):
    """A test file that does not compile never blocks a submission."""
    gradle = ProjectGradle()
    prepare(runner_on(tmp_path, gradle), ProjectGrading(folder))
    assert gradle.builds == [("-p", str(folder), *GRADLE_FLAGS, "csMainClasspath")]


def test_the_test_files_of_locked_levels_are_left_out_of_the_build(tmp_path, folder):
    gradle = ProjectGradle()
    excluded = ("src/test/java/bank/Level2Test.java", "src/test/java/bank/Level3Test.java")
    prepare(runner_on(tmp_path, gradle), ProjectSuite(folder, exclude=excluded))
    assert gradle.builds[0][-1] == f"-Pcs.exclude={','.join(excluded)}"


def test_kotlin_builds_its_folder_the_same_way(tmp_path, folder):
    gradle = ProjectGradle()
    prepare(runner_on(tmp_path, gradle, Language.KOTLIN), ProjectSuite(folder))
    assert gradle.builds == [("-p", str(folder), *GRADLE_FLAGS, "csClasspath")]


def test_a_cold_daemon_prints_the_warm_up_notice(tmp_path, folder):
    notices: list[str] = []
    prepare(runner_on(tmp_path, ProjectGradle(warm=False)), ProjectSuite(folder), notices)
    assert notices == [COLD_DAEMON_NOTICE]


def test_builds_of_one_folder_take_turns(tmp_path, folder):
    gradle = ProjectGradle(pause=0.2)
    runners = [runner_on(tmp_path, gradle) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda runner: prepare(runner, ProjectSuite(folder)), runners))
    assert gradle.most_running == 1


def test_builds_of_two_folders_run_side_by_side(tmp_path, folder):
    """Once a first build recorded the runtime's jars; the builds after a change take turns."""
    other = folder.parent / "inventory-project-java"
    other.mkdir()
    gradle = ProjectGradle(pause=0.3)
    runners = [runner_on(tmp_path, gradle) for _ in range(2)]
    prepare(runners[0], ProjectSuite(folder))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(prepare, runners, [ProjectSuite(folder), ProjectSuite(other)]))
    assert gradle.most_running == 2


# the launch


def test_the_runner_starts_in_the_project_root(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectSuite(folder)))
    assert (launch.cwd, launch.command[-1]) == (folder, MAIN_CLASS)


def test_the_launch_uses_the_jvm_hello_timeout(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectGrading(folder)))
    assert launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.JAVA]


def test_a_suite_runs_on_the_test_runtime_classpath(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectSuite(folder)))
    entries = classpath(launch)
    assert [Path(entry).name for entry in entries[:2]] == ["0-java-test", "1-java-main"]


def test_grading_runs_on_the_main_runtime_classpath(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectGrading(folder)))
    assert [Path(entry).name for entry in classpath(launch)] == ["0-java-main", Path(LIBRARY).name]


def test_the_runner_loads_a_private_copy_of_the_built_classes(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectSuite(folder)))
    assert launch.scratch is not None
    assert all(Path(entry).is_relative_to(launch.scratch) for entry in classpath(launch)[:2])


def test_libraries_in_gradles_cache_keep_their_path(tmp_path, folder):
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectSuite(folder)))
    assert classpath(launch)[-1] == LIBRARY


def test_a_debugged_suite_waits_for_the_ide(tmp_path, folder):
    session = DebugSession(Language.JAVA, 0)
    launch = launched(prepare(runner_on(tmp_path, ProjectGradle()), ProjectSuite(folder, session)))
    assert launch.debug is not None
    assert launch.debug.ready_marker == JDWP_LISTENING_MARKER
    assert any(part.startswith("-agentlib:jdwp=") for part in launch.command)


# failures


def test_code_that_does_not_compile_is_a_build_failure(tmp_path, folder):
    error = f"{folder.resolve()}/src/main/java/bank/Bank.java:3: error: ';' expected"
    gradle = ProjectGradle(outcome=compile_failure(error, "        int x", "             ^"))
    result = prepare(runner_on(tmp_path, gradle), ProjectGrading(folder))
    assert result == BuildFailed(
        ("src/main/java/bank/Bank.java:3: error: ';' expected", "        int x", "             ^")
    )


def test_compiler_lines_are_kept_once(tmp_path, folder):
    """Gradle repeats them, indented, under `What went wrong`."""
    error = f"{folder.resolve()}/src/main/java/bank/Bank.java:3: error: ';' expected"
    output = "\n".join((error, "* What went wrong:", f"  {error}", "  1 error"))
    gradle = ProjectGradle(outcome=GradleOutcome(1, output))
    result = prepare(runner_on(tmp_path, gradle), ProjectGrading(folder))
    assert result == BuildFailed(("src/main/java/bank/Bank.java:3: error: ';' expected",))


def test_kotlin_compiler_lines_name_the_file_by_its_url(tmp_path, folder):
    error = f"e: file://{folder.resolve()}/src/main/kotlin/bank/Bank.kt:1:31 Return type mismatch."
    gradle = ProjectGradle(outcome=compile_failure(error))
    result = prepare(runner_on(tmp_path, gradle, Language.KOTLIN), ProjectSuite(folder))
    assert result == BuildFailed(("e: src/main/kotlin/bank/Bank.kt:1:31 Return type mismatch.",))


def test_a_build_failure_leaves_no_private_copy(tmp_path, folder):
    error = f"{folder.resolve()}/src/main/java/bank/Bank.java:3: error: ';' expected"
    prepare(
        runner_on(tmp_path, ProjectGradle(outcome=compile_failure(error))), ProjectSuite(folder)
    )
    runs = tmp_path / ".cs" / "build" / "jvm-runs"
    assert not runs.exists() or not any(runs.iterdir())


def test_libraries_missing_offline_name_the_doctor(tmp_path, folder):
    gradle = ProjectGradle(outcome=GradleOutcome(1, OFFLINE_FAILURE))
    with pytest.raises(RunnerStartError, match="cstudy doctor --fix") as raised:
        prepare(runner_on(tmp_path, gradle), ProjectSuite(folder))
    assert str(raised.value).startswith(MISSING_LIBRARIES)


def warmed_up(tmp_path: Path, language: Language, *entries: Path) -> None:
    """The classpath file the warm-up project's build wrote, naming `entries`."""
    output = tmp_path / "runners" / "jvm" / "project-warmup" / language / WARMUP_CLASSPATH
    output.parent.mkdir(parents=True)
    output.write_text(os.pathsep.join(str(entry) for entry in entries) + "\n")


def test_libraries_are_uncached_until_the_warm_up_project_built(tmp_path):
    runner = runner_on(tmp_path, ProjectGradle(), Language.KOTLIN)
    assert runner.uncached_project_libraries() == (
        "the kotlin warm-up project has not built yet (it caches what project folders build with)"
    )


def test_libraries_are_cached_while_the_warm_ups_classpath_exists(tmp_path):
    jar = tmp_path / "caches" / "junit-jupiter-5.14.4.jar"
    jar.parent.mkdir()
    jar.write_text("jar")
    warmed_up(tmp_path, Language.JAVA, jar)
    assert runner_on(tmp_path, ProjectGradle()).uncached_project_libraries() is None


def test_libraries_removed_from_gradles_cache_are_uncached(tmp_path):
    gone = tmp_path / "caches" / "kotlin-test-junit5-2.4.21.jar"
    warmed_up(tmp_path, Language.JAVA, gone, tmp_path / "caches" / "opentest4j-1.3.0.jar")
    assert runner_on(tmp_path, ProjectGradle()).uncached_project_libraries() == (
        "2 libraries the java warm-up project built with are gone, such as "
        "kotlin-test-junit5-2.4.21.jar"
    )


def test_directories_the_build_never_made_are_no_libraries(tmp_path):
    """Gradle names `build/resources/test` on the classpath whether or not it exists."""
    warmed_up(tmp_path, Language.JAVA, tmp_path / "build" / "resources" / "test")
    assert runner_on(tmp_path, ProjectGradle()).uncached_project_libraries() is None


def test_any_other_failure_is_an_environment_error_with_gradles_output(tmp_path, folder):
    gradle = ProjectGradle(outcome=GradleOutcome(1, "Daemon died unexpectedly"))
    with pytest.raises(RunnerStartError, match="gradle build failed with exit code 1") as raised:
        prepare(runner_on(tmp_path, gradle), ProjectSuite(folder))
    assert raised.value.stderr_tail == ("Daemon died unexpectedly",)


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_warm_up_project_builds_like_any_project_folder(language):
    """It caches exactly what a folder needs only while its build files are the template's."""
    folder = REPOSITORY_ROOT / "runners" / "jvm" / "project-warmup" / language
    expected = jvm_build_files(f"project-warmup-{language}", language)
    assert {path: (folder / path).read_text() for path in expected} == expected
