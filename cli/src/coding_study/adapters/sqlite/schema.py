"""progress.db's numbered migrations and the schema version they record
(docs/specs/progress-and-scheduling.md#schema).

`migrations/0001_init.sql`, ... run in order; `meta.schema_version` records the last one applied.
A database that has a schema is copied first, and restored from the copy when a script fails; one
newer than the last migration is refused (docs/specs/compatibility.md#migrations).
"""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import NoReturn

from coding_study.adapters.sqlite.migration_lock import migration_lock
from coding_study.domain.errors import BackupError, MigrationError, UsageError
from coding_study.domain.layout import BACKUPS_DIRECTORY
from coding_study.domain.progress_migration import ProgressMigration

_DUPLICATE_COLUMN = "duplicate column name"
SCHEMA_VERSION_KEY = "schema_version"
MIGRATIONS_PACKAGE = "coding_study.adapters.sqlite"
MIGRATIONS_DIRECTORY = "migrations"
MIGRATION_SUFFIX = ".sql"
BACKUP_STAMP = "%Y%m%dT%H%M%SZ"


def migrate_locked(
    database: Path, connection: sqlite3.Connection, workspace: Path
) -> ProgressMigration | None:
    """Migrate under a lock that every process of this database takes: the scripts commit on
    their own, so a transaction cannot make the check and the change one step. The copy of an
    older database is made under it too, so of processes that open one together, one copies and
    migrates, and the others find it migrated."""
    with migration_lock(database):
        return migrate(connection, database, workspace)


def migrate(
    connection: sqlite3.Connection, database: Path, workspace: Path
) -> ProgressMigration | None:
    """Brings the database to the latest schema; None when it was there already.

    A database that has a schema is copied into the workspace's `.cs/backups` before the first
    script runs. Raises UsageError for a newer database and BackupError when the copy fails; both
    leave it unchanged. A script that fails after the copy puts the copy back and raises
    MigrationError, or, for an interrupt, raises the interrupt.
    """
    migrations = _migrations()
    latest = migrations[-1][0]
    found = schema_version(connection)
    if found > latest:
        raise UsageError(
            f"progress.db uses schema {found}, newer than the {latest} this cstudy reads: "
            "upgrade cstudy"
        )
    copy = _back_up(connection, workspace, database.stem, found) if 0 < found < latest else None
    connection.execute("PRAGMA journal_mode = WAL")
    number = found
    try:
        for number, script in migrations:
            if number <= found:
                continue
            _apply(connection, script)
            with connection:
                connection.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (SCHEMA_VERSION_KEY, str(number)),
                )
    except BaseException as error:
        if copy is None:
            raise
        _restore_after(connection, copy, workspace, found, number, error)
    if found == latest:
        return None
    return ProgressMigration(
        found, latest, None if copy is None else copy.relative_to(workspace).as_posix()
    )


def _restore_after(
    connection: sqlite3.Connection,
    copy: Path,
    workspace: Path,
    found: int,
    failed_at: int,
    error: BaseException,
) -> NoReturn:
    """Puts `copy` back over the database after `error` ended the migration at schema `failed_at`.
    Raises MigrationError, or `error` itself when it is an interrupt and the copy went back."""
    backup = copy.relative_to(workspace).as_posix()
    reason = str(error) or type(error).__name__
    try:
        _restore(connection, copy, found)
    except (OSError, sqlite3.Error) as failure:
        raise MigrationError(found, failed_at, reason, backup, str(failure)) from error
    if not isinstance(error, Exception):
        raise error
    raise MigrationError(found, failed_at, reason, backup) from error


def _restore(connection: sqlite3.Connection, copy: Path, found: int) -> None:
    """Writes `copy` over the database with SQLite's online backup, and checks that it reads schema
    `found`."""
    if connection.in_transaction:
        connection.rollback()
    source = sqlite3.connect(f"{copy.resolve().as_uri()}?mode=ro", uri=True)
    try:
        source.backup(connection)
    finally:
        source.close()
    restored = schema_version(connection)
    if restored != found:
        raise sqlite3.DatabaseError(f"the restored database reads schema {restored}, not {found}")


def _back_up(connection: sqlite3.Connection, workspace: Path, stem: str, found: int) -> Path:
    """Copies the database into the workspace's `.cs/backups` with SQLite's online backup, as a
    file of its own, and checks that the copy reads schema `found`; a copy that fails either step
    is removed."""
    copy: Path | None = None
    try:
        backups = workspace / BACKUPS_DIRECTORY
        backups.mkdir(parents=True, exist_ok=True)
        copy = _unused_file(backups, f"{stem}-schema-{found}-{_utc_stamp()}")
        _copy_to(connection, copy)
        copied = _copy_schema(copy)
        if copied != found:
            raise BackupError(f"the copy reads schema {copied}, not {found}")
    except (OSError, sqlite3.Error) as error:
        _remove(copy)
        raise BackupError(str(error)) from None
    except BaseException:
        _remove(copy)
        raise
    return copy


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime(BACKUP_STAMP)


def _unused_file(directory: Path, name: str) -> Path:
    """Creates an empty `<name>.db`, or `<name>-2.db`, `<name>-3.db`, ... for the first that no
    file has."""
    number = 1
    while True:
        file = directory / (f"{name}.db" if number == 1 else f"{name}-{number}.db")
        try:
            file.touch(exist_ok=False)
        except FileExistsError:
            number += 1
        else:
            return file


def _copy_to(connection: sqlite3.Connection, file: Path) -> None:
    """The copy leaves write-ahead logging, so it is one file that opens read-only."""
    destination = sqlite3.connect(file)
    try:
        connection.backup(destination)
        destination.execute("PRAGMA journal_mode = DELETE")
    finally:
        destination.close()


def _copy_schema(file: Path) -> int:
    copy = sqlite3.connect(f"{file.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return schema_version(copy)
    finally:
        copy.close()


def _remove(file: Path | None) -> None:
    if file is not None:
        file.unlink(missing_ok=True)


def _apply(connection: sqlite3.Connection, script: str) -> None:
    """Runs a migration script. SQLite has no `ADD COLUMN IF NOT EXISTS`, so a script that adds a
    column the table already has, as one run again under a new number after a merge does, runs
    statement by statement instead, skipping each column that is there."""
    try:
        connection.executescript(script)
    except sqlite3.OperationalError as error:
        if not _is_duplicate_column(error):
            raise
        for statement in _statements(script):
            try:
                connection.executescript(statement)
            except sqlite3.OperationalError as skipped:
                if not _is_duplicate_column(skipped):
                    raise


def _is_duplicate_column(error: sqlite3.OperationalError) -> bool:
    return str(error).startswith(_DUPLICATE_COLUMN)


def _statements(script: str) -> Iterator[str]:
    """The script's statements, each complete as SQLite reads it."""
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""


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
