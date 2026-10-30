"""The runner and support jars on every JVM classpath (docs/specs/runners.md#jvm-build-details).

Both Gradle projects of a workspace, the practice project and the references, include the
runtime's `runners/jvm` build, so any JVM build rebuilds `runner.jar` and `support.jar` once their
sources change, and Gradle writes a jar in place. Two builds that do so at once write the same
files, and a JVM that reads a jar while it is rewritten fails before `hello`, for example with
`NoClassDefFoundError`. Every build therefore holds the runtime lock: shared while the sources and
jars are as the last build under the exclusive lock left them, since Gradle then leaves the jars
alone, and exclusive otherwise. Java and Kotlin, references and practice, still build side by side
once the jars are current; the first builds after a change take turns.
"""

import hashlib
import os
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from pathlib import Path

from coding_study.adapters.file_lock import exclusive_lock, shared_lock

LOCK_FILE = "runtime.lock"
RECORD_FILE = "runtime-jars.txt"
"""What the sources and jars looked like after the last build under the exclusive lock."""
BUILD_OUTPUT = "build"
JARS_DIRECTORY = "libs"
JAR_SUFFIX = ".jar"
SKIPPED_DIRECTORIES = frozenset({".gradle", ".kotlin"})


class RuntimeJars:
    def __init__(self, directory: Path, locks: Path) -> None:
        """`directory` is the runtime's `runners/jvm`; `locks` holds the lock and the record."""
        self._directory = directory
        self._lock = locks / LOCK_FILE
        self._record = locks / RECORD_FILE

    @property
    def directory(self) -> Path:
        return self._directory

    @contextmanager
    def held(self, on_wait: Callable[[], None]) -> Generator[None]:
        """The runtime lock for one build: shared when the jars are current, else exclusive,
        recording the state the build left once it returns."""
        with shared_lock(self._lock, on_wait):
            if self._state() == self._recorded():
                yield
                return
        with exclusive_lock(self._lock, on_wait):
            yield
            self._record.write_text(self._state(), encoding="utf-8")

    def _recorded(self) -> str | None:
        try:
            return self._record.read_text(encoding="utf-8")
        except OSError:
            return None

    def _state(self) -> str:
        """Path, size and modification time of every source and jar: the runtime refresh
        rewrites a changed source, and Gradle a rebuilt jar."""
        digest = hashlib.sha256()
        for path in _inputs_and_jars(self._directory):
            status = path.stat()
            relative = path.relative_to(self._directory).as_posix()
            digest.update(f"{relative}\0{status.st_size}\0{status.st_mtime_ns}\n".encode())
        return digest.hexdigest()


def _inputs_and_jars(directory: Path) -> Iterator[Path]:
    """Every file below `directory` but build output, plus the jars in each `build/libs/`."""
    for current, subdirectories, names in os.walk(directory):
        here = Path(current)
        if here.name == BUILD_OUTPUT:
            subdirectories[:] = [name for name in subdirectories if name == JARS_DIRECTORY]
            continue
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in SKIPPED_DIRECTORIES
        )
        is_jars = here.name == JARS_DIRECTORY and here.parent.name == BUILD_OUTPUT
        for name in sorted(names):
            if not is_jars or name.endswith(JAR_SUFFIX):
                yield here / name
