"""Reading and migrating progress.db's schema for `cstudy doctor`
(docs/specs/progress-and-scheduling.md#schema)."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from coding_study.adapters.sqlite import schema
from coding_study.adapters.sqlite.progress_database import SqliteProgressDatabase
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.helpers import progress_database_at

LAST_BEFORE_PROJECTS = 4


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "progress.db"


@pytest.fixture
def database(path: Path) -> SqliteProgressDatabase:
    return SqliteProgressDatabase(path)


def stored_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row[0])


def test_a_database_that_does_not_exist_has_no_schema(database):
    assert database.schema().found is None


def test_reading_the_schema_does_not_create_the_database(database, path):
    database.schema()
    assert not path.exists()


def test_a_migrated_database_is_at_the_latest_schema(database, path):
    SqliteProgressStore(path).active_attempt()
    assert database.schema().found == latest_schema_version()


def test_the_schema_names_the_version_this_cstudy_migrates_to(database):
    assert database.schema().latest == latest_schema_version()


def test_an_older_database_reports_its_schema_without_migrating(database, path):
    progress_database_at(path, LAST_BEFORE_PROJECTS)
    assert (database.schema().found, stored_version(path)) == (
        LAST_BEFORE_PROJECTS,
        LAST_BEFORE_PROJECTS,
    )


def test_a_write_ahead_log_database_without_its_log_files_is_read(database, path):
    """Python leaves the `-wal` and `-shm` files of a database it closes; another process may
    have removed them, and a read-only connection cannot open the database then."""
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO meta VALUES ('schema_version', '4')")
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()
    for log in (path.with_name("progress.db-wal"), path.with_name("progress.db-shm")):
        log.unlink(missing_ok=True)
    assert database.schema().found == 4


def test_a_newer_database_reports_its_schema(database, path):
    SqliteProgressStore(path).active_attempt()
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    assert database.schema().found == 99


def test_a_file_that_is_not_a_database_is_a_usage_error(database, path):
    path.write_text("not a database, not even close\n" * 40)
    with pytest.raises(UsageError, match="progress database"):
        database.schema()


def test_migrating_brings_an_older_database_to_the_latest_schema(database, path):
    progress_database_at(path, LAST_BEFORE_PROJECTS)
    database.migrate()
    assert stored_version(path) == latest_schema_version()


def test_migrating_keeps_the_attempts(database, path):
    progress_database_at(path, LAST_BEFORE_PROJECTS)
    database.migrate()
    attempt = SqliteProgressStore(path).latest_attempt("two-sum", Language.PYTHON)
    assert (attempt.id if attempt else None) == 7


def test_migrating_a_current_database_keeps_its_attempts(database, path):
    store = SqliteProgressStore(path)
    store.add_attempt(
        NewAttempt(
            slug="two-sum",
            language=Language.PYTHON,
            mode=AttemptMode.NEW,
            started_at=datetime(2026, 10, 24, 10, 0, tzinfo=UTC),
            time_limit_s=1500,
            stub_path="python/practice/two_sum.py",
        )
    )
    database.migrate()
    assert store.latest_attempt("two-sum", Language.PYTHON) is not None


def test_migrating_holds_the_migration_lock(database, path, monkeypatch):
    held: list[Path] = []

    class RecordingLock:
        def __init__(self, locked: Path) -> None:
            held.append(locked)

        def __enter__(self) -> None:
            return None

        def __exit__(self, *_exc: object) -> None:
            return None

    progress_database_at(path, LAST_BEFORE_PROJECTS)
    monkeypatch.setattr(schema, "migration_lock", RecordingLock)
    database.migrate()
    assert held == [path]


def test_a_database_that_cannot_be_migrated_is_a_usage_error(database, path):
    path.write_text("not a database, not even close\n" * 40)
    with pytest.raises(UsageError, match="progress database"):
        database.migrate()
