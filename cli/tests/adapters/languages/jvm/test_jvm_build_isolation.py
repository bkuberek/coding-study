"""Concurrent `cstudy` processes on one workspace (docs/specs/runners.md#jvm-build-details).

A fake Gradle that builds like `-Pcs.only` (the output directory keeps the requested problem's class
only) stands in for the real one; `test_jvm_end_to_end.py` repeats the scenario with real Gradle.
Separate `JvmRunner`s on one workspace root stand in for separate processes: `flock` locks conflict
between file descriptors, whether they belong to one process or to two.
"""

import fcntl
import os
import sys
import threading
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import GradleOutcome
from coding_study.adapters.languages.jvm.reference_build import ReferenceBuild
from coding_study.adapters.languages.jvm.run_classes import (
    RUNS_DIRECTORY,
    RunClasses,
    remove_abandoned_runs,
)
from coding_study.adapters.languages.jvm.runner import (
    LOCKS_DIRECTORY,
    PRACTICE_LOCK,
    REFERENCES_LOCK,
    WAIT_NOTICE,
    JvmRunner,
)
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    Prepared,
    PrepareResult,
    References,
    UserCode,
)
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import RunRequest
from tests.adapters.languages.jvm.fake_gradle import (
    CLASS_FILE,
    ClassBuildingGradle,
    reference_sources,
)
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
THREE_SUM = replace(TWO_SUM, slug="three-sum")
FAKE_RUNNER = Path(__file__).resolve().parents[3] / "fixtures" / "fake_runner.py"
ENDED_PROCESS_ID = 2**22 + 12345
"""Above the largest process id Linux hands out, and macOS's."""
WAIT_SECONDS = 10.0


def runner_on(root: Path, language: Language, gradle: ClassBuildingGradle) -> JvmRunner:
    return JvmRunner(LanguageContext(root, root / "runners"), language, gradle)


def references(directory: Path, meta: ProblemMeta, language: Language) -> References:
    return References(meta, reference_sources(directory / meta.slug, language, "hash-map"))


def prepare(runner: JvmRunner, scope: References | UserCode | BenchCode) -> PrepareResult:
    return runner.prepare(scope, lambda _line: None)


def prepared(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared), result
    return result


def classpath(result: PrepareResult) -> list[Path]:
    command = prepared(result).launch.command
    return [Path(entry) for entry in command[command.index("-cp") + 1].split(os.pathsep)]


def lock_held(lock: Path) -> bool:
    lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(descriptor)
    return False


def lock_path(root: Path, project: str, language: Language) -> Path:
    return root / LOCKS_DIRECTORY / f"{project}-{language}.lock"


def runs(root: Path) -> list[Path]:
    directory = root / RUNS_DIRECTORY
    return sorted(directory.iterdir()) if directory.is_dir() else []


# The lock covers everything that touches the shared project.


def test_reference_sources_build_and_copy_happen_under_the_lock(root, tmp_path, monkeypatch):
    lock = lock_path(root, REFERENCES_LOCK, Language.JAVA)
    held: dict[str, bool] = {}
    write, copy = ReferenceBuild.materialize, RunClasses.isolate

    def writing(*arguments, **keywords):
        held["write"] = lock_held(lock)
        return write(*arguments, **keywords)

    def copying(*arguments, **keywords):
        held["copy"] = lock_held(lock)
        return copy(*arguments, **keywords)

    monkeypatch.setattr(ReferenceBuild, "materialize", writing)
    monkeypatch.setattr(RunClasses, "isolate", copying)
    gradle = ClassBuildingGradle(root, on_build=lambda: held.update(build=lock_held(lock)))
    prepare(runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA))
    assert held == {"write": True, "build": True, "copy": True}


