"""Upgrading progress.db from every schema it has had, and refusing a newer one
(docs/specs/compatibility.md#migrations and #upgrade-tests).

`tests/fixtures/progress/schema-<N>.sql` builds a database at schema N with rows in every table.
"""

import io
import json
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager, redirect_stderr
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytest

from coding_study.adapters.sqlite import schema
from coding_study.adapters.sqlite.progress_database import SqliteProgressDatabase
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.application.progress_backup import export_progress, import_progress
from coding_study.domain.attempts import AttemptMode, AttemptStatus
from coding_study.domain.errors import BackupError, UsageError
from coding_study.domain.progress_export import ProgressSnapshot, export_text
from coding_study.domain.progress_migration import ProgressMigration
from tests.fakes import NOW, FakeClock, make_environment
from tests.helpers import progress_database_at
from tests.progress_fixtures import (
    FIXTURES,
    Rows,
    backups_in,
    database_at_schema,
    read_rows,
    stored_schema,
)

LATEST = latest_schema_version()
SCHEMAS = range(1, LATEST + 1)
OLDER = range(1, LATEST)
FIRST_WITH_LEVELS = 6
STORE = "store"
DATABASE = "database"


def structure(path: Path) -> dict[str, object]:
    """The tables with their columns, and the indexes, of the database."""
    with closing(sqlite3.connect(path)) as connection:
        tables = [
            name
            for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        ]
        indexes = sorted(
            name
            for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        )
        columns = {
            table: connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            for table in sorted(tables)
        }
    return {"columns": columns, "indexes": indexes}


def survives(before: Rows, after: Rows) -> bool:
    """Whether every row of `before` is in `after` with the values it had, and whatever `after`
    has beyond them, as a column a migration added, is NULL."""
    return all(
        len(after[table]) == len(rows)
        and all(
            {column: new[column] for column in old} == old
            and all(value is None for column, value in new.items() if column not in old)
            for old, new in zip(rows, after[table], strict=True)
        )
        for table, rows in before.items()
    )


def migrated_by_store(path: Path) -> None:
    SqliteProgressStore(path).active_attempt()


def migrated_by_database(path: Path) -> None:
    SqliteProgressDatabase(path).migrate()


ROUTES: dict[str, Callable[[Path], None]] = {
    STORE: migrated_by_store,
    DATABASE: migrated_by_database,
}


@pytest.fixture(params=ROUTES)
def route(request: pytest.FixtureRequest) -> Callable[[Path], None]:
    return ROUTES[request.param]


# The fixtures


def test_every_schema_up_to_the_latest_has_a_fixture():
    assert sorted(file.name for file in FIXTURES.glob("schema-*.sql")) == sorted(
        f"schema-{number}.sql" for number in SCHEMAS
    )


@pytest.mark.parametrize("number", SCHEMAS)
def test_a_fixture_records_its_schema(tmp_path, number):
    assert stored_schema(database_at_schema(tmp_path / "progress.db", number)) == number


@pytest.mark.parametrize("number", SCHEMAS)
def test_a_fixture_is_what_its_migrations_make(tmp_path, number):
    progress_database_at(tmp_path / "migrated.db", number)
    assert structure(database_at_schema(tmp_path / "progress.db", number)) == structure(
        tmp_path / "migrated.db"
    )


@pytest.mark.parametrize("number", SCHEMAS)
def test_a_fixture_has_rows_in_every_table(tmp_path, number):
    rows = read_rows(database_at_schema(tmp_path / "progress.db", number))
    assert [table for table, held in rows.items() if not held] == []


@pytest.mark.parametrize("number", SCHEMAS)
def test_a_fixture_covers_every_attempt_mode_and_status(tmp_path, number):
    attempts = read_rows(database_at_schema(tmp_path / "progress.db", number))["attempts"]
    assert ({row["mode"] for row in attempts}, {row["status"] for row in attempts}) == (
        set(AttemptMode),
        set(AttemptStatus),
    )


@pytest.mark.parametrize("number", range(FIRST_WITH_LEVELS, LATEST + 1))
def test_a_fixture_holds_the_levels_of_a_schedule_entry(tmp_path, number):
    entries = read_rows(database_at_schema(tmp_path / "progress.db", number))["schedule"]
    levels = [json.loads(str(row["levels"])) for row in entries if row["levels"] is not None]
    assert {key for held in levels for level in held for key in level} == {
        "level",
        "ease",
        "interval_days",
        "reps",
        "lapses",
        "last_grade",
    }


# Upgrading


@dataclass(frozen=True)
class Upgrade:
    path: Path
    number: int
    before: Rows
    notice: list[str]
    """The lines that say what the migration did: the store's on standard error, or the one the
    database returns."""

    @property
    def backups(self) -> list[Path]:
        return backups_in(self.path.parent)


