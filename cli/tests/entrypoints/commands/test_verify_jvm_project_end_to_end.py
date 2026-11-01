"""`cstudy verify` on a Java project problem through real Gradle: the builds it keeps in
`.cs/build/projects/` and `.cs/build/stubs/projects/` stay incremental between runs
(docs/specs/runners.md#reference-materialization).

Marked `slow`. The content root is temporary (the Java project fixture problem and a link to the
real `runners/`), and the workspace is a copy of the session's practice workspace, whose Gradle
daemon and cached project libraries it shares.

Runs from empty build folders and runs over the folders an earlier run left alternate, and the
fastest of each kind counts: a busy machine only adds time, and it adds it in bursts, such as a
Gradle daemon that another build keeps busy, so a new one starts cold. The speed-up is asserted on
the time spent in Gradle, which the kept folders save; the whole run's time, mostly the runner
JVMs and the tests they run, is reported beside it.
"""

import os
import shutil
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.jvm.gradle import GradleOutcome, WrapperGradle
from coding_study.application.verify_projects import PROJECT_BUILDS, STARTER_BUILDS
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = [pytest.mark.slow, pytest.mark.jvm]

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "jvm-projects" / "problems"
SLUG = "bank-project-java"
RUNS = 3
"""Runs of each kind."""
INCREMENTAL_SHARE = 0.85
"""Gradle's time in a run over kept builds may be at most this share of its time in a run from
empty folders. Measured at load averages near 50 on 11 cores: 0.51, and 0.68 when every run still
rebuilt from empty folders; a single Gradle build of the reference took 1.5 to 3 s over kept
builds and 4 to 10 s from an empty folder. On a quiet machine (load averages 2 to 3) Gradle needs
less time from empty folders, 1.9 to 2.2 s against 1.5 s over kept builds: 0.72 to 0.75. The
class files that are not compiled again are the deterministic check."""


@dataclass(frozen=True, slots=True)
class Run:
    seconds: float
    """The whole `cstudy verify`."""
    gradle_seconds: float
    """Its Gradle builds: the starter's and the reference's, each graded and run as a suite."""


@dataclass(frozen=True, slots=True)
class Timings:
    from_empty: tuple[Run, ...]
    over_kept: tuple[Run, ...]
    classes_before: dict[str, int]
    """Modification time of every class file of the reference build, by path, after a run from
    empty folders."""
    classes_after: dict[str, int]
    """The same after the run over kept builds that followed it."""

    def summary(self) -> str:
        load = ", ".join(f"{average:.1f}" for average in os.getloadavg())
        return (
            f"from empty folders {_listed(self.from_empty)}; "
            f"over kept builds {_listed(self.over_kept)}; load averages {load}"
        )


class _GradleClock:
    """Adds up the seconds `WrapperGradle.run` takes."""

    def __init__(self, run: Callable[[WrapperGradle, Sequence[str]], GradleOutcome]) -> None:
        self._run = run
        self.seconds = 0.0

    def run(self, gradle: WrapperGradle, arguments: Sequence[str]) -> GradleOutcome:
        started = time.perf_counter()
        try:
            return self._run(gradle, arguments)
        finally:
            self.seconds += time.perf_counter() - started


@pytest.fixture(scope="module")
def timings(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Timings:
    tmp_path = tmp_path_factory.mktemp("jvm-incremental")
    content = tmp_path / "content"
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(FIXTURES, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    root = workspace_like(practice_workspace, tmp_path / "ws")
    builds = (root / PROJECT_BUILDS / SLUG, root / STARTER_BUILDS / SLUG)
    reference = builds[0] / "reference"
    clock = _GradleClock(WrapperGradle.run)
    from_empty: list[Run] = []
    over_kept: list[Run] = []
    before: dict[str, int] = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CSTUDY_CONTENT", str(content))
        patch.setenv("CSTUDY_WORKSPACE", str(root))
        patch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
        patch.setattr(WrapperGradle, "run", lambda gradle, arguments: clock.run(gradle, arguments))
        for _ in range(RUNS):
            for build in builds:
                shutil.rmtree(build, ignore_errors=True)
            from_empty.append(_timed_verify(clock))
            before = _class_times(reference)
            over_kept.append(_timed_verify(clock))
    return Timings(tuple(from_empty), tuple(over_kept), before, _class_times(reference))


def test_a_verify_over_kept_builds_compiles_nothing_again(timings):
    assert (len(timings.classes_before) > 0, timings.classes_after) == (
        True,
        timings.classes_before,
    )


def test_a_verify_over_kept_builds_spends_measurably_less_time_in_gradle(timings):
    print(timings.summary())
    over_kept = min(run.gradle_seconds for run in timings.over_kept)
    from_empty = min(run.gradle_seconds for run in timings.from_empty)
    assert over_kept < from_empty * INCREMENTAL_SHARE, timings.summary()


def _timed_verify(clock: _GradleClock) -> Run:
    """Runs `cstudy verify` on the project, which must pass."""
    clock.seconds = 0.0
    started = time.perf_counter()
    result = runner.invoke(cli.app, ["verify", SLUG])
    seconds = time.perf_counter() - started
    assert result.exit_code == ExitCode.SUCCESS, result.output
    return Run(seconds, clock.seconds)


def _class_times(build: Path) -> dict[str, int]:
    classes = build / "build" / "classes"
    return {
        path.relative_to(classes).as_posix(): path.stat().st_mtime_ns
        for path in classes.rglob("*.class")
    }


def _listed(runs: tuple[Run, ...]) -> str:
    return ", ".join(f"{run.seconds:.1f} s (gradle {run.gradle_seconds:.1f} s)" for run in runs)
