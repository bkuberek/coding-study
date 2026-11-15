"""`ProgressDatabase` on SQLite: what `cstudy doctor` reads and `--fix` migrates
(docs/specs/progress-and-scheduling.md#schema)."""

import sqlite3
from pathlib import Path

from coding_study.adapters.sqlite.schema import (
    latest_schema_version,
    migrate_locked,
    schema_version,
)
from coding_study.application.ports import ProgressSchema
from coding_study.domain.errors import UsageError
from coding_study.domain.progress_migration import ProgressMigration

UNREADABLE = "the progress database cannot be read"


class SqliteProgressDatabase:
    """`ProgressDatabase`; `migrate` copies an older database into `.cs/backups` of `workspace`
    first (default: the folder of the database)."""

    def __init__(self, path: Path, workspace: Path | None = None) -> None:
        self._path = path
        self._workspace = workspace if workspace is not None else path.parent

    def schema(self) -> ProgressSchema:
        """Opens the file for writing without creating it, since a write-ahead log database
        cannot be opened read-only once its log files are gone; the connection only reads."""
        latest = latest_schema_version()
        if not self._path.exists():
            return ProgressSchema(None, latest)
        try:
            connection = sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=rw", uri=True)
            try:
                return ProgressSchema(schema_version(connection), latest)
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise UsageError(f"{UNREADABLE}: {error}") from None

    def migrate(self) -> ProgressMigration | None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(self._path)
            try:
                return migrate_locked(self._path, connection, self._workspace)
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise UsageError(f"{UNREADABLE}: {error}") from None
