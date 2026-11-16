"""One short-lived connection per call to progress.db, migrating the database on the first
(docs/specs/progress-and-scheduling.md#schema)."""

import sqlite3
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from coding_study.adapters.sqlite.schema import migrate_locked


class ProgressConnection:
    """Opens `path`. The first call migrates the database: an older one is copied into
    `.cs/backups` of `workspace` first (default: the folder of the database), and the copy is
    named on standard error; a newer one is refused with UsageError."""

    def __init__(self, path: Path, workspace: Path | None = None) -> None:
        self._path = path
        self._workspace = workspace if workspace is not None else path.parent
        self._migrated = False

    @contextmanager
    def __call__(self) -> Generator[sqlite3.Connection]:
        """The connection, with rows by name and foreign keys on; its changes are committed when
        the block ends and rolled back when it raises."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            if not self._migrated:
                self._migrate_once(connection)
            with connection:
                yield connection
        finally:
            connection.close()

    def _migrate_once(self, connection: sqlite3.Connection) -> None:
        migration = migrate_locked(self._path, connection, self._workspace)
        self._migrated = True
        if migration is not None and migration.backup is not None:
            print(migration.notice, file=sys.stderr)
