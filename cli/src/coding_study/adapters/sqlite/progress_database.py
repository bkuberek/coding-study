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

UNREADABLE = "the progress database cannot be read"


class SqliteProgressDatabase:
    def __init__(self, path: Path) -> None:
        self._path = path

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

    def migrate(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(self._path)
            try:
                migrate_locked(self._path, connection)
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise UsageError(f"{UNREADABLE}: {error}") from None
