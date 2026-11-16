"""Run folders under `.cs/runs/` as other `cstudy` processes leave them, and processes to name them
for (docs/specs/runners.md#invocation)."""

import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DAY_SECONDS = 24 * 60 * 60
SLEEP_FOR_A_MINUTE = "import time; time.sleep(60)"
RANDOM_PART = "abcd1234"


def run_folder(runs: Path, pid: int | None, *, number: int = 0, age_seconds: float = 0) -> Path:
    """An empty run folder of `pid` (of the form before pids were named, when None) that last
    changed `age_seconds` ago. Its stamp is long past, so it sorts before any folder a runner makes
    now, and `number` orders folders among themselves."""
    stamp = f"20200101-000000-{number:06d}"
    owner = "" if pid is None else f"p{pid}-"
    folder = runs / f"{stamp}-{owner}{RANDOM_PART}"
    folder.mkdir(parents=True)
    changed = time.time() - age_seconds
    os.utime(folder, (changed, changed))
    return folder


@contextmanager
def running_process() -> Iterator[int]:
    """The pid of a process that runs until the block ends."""
    process = subprocess.Popen((sys.executable, "-c", SLEEP_FOR_A_MINUTE))
    try:
        yield process.pid
    finally:
        process.kill()
        process.wait()


def ended_pid() -> int:
    """The pid of a process that ran and was waited for."""
    process = subprocess.Popen((sys.executable, "-c", "pass"))
    process.wait()
    return process.pid