@pytest.fixture(
    scope="module",
    params=[(name, number) for name in ROUTES for number in OLDER],
    ids=lambda param: f"{param[0]}-schema-{param[1]}",
)
def upgrade(request, tmp_path_factory) -> Upgrade:
    """A database at schema N, migrated by the store's first use or by the database's `migrate`,
    which `cstudy doctor --fix` calls."""
    name, number = request.param
    path = database_at_schema(tmp_path_factory.mktemp(f"{name}-{number}") / "progress.db", number)
    before = read_rows(path)
    if name == STORE:
        printed = io.StringIO()
        with redirect_stderr(printed):
            migrated_by_store(path)
        notice = printed.getvalue().splitlines()
    else:
        migration = SqliteProgressDatabase(path).migrate()
        notice = [migration.notice] if migration else []
    return Upgrade(path, number, before, notice)


def test_the_database_is_at_the_latest_schema(upgrade):
    assert stored_schema(upgrade.path) == LATEST


def test_one_backup_is_made_named_by_its_schema(upgrade):
    pattern = rf"progress-schema-{upgrade.number}-\d{{8}}T\d{{6}}Z\.db"
    assert [bool(re.fullmatch(pattern, backup.name)) for backup in upgrade.backups] == [True]


def test_the_backup_reads_the_old_schema_and_holds_its_rows(upgrade):
    (backup,) = upgrade.backups
    assert (stored_schema(backup), read_rows(backup)) == (upgrade.number, upgrade.before)


def test_every_row_survives_and_new_columns_are_null(upgrade):
    assert survives(upgrade.before, read_rows(upgrade.path))


def test_one_line_says_where_the_copy_went_and_what_was_migrated(upgrade):
    (backup,) = upgrade.backups
    assert upgrade.notice == [
        f"progress.db: backed up to .cs/backups/{backup.name}; "
        f"migrated from schema {upgrade.number} to {LATEST}"
    ]


def test_the_database_returns_the_migration_it_made(tmp_path):
    path = database_at_schema(tmp_path / "progress.db", 3)
    migration = SqliteProgressDatabase(path).migrate()
    (backup,) = backups_in(tmp_path)
    assert migration == ProgressMigration(3, LATEST, f".cs/backups/{backup.name}")


def test_a_backup_is_one_file_that_leaves_no_log_beside_it(tmp_path):
    migrated_by_store(database_at_schema(tmp_path / "progress.db", 4))
    assert [backup.suffix for backup in backups_in(tmp_path)] == [".db"]


def test_a_backup_clash_adds_a_number(tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "_utc_stamp", lambda: "20261114T101500Z")
    for _ in range(3):
        migrated_by_store(database_at_schema(tmp_path / "progress.db", 3))
        for log in tmp_path.glob("progress.db*"):
            log.unlink()
    assert [backup.name for backup in backups_in(tmp_path)] == [
        "progress-schema-3-20261114T101500Z-2.db",
        "progress-schema-3-20261114T101500Z-3.db",
        "progress-schema-3-20261114T101500Z.db",
    ]


def test_the_backup_is_made_under_the_lock_before_the_first_script(tmp_path, monkeypatch):
    events: list[str] = []
    copy, apply = schema._copy_to, schema._apply

    @contextmanager
    def lock(_database: Path) -> Iterator[None]:
        events.append("lock")
        yield
        events.append("unlock")

    def copy_recorded(connection: sqlite3.Connection, file: Path) -> None:
        events.append("copy")
        copy(connection, file)

    def apply_recorded(connection: sqlite3.Connection, script: str) -> None:
        events.append("script")
        apply(connection, script)

    monkeypatch.setattr(schema, "migration_lock", lock)
    monkeypatch.setattr(schema, "_copy_to", copy_recorded)
    monkeypatch.setattr(schema, "_apply", apply_recorded)
    migrated_by_store(database_at_schema(tmp_path / "progress.db", LATEST - 2))
    assert events == ["lock", "copy", "script", "script", "unlock"]


def test_a_new_database_is_made_without_a_backup(tmp_path, capsys):
    path = tmp_path / "new" / "progress.db"
    migrated_by_store(path)
    assert (stored_schema(path), backups_in(path.parent), capsys.readouterr().err) == (
        LATEST,
        [],
        "",
    )


def test_a_database_at_the_latest_schema_is_not_copied(tmp_path, capsys):
    migrated_by_store(database_at_schema(tmp_path / "progress.db", LATEST))
    assert (backups_in(tmp_path), capsys.readouterr().err) == ([], "")


def test_later_calls_of_the_store_make_no_second_copy(tmp_path):
    store = SqliteProgressStore(database_at_schema(tmp_path / "progress.db", 3))
    store.active_attempt()
    store.active_attempt()
    assert len(backups_in(tmp_path)) == 1


