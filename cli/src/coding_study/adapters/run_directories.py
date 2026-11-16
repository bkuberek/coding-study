"""The folder of each run under `.cs/runs/` and which of them to remove
(docs/specs/runners.md#invocation).

Several `cstudy` processes work on one workspace at once (a `verify` and a `test`, `serve` and a
`test`), so a folder's name holds the pid of the process that made it:
`<yyyymmdd>-<hhmmss>-<microseconds>-p<pid>-<random>`. A process keeps its own newest `KEPT_RUNS`
folders, and removes another process's folder only once that process has ended or the folder is
more than a day old (a pid can be reused). A folder named without a pid, the form of earlier
releases, is removed once it is more than a day old. Any other name under `.cs/runs/` (a service
stack's folder, say) is never touched.
"""

import os
import re
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from functools import cache
from pathlib import Path
from shutil import rmtree

from coding_study.adapters.process_liveness import is_alive

KEPT_RUNS = 20
ABANDONED_AFTER_SECONDS = 24 * 60 * 60
"""A run folder this old is no run in progress, whatever its owner's pid is now."""

_STAMP = r"\d{8}-\d{6}-\d{6}"
_RANDOM = r"[a-z0-9_]{8}"
"""What `tempfile.mkdtemp` appends."""
_OWNED = re.compile(rf"{_STAMP}-p(?P<pid>[1-9][0-9]{{0,8}})-{_RANDOM}")
_UNOWNED = re.compile(rf"{_STAMP}-{_RANDOM}")


class RunDirectories:
    """The run folders under `directory`, shared with every other `cstudy` process of the
    workspace. `owner` gives the pid that a new folder is named for and that `sweep` keeps."""

    def __init__(self, directory: Path, owner: Callable[[], int] = os.getpid) -> None:
        self._directory = directory
        self._owner = owner

    def create(self) -> Path:
        """A new empty folder for one run, after removing the folders that are no longer needed."""
        self._directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        prefix = f"{stamp}-p{self._owner()}-"
        created = Path(tempfile.mkdtemp(prefix=prefix, dir=self._directory))
        self.sweep()
        return created

    def sweep(self) -> None:
        """Removes this process's folders beyond the newest `KEPT_RUNS`, the folders of processes
        that ended, and any folder more than a day old that this process does not own."""
        owner = self._owner()
        now = time.time()
        lives = cache(is_alive)
        own: list[Path] = []
        for path in sorted(self._directory.iterdir()):
            if path.is_symlink() or not path.is_dir():
                continue
            owned = _OWNED.fullmatch(path.name)
            if owned is None:
                if _UNOWNED.fullmatch(path.name) and _is_old(path, now):
                    rmtree(path, ignore_errors=True)
                continue
            pid = int(owned["pid"])
            if pid == owner:
                own.append(path)
                continue
            if _is_old(path, now) or not lives(pid):
                rmtree(path, ignore_errors=True)
        for old_run in own[:-KEPT_RUNS]:
            rmtree(old_run, ignore_errors=True)


def _is_old(path: Path, now: float) -> bool:
    try:
        return now - path.stat().st_mtime > ABANDONED_AFTER_SECONDS
    except OSError:
        return False
