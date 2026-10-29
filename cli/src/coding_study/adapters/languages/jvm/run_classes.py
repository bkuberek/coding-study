"""A run's private copy of the classes Gradle built (docs/specs/runners.md#jvm-build-details).

`-Pcs.only` narrows each build to one problem, so every build rewrites the shared output
directories and deletes the classes of the problem built before. A JVM that loads classes lazily
from those directories would lose them to the next `cstudy` process. Instead the build, taken under
a lock, is copied into a directory of the run's own, and the JVM's classpath points at the copy.
"""

import os
import shutil
import tempfile
from pathlib import Path

from coding_study.adapters.process_liveness import is_alive
from coding_study.domain.layout import BUILD_DIRECTORY

RUNS_DIRECTORY = f"{BUILD_DIRECTORY}/jvm-runs"
"""Relative to the workspace; one `<pid>-<random>` directory per run holds that run's copies."""
_PID_SEPARATOR = "-"


class RunClasses:
    """The copies made for one `prepare`; the directory exists once the first copy is made."""

    def __init__(self, runs: Path) -> None:
        self._runs = runs
        self._directory: Path | None = None
        self._copies = 0

    @property
    def directory(self) -> Path | None:
        return self._directory

    def isolate(self, classpath: str, build: Path) -> str:
        """`classpath` with every existing directory below `build` replaced by a private copy.

        Call it while the build lock is held, so the directories are the build just made. Jars and
        everything outside `build` keep their paths: nothing rewrites those between runs.
        """
        resolved_build = build.resolve()
        entries = (
            self._isolated(Path(entry), resolved_build) for entry in classpath.split(os.pathsep)
        )
        return os.pathsep.join(str(entry) for entry in entries)

    def discard(self) -> None:
        if self._directory is not None:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = None

    def _isolated(self, entry: Path, build: Path) -> Path:
        if not (entry.is_dir() and entry.resolve().is_relative_to(build)):
            return entry
        copy = self._run_directory() / f"{self._copies}-{entry.parent.name}-{entry.name}"
        self._copies += 1
        shutil.copytree(entry, copy)
        return copy

    def _run_directory(self) -> Path:
        if self._directory is None:
            self._runs.mkdir(parents=True, exist_ok=True)
            remove_abandoned_runs(self._runs)
            self._directory = Path(
                tempfile.mkdtemp(prefix=f"{os.getpid()}{_PID_SEPARATOR}", dir=self._runs)
            )
        return self._directory


def remove_abandoned_runs(runs: Path) -> None:
    """Delete the run directories of processes that ended without cleaning up (killed, say)."""
    for directory in runs.iterdir():
        owner, separator, _ = directory.name.partition(_PID_SEPARATOR)
        if separator and owner.isdigit() and not is_alive(int(owner)):
            shutil.rmtree(directory, ignore_errors=True)
