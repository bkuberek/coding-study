"""A run's private copy of what Gradle built (docs/specs/runners.md#jvm-build-details).

`-Pcs.only` narrows each build to one problem, so every build rewrites the shared output
directories and deletes the classes of the problem built before, and a build after a change to the
runner's sources rewrites the runner and support jars in place. A JVM that loads classes lazily
from those files would lose them to the next `cstudy` process. Instead the build, taken under a
lock, is copied into a directory of the run's own, and the JVM's classpath points at the copy.
"""

import os
import shutil
import tempfile
from collections.abc import Sequence
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

    def isolate(self, classpath: str, outputs: Sequence[Path]) -> str:
        """`classpath` with every existing entry below one of `outputs`, a class directory or a
        jar, replaced by a private copy.

        Call it while the build locks are held, so the entries are what the build just made.
        Everything else, such as the jars in Gradle's cache, keeps its path: nothing rewrites
        those between runs.
        """
        resolved = tuple(output.resolve() for output in outputs)
        entries = (self._isolated(Path(entry), resolved) for entry in classpath.split(os.pathsep))
        return os.pathsep.join(str(entry) for entry in entries)

    def discard(self) -> None:
        if self._directory is not None:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = None

    def _isolated(self, entry: Path, outputs: Sequence[Path]) -> Path:
        if not entry.exists():
            return entry
        resolved = entry.resolve()
        if not any(resolved.is_relative_to(output) for output in outputs):
            return entry
        copy = self._run_directory() / f"{self._copies}-{entry.parent.name}-{entry.name}"
        self._copies += 1
        if entry.is_dir():
            shutil.copytree(entry, copy)
        else:
            shutil.copyfile(entry, copy)
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
