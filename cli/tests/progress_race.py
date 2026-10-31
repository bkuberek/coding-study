"""Worker for the race over a brand-new progress.db
(docs/specs/progress-and-scheduling.md#migrations).

It runs in a process of its own, started with `spawn`, so it lives in a module that a new
interpreter can import by name.
"""

from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from pathlib import Path

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore


def open_at_once(path: Path, barrier: Barrier, errors: "Queue[str]") -> None:
    """Opens a new store on `path` once every worker is ready; puts the error it met, or ""."""
    store = SqliteProgressStore(path)
    barrier.wait()
    try:
        store.active_attempt()
    except Exception as error:
        errors.put(f"{type(error).__name__}: {error}")
    else:
        errors.put("")