def test_user_code_build_and_copy_happen_under_the_lock(root, monkeypatch):
    lock = lock_path(root, PRACTICE_LOCK, Language.JAVA)
    held: dict[str, bool] = {}
    copy = RunClasses.isolate

    def copying(*arguments, **keywords):
        held["copy"] = lock_held(lock)
        return copy(*arguments, **keywords)

    monkeypatch.setattr(RunClasses, "isolate", copying)
    gradle = ClassBuildingGradle(root, on_build=lambda: held.update(build=lock_held(lock)))
    prepare(runner_on(root, Language.JAVA, gradle), UserCode(TWO_SUM))
    assert held == {"build": True, "copy": True}


def test_the_lock_is_released_when_prepare_returns(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    prepare(runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA))
    assert not lock_held(lock_path(root, REFERENCES_LOCK, Language.JAVA))


def test_the_lock_is_released_when_the_build_cannot_run(root, tmp_path):
    gradle = ClassBuildingGradle(root, outcome=GradleOutcome(1, "Could not resolve cs:runner."))
    with pytest.raises(RunnerStartError):
        prepare(
            runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
        )
    assert not lock_held(lock_path(root, REFERENCES_LOCK, Language.JAVA))


def test_references_and_user_code_use_different_locks(root):
    assert lock_path(root, REFERENCES_LOCK, Language.JAVA) != lock_path(
        root, PRACTICE_LOCK, Language.JAVA
    )


# The launch loads its own copy of the classes.


