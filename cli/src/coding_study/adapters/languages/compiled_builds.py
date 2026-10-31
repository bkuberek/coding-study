"""What the Go and Rust runners share about their generated builds in `.cs/build/<lang>`
(docs/specs/runners.md#go-build-details, #rust-build-details).

Two `cstudy` processes may build the same problem at once (a watcher and a verify), so the
runners hold `exclusive_lock` (adapters/file_lock.py) around the generation and the build, and
each run launches its own copy of the built binary, which no other build overwrites. Generated
files are written only when their content changes: Cargo fingerprints sources by modification
time, and editors and watchers notice writes.
"""

import os
import shutil
import tempfile
from pathlib import Path

from coding_study.adapters.process_liveness import is_alive

RUNS_DIRECTORY = "run"
"""Below a build directory; one `<pid>-<random>` directory per run holds that run's binary."""
EXECUTABLE_MODE = 0o755
_PID_SEPARATOR = "-"


def write_if_changed(path: Path, text: str) -> None:
    """Writes `text` unless the file already holds it, keeping its timestamp."""
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def private_copy(binary: Path, build_directory: Path) -> Path:
    """A copy of `binary` in a directory of this run's own, so a later build by another process
    can never replace the file this one is about to start.

    The copy's directory is the launch's `scratch`: `RunnerProcess` removes it when the run ends.
    Directories of processes that ended without cleaning up (killed, say) are removed here."""
    _, (copy,) = private_copies((binary,), build_directory)
    return copy


def private_copies(
    binaries: tuple[Path, ...], build_directory: Path
) -> tuple[Path, tuple[Path, ...]]:
    """`private_copy` for several binaries, in one directory of this run's own: the directory,
    and the copies in the order of `binaries`. Their names must differ."""
    runs = build_directory / RUNS_DIRECTORY
    runs.mkdir(parents=True, exist_ok=True)
    _remove_abandoned_runs(runs)
    directory = Path(tempfile.mkdtemp(prefix=f"{os.getpid()}{_PID_SEPARATOR}", dir=runs))
    copies = tuple(directory / binary.name for binary in binaries)
    try:
        for binary, copy in zip(binaries, copies, strict=True):
            shutil.copyfile(binary, copy)
            copy.chmod(EXECUTABLE_MODE)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return directory, copies


def _remove_abandoned_runs(runs: Path) -> None:
    for directory in runs.iterdir():
        owner, separator, _ = directory.name.partition(_PID_SEPARATOR)
        if separator and owner.isdigit() and not is_alive(int(owner)):
            shutil.rmtree(directory, ignore_errors=True)


def relative(path: Path, start: Path) -> str:
    """`path` relative to `start`, in POSIX form."""
    return Path(os.path.relpath(path, start)).as_posix()
