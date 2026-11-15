"""Progress databases at each schema they have had, built from
`tests/fixtures/progress/schema-<N>.sql` (docs/specs/compatibility.md#upgrade-tests)."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from coding_study.adapters.sqlite import schema
from coding_study.adapters.sqlite.schema import schema_version
from coding_study.domain.progress_export import ColumnValue

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "progress"
type Rows = dict[str, list[dict[str, ColumnValue]]]
FAILING_SCRIPT = """\
CREATE TABLE half_migrated (id INTEGER);
BEGIN;
INSERT INTO half_migrated VALUES (1);
SELECT * FROM missing_table;
"""
FAILING_REASON = "no such table: missing_table"


def database_at_schema(path: Path, number: int) -> Path:
    """Builds `path` as a database at schema `number`, with the rows of its fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript((FIXTURES / f"schema-{number}.sql").read_text(encoding="utf-8"))
    return path


def read_rows(path: Path) -> Rows:
    """Every row of every table but `meta`, by table, in insertion order."""
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'meta' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            table: [
                dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
            ]
            for table in tables
        }


def stored_schema(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        return schema_version(connection)


def backups_in(workspace: Path) -> list[Path]:
    """The files in the workspace's `.cs/backups`."""
    directory = workspace / ".cs" / "backups"
    return sorted(directory.iterdir()) if directory.exists() else []


def fail_migration_at(monkeypatch: pytest.MonkeyPatch, number: int) -> None:
    """Makes migration `number` a script that changes the database, then fails with
    `FAILING_REASON`, with a transaction still open."""
    real = schema._migrations()
    monkeypatch.setattr(
        schema,
        "_migrations",
        lambda: [(n, FAILING_SCRIPT if n == number else script) for n, script in real],
    )