def test_the_backups_of_a_workspace_go_to_its_cs_folder_whatever_the_database_path(tmp_path):
    path = database_at_schema(tmp_path / "data" / "progress.db", 3)
    SqliteProgressStore(path, workspace=tmp_path).active_attempt()
    assert (len(backups_in(tmp_path)), backups_in(path.parent)) == (1, [])


# A newer database


def make_newer(path: Path) -> bytes:
    database_at_schema(path, LATEST)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (LATEST + 1,))
    return path.read_bytes()


def test_a_newer_database_is_refused_and_left_as_it_was(tmp_path, route):
    path = tmp_path / "progress.db"
    before = make_newer(path)
    with pytest.raises(
        UsageError,
        match=re.escape(
            f"progress.db uses schema {LATEST + 1}, newer than the {LATEST} this cstudy reads: "
            "upgrade cstudy"
        ),
    ):
        route(path)
    assert (path.read_bytes(), backups_in(tmp_path)) == (before, [])


@pytest.mark.parametrize(
    "call",
    [
        lambda store: store.active_attempt(),
        lambda store: store.attempts("two-sum"),
        lambda store: store.snapshot(),
    ],
    ids=["active_attempt", "attempts", "snapshot"],
)
def test_a_newer_database_is_refused_by_every_call_of_the_store(tmp_path, call):
    path = tmp_path / "progress.db"
    make_newer(path)
    store = SqliteProgressStore(path)
    with pytest.raises(UsageError, match="newer than the"):
        call(store)
    with pytest.raises(UsageError, match="newer than the"):
        call(store)


# A backup that fails


def test_a_backup_that_cannot_be_made_changes_nothing(tmp_path, route):
    path = database_at_schema(tmp_path / "progress.db", 4)
    (tmp_path / ".cs").mkdir()
    (tmp_path / ".cs" / "backups").write_text("a file where the folder goes")
    before = path.read_bytes()
    with pytest.raises(BackupError, match=r"^cannot back up progress\.db .*; nothing changed$"):
        route(path)
    assert (path.read_bytes(), stored_schema(path)) == (before, 4)


def test_a_failed_backup_names_the_reason(tmp_path, monkeypatch):
    path = database_at_schema(tmp_path / "progress.db", 4)

    def full(_connection: sqlite3.Connection, file: Path) -> None:
        file.write_bytes(b"half a database")
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(schema, "_copy_to", full)
    with pytest.raises(BackupError) as caught:
        migrated_by_store(path)
    assert (str(caught.value), backups_in(tmp_path)) == (
        "cannot back up progress.db before migrating it: database or disk is full; nothing changed",
        [],
    )


def test_a_copy_that_does_not_read_the_old_schema_is_removed_and_nothing_changes(
    tmp_path, monkeypatch, route
):
    path = database_at_schema(tmp_path / "progress.db", 4)
    monkeypatch.setattr(schema, "_copy_schema", lambda _file: 3)
    before = path.read_bytes()
    with pytest.raises(BackupError, match="the copy reads schema 3, not 4; nothing changed"):
        route(path)
    assert (path.read_bytes(), backups_in(tmp_path)) == (before, [])


def test_a_database_that_failed_its_backup_migrates_once_it_can(tmp_path):
    path = database_at_schema(tmp_path / "progress.db", 4)
    (tmp_path / ".cs").mkdir()
    blocker = tmp_path / ".cs" / "backups"
    blocker.write_text("a file where the folder goes")
    with pytest.raises(BackupError):
        migrated_by_store(path)
    blocker.unlink()
    migrated_by_store(path)
    assert (stored_schema(path), len(backups_in(tmp_path))) == (LATEST, 1)


# Export round trips


def exported_without_its_time(text: str) -> dict[str, object]:
    document = json.loads(text)
    del document["exported_at"]
    return document


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_of_a_migrated_database_imports_and_exports_the_same_document(
    content_root, number
):
    migrated = database_at_schema(content_root / "migrated" / "progress.db", number)
    source = make_environment(content_root, progress=SqliteProgressStore(migrated))
    target = make_environment(
        content_root,
        progress=SqliteProgressStore(content_root / "empty" / "progress.db"),
        clock=FakeClock(NOW + timedelta(hours=1)),
    )
    exported = export_progress(source).text
    import_progress(target, exported)
    assert exported_without_its_time(export_progress(target).text) == exported_without_its_time(
        exported
    )


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_built_at_each_schema_imports_into_the_latest(content_root, number):
    rows = read_rows(database_at_schema(content_root / "fixture" / "progress.db", number))
    export = export_text(
        ProgressSnapshot(number, {table: tuple(held) for table, held in rows.items()}), NOW
    )
    latest = content_root / "latest" / "progress.db"
    import_progress(make_environment(content_root, progress=SqliteProgressStore(latest)), export)
    assert survives(rows, read_rows(latest))
