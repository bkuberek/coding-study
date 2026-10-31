"""One process at a time migrates a progress database."""

import fcntl
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def migration_lock(database: Path) -> Generator[None]:
    """Hold an exclusive `flock` on the folder of `database` for the `with` block.

    The lock is on the folder because SQLite takes its own locks on the database file (and `flock`
    on that file would deadlock against them), and a lock file beside it would be one more
    untracked file in the workspace. The kernel drops the lock when its holder ends, so a crash
    never leaves it held.
    """
    descriptor = os.open(database.parent, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)