def test_the_launch_does_not_load_classes_from_the_shared_build_directory(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    result = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    shared = root / ".cs" / "build" / "jvm" / "java" / "build"
    assert not any(entry.is_relative_to(shared) for entry in classpath(result))


def test_the_private_copy_holds_the_built_classes(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    result = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    assert (classpath(result)[0] / "two_sum" / CLASS_FILE).is_file()


def test_the_private_copy_lies_in_the_launch_scratch_directory(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    result = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    [classes, _] = classpath(result)
    assert classes.parent == prepared(result).launch.scratch


def test_the_user_code_launch_loads_a_private_copy_too(root):
    result = prepare(runner_on(root, Language.JAVA, ClassBuildingGradle(root)), UserCode(TWO_SUM))
    [classes, _] = classpath(result)
    assert classes.parent == prepared(result).launch.scratch


def test_jars_stay_where_gradle_put_them(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    result = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    assert classpath(result)[1] == Path("/runner.jar")


def test_a_later_build_for_another_problem_leaves_the_earlier_launch_its_classes(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    first = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    prepare(runner_on(root, Language.JAVA, gradle), references(tmp_path, THREE_SUM, Language.JAVA))
    assert (classpath(first)[0] / "two_sum" / CLASS_FILE).is_file()


def test_a_bench_launch_loads_private_copies_of_both_builds(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    sources = references(tmp_path, TWO_SUM, Language.JAVA).sources
    result = prepare(
        runner_on(root, Language.JAVA, gradle), BenchCode(TWO_SUM, sources, references_only=False)
    )
    [user, _, reference, _] = classpath(result)
    assert user.parent == reference.parent == prepared(result).launch.scratch


def test_the_copy_is_removed_when_the_run_ends(root, tmp_path):
    gradle = ClassBuildingGradle(root)
    result = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    fake = replace(prepared(result).launch, command=(sys.executable, str(FAKE_RUNNER)))
    SubprocessRunner(root / ".cs" / "runs").run(fake, RunRequest(()))
    assert runs(root) == []


# A preparation that fails leaves nothing behind.


def test_an_environment_error_leaves_no_copy(root, tmp_path):
    gradle = ClassBuildingGradle(root, outcome=GradleOutcome(1, "Could not resolve cs:runner."))
    with pytest.raises(RunnerStartError):
        prepare(
            runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
        )
    assert runs(root) == []


class FailingUserBuild(ClassBuildingGradle):
    """Builds the references, then fails to compile the user's file."""

    def __init__(self, root: Path, error: str):
        super().__init__(root)
        self._error = error

    def run(self, arguments: Sequence[str]) -> GradleOutcome:
        if "-p" in arguments:
            return super().run(arguments)
        return GradleOutcome(1, f"{self._error}\n")


def bench_with_a_failing_user_build(root: Path, tmp_path: Path) -> PrepareResult:
    error = f"{root}/jvm/java/src/main/java/practice/two_sum/Solution.java:4: error: x"
    sources = references(tmp_path, TWO_SUM, Language.JAVA).sources
    return prepare(
        runner_on(root, Language.JAVA, FailingUserBuild(root, error)),
        BenchCode(TWO_SUM, sources, references_only=False),
    )


def test_a_user_build_failure_after_the_reference_build_is_a_build_failure(root, tmp_path):
    assert isinstance(bench_with_a_failing_user_build(root, tmp_path), BuildFailed)


def test_a_user_build_failure_after_the_reference_build_leaves_no_copy(root, tmp_path):
    bench_with_a_failing_user_build(root, tmp_path)
    assert runs(root) == []


# Runs that ended without cleaning up (killed) are removed by the next preparation.


def test_the_runs_of_ended_processes_are_removed(tmp_path):
    abandoned = tmp_path / f"{ENDED_PROCESS_ID}-abc"
    abandoned.mkdir()
    remove_abandoned_runs(tmp_path)
    assert not abandoned.exists()


def test_the_runs_of_live_processes_are_kept(tmp_path):
    live = tmp_path / f"{os.getpid()}-abc"
    live.mkdir()
    remove_abandoned_runs(tmp_path)
    assert live.is_dir()


def test_directories_that_are_not_runs_are_kept(tmp_path):
    other = tmp_path / "notes"
    other.mkdir()
    remove_abandoned_runs(tmp_path)
    assert other.is_dir()


def test_a_preparation_removes_the_runs_of_ended_processes(root):
    abandoned = root / RUNS_DIRECTORY / f"{ENDED_PROCESS_ID}-abc"
    abandoned.mkdir(parents=True)
    prepare(runner_on(root, Language.JAVA, ClassBuildingGradle(root)), UserCode(TWO_SUM))
    assert not abandoned.exists()


# Two processes on one workspace take turns; Java and Kotlin do not wait for each other.


def test_builds_of_two_processes_never_overlap(root, tmp_path):
    gradle = ClassBuildingGradle(root, pause=0.05)

    def build(meta: ProblemMeta) -> PrepareResult:
        runner = runner_on(root, Language.JAVA, gradle)
        return prepare(runner, references(tmp_path, meta, Language.JAVA))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(build, [TWO_SUM, THREE_SUM]))
    assert gradle.most_running == 1


def test_each_of_two_processes_keeps_the_classes_it_built(root, tmp_path):
    gradle = ClassBuildingGradle(root, pause=0.05)

    def build(meta: ProblemMeta) -> bool:
        runner = runner_on(root, Language.JAVA, gradle)
        result = prepare(runner, references(tmp_path, meta, Language.JAVA))
        return (classpath(result)[0] / meta.snake_slug / CLASS_FILE).is_file()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(build, [TWO_SUM, THREE_SUM])) == [True, True]


def test_java_and_kotlin_build_at_the_same_time_once_the_runner_jars_are_current(root, tmp_path):
    prepare(
        runner_on(root, Language.JAVA, RuntimeJarGradle(root)),
        references(tmp_path, TWO_SUM, Language.JAVA),
    )
    both_building = threading.Barrier(2, timeout=WAIT_SECONDS)
    gradle = RuntimeJarGradle(root, on_build=both_building.wait)

    def build(language: Language) -> PrepareResult:
        return prepare(runner_on(root, language, gradle), references(tmp_path, TWO_SUM, language))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(build, [Language.JAVA, Language.KOTLIN]))
    assert all(isinstance(result, Prepared) for result in results)


# Every JVM build may rebuild the runtime's runner and support jars, in place.


class RuntimeJarGradle(ClassBuildingGradle):
    """Also rewrites the runtime's runner jar, as Gradle does when the runner's sources changed:
    its content names the build that wrote it."""

    def build_classes(self, project: Path, language: Language, slug: str) -> str:
        classes = super().build_classes(project, language, slug).split(":")[0]
        jar = runtime_jar(self.root)
        jar.parent.mkdir(parents=True, exist_ok=True)
        jar.write_text(f"built for {slug}")
        return f"{classes}:{jar}"


def runtime_jar(root: Path) -> Path:
    return root / "runners" / "jvm" / "runner" / "build" / "libs" / "runner.jar"


def change_runtime_source(root: Path, text: str) -> None:
    source = root / "runners" / "jvm" / "runner" / "src" / "Main.java"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text)


def build_side_by_side(root: Path, tmp_path: Path, gradle: ClassBuildingGradle) -> None:
    def build(language: Language) -> PrepareResult:
        return prepare(runner_on(root, language, gradle), references(tmp_path, TWO_SUM, language))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(build, [Language.JAVA, Language.KOTLIN]))


def test_a_launch_loads_a_private_copy_of_the_runtime_jars(root, tmp_path):
    result = prepare(
        runner_on(root, Language.JAVA, RuntimeJarGradle(root)),
        references(tmp_path, TWO_SUM, Language.JAVA),
    )
    assert classpath(result)[1].parent == prepared(result).launch.scratch


def test_a_later_build_that_rewrites_the_runner_jar_leaves_the_earlier_launch_its_jar(
    root, tmp_path
):
    gradle = RuntimeJarGradle(root)
    first = prepare(
        runner_on(root, Language.JAVA, gradle), references(tmp_path, TWO_SUM, Language.JAVA)
    )
    prepare(runner_on(root, Language.JAVA, gradle), references(tmp_path, THREE_SUM, Language.JAVA))
    assert classpath(first)[1].read_text() == "built for two_sum"


def test_the_first_builds_of_java_and_kotlin_take_turns(root, tmp_path):
    change_runtime_source(root, "class Main {}")
    gradle = RuntimeJarGradle(root, pause=0.05)
    build_side_by_side(root, tmp_path, gradle)
    assert gradle.most_running == 1


def test_builds_take_turns_again_after_the_runtime_sources_change(root, tmp_path):
    change_runtime_source(root, "class Main {}")
    build_side_by_side(root, tmp_path, RuntimeJarGradle(root))
    change_runtime_source(root, "class Main { int changed; }")
    gradle = RuntimeJarGradle(root, pause=0.05)
    build_side_by_side(root, tmp_path, gradle)
    assert gradle.most_running == 1


def test_builds_take_turns_again_when_a_runner_jar_is_gone(root, tmp_path):
    change_runtime_source(root, "class Main {}")
    build_side_by_side(root, tmp_path, RuntimeJarGradle(root))
    runtime_jar(root).unlink()
    gradle = RuntimeJarGradle(root, pause=0.05)
    build_side_by_side(root, tmp_path, gradle)
    assert gradle.most_running == 1


@dataclass(frozen=True, slots=True)
class WaitingBuild:
    notices: list[str]
    built_while_locked: bool
    result: PrepareResult


@pytest.fixture
def waiting_build(root: Path, tmp_path: Path) -> WaitingBuild:
    """A reference build that starts while another process holds the lock, until it prints."""
    notices: list[str] = []
    gradle = ClassBuildingGradle(root)
    runner = runner_on(root, Language.JAVA, gradle)
    scope = references(tmp_path, TWO_SUM, Language.JAVA)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with exclusive_lock(lock_path(root, REFERENCES_LOCK, Language.JAVA)):
            waiting = pool.submit(runner.prepare, scope, notices.append)
            deadline = time.monotonic() + WAIT_SECONDS
            while not notices and time.monotonic() < deadline:
                time.sleep(0.01)
            built_while_locked = bool(gradle.builds)
        return WaitingBuild(notices, built_while_locked, waiting.result(timeout=WAIT_SECONDS))


def test_a_process_waiting_for_the_lock_says_so(waiting_build):
    assert waiting_build.notices == [WAIT_NOTICE]


def test_a_process_waiting_for_the_lock_does_not_build_meanwhile(waiting_build):
    assert not waiting_build.built_while_locked


def test_a_process_waiting_for_the_lock_builds_once_it_is_free(waiting_build):
    assert isinstance(waiting_build.result, Prepared)
