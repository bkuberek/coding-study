"""progress.db's numbered migrations and the schema version they record
(docs/specs/progress-and-scheduling.md#schema).

`migrations/0001_init.sql`, ... run in order; `meta.schema_version` records the last one applied.
"""

import sqlite3
from importlib import resources
from pathlib import Path

from coding_study.adapters.sqlite.migration_lock import migration_lock

SCHEMA_VERSION_KEY = "schema_version"
MIGRATIONS_PACKAGE = "coding_study.adapters.sqlite"
MIGRATIONS_DIRECTORY = "migrations"
MIGRATION_SUFFIX = ".sql"


def migrate_locked(database: Path, connection: sqlite3.Connection) -> None:
    """Migrate under a lock that every process of this database takes: the scripts commit on
    their own, so a transaction cannot make the check and the change one step."""
    with migration_lock(database):
        migrate(connection)


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    applied = schema_version(connection)
    for number, script in _migrations():
        if number <= applied:
            continue
        connection.executescript(script)
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (SCHEMA_VERSION_KEY, str(number)),
            )


def schema_version(connection: sqlite3.Connection) -> int:
    """The last migration applied; 0 for a database that has none."""
    has_meta = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if has_meta is None:
        return 0
    row = connection.execute(
        "SELECT value FROM meta WHERE key = ?", (SCHEMA_VERSION_KEY,)
    ).fetchone()
    return int(row[0]) if row is not None else 0


def latest_schema_version() -> int:
    """The schema this `cstudy` migrates a database to."""
    return _migrations()[-1][0]


def _migrations() -> list[tuple[int, str]]:
    directory = resources.files(MIGRATIONS_PACKAGE) / MIGRATIONS_DIRECTORY
    scripts = sorted(
        (entry for entry in directory.iterdir() if entry.name.endswith(MIGRATION_SUFFIX)),
        key=lambda entry: entry.name,
    )
    return [(_migration_number(entry.name), entry.read_text(encoding="utf-8")) for entry in scripts]


def _migration_number(file_name: str) -> int:
    return int(file_name.partition("_")[0])
