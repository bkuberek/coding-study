"""The progress backup that `cstudy export` writes and `cstudy import` reads
(docs/specs/cli.md#cstudy-export).

Rows are kept exactly as SQLite stores them (JSON columns stay strings), so an import restores
the same database and the same `cstudy stats`.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from coding_study.domain.cases import JsonValue

EXPORT_FORMAT = "coding-study-progress"
EXPORT_VERSION = 1
NOT_AN_EXPORT = "not a coding-study progress export"
TABLES_KEY = "tables"
_BAD_SCHEMA_VERSION = "schema_version must be a positive integer"

type ColumnValue = str | int | float | None
type Row = Mapping[str, ColumnValue]


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    """Every row of every progress.db table but `meta`, by table, in insertion order."""

    schema_version: int
    """The last migration applied to the database the rows came from."""
    tables: Mapping[str, tuple[Row, ...]]

    def row_counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}


def export_document(snapshot: ProgressSnapshot, exported_at: datetime) -> dict[str, JsonValue]:
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "schema_version": snapshot.schema_version,
        "exported_at": exported_at.isoformat(),
        TABLES_KEY: {name: [dict(row) for row in rows] for name, rows in snapshot.tables.items()},
    }


def export_text(snapshot: ProgressSnapshot, exported_at: datetime) -> str:
    """The document as JSON with one row per line, so a committed export diffs by row."""
    document = export_document(snapshot, exported_at)
    header = [
        f"  {json.dumps(key)}: {json.dumps(value)},"
        for key, value in document.items()
        if key != TABLES_KEY
    ]
    tables = ",\n".join(_table_text(name, rows) for name, rows in snapshot.tables.items())
    return "\n".join(["{", *header, f'  "{TABLES_KEY}": {{', tables, "  }", "}"]) + "\n"


def _table_text(name: str, rows: tuple[Row, ...]) -> str:
    if not rows:
        return f"    {json.dumps(name)}: []"
    lines = ",\n".join(f"      {json.dumps(dict(row))}" for row in rows)
    return f"    {json.dumps(name)}: [\n{lines}\n    ]"


def parse_export(document: object) -> ProgressSnapshot:
    """Raises ValueError naming the first problem in `document`."""
    if not isinstance(document, dict):
        raise ValueError(NOT_AN_EXPORT)
    fields = cast(dict[str, object], document)
    if fields.get("format") != EXPORT_FORMAT:
        raise ValueError(NOT_AN_EXPORT)
    version = fields.get("version")
    if version != EXPORT_VERSION:
        raise ValueError(f"export version {version} is not supported (expected {EXPORT_VERSION})")
    schema_version = fields.get("schema_version")
    if not isinstance(schema_version, int) or not _is_column_value(schema_version):
        raise ValueError(_BAD_SCHEMA_VERSION)
    if schema_version < 1:
        raise ValueError(_BAD_SCHEMA_VERSION)
    tables = fields.get(TABLES_KEY)
    if not isinstance(tables, dict):
        raise ValueError("tables must be an object of row lists")
    named = cast(dict[str, object], tables)
    return ProgressSnapshot(
        schema_version, {name: _rows(name, rows) for name, rows in named.items()}
    )


def _rows(table: str, rows: object) -> tuple[Row, ...]:
    if not isinstance(rows, list):
        raise ValueError(f"tables.{table} must be a list of rows")
    items = cast(list[object], rows)
    return tuple(_row(f"tables.{table}[{index}]", row) for index, row in enumerate(items))


def _row(where: str, row: object) -> Row:
    if not isinstance(row, dict):
        raise ValueError(f"{where} must be an object")
    columns = cast(dict[str, object], row)
    for column, value in columns.items():
        if not _is_column_value(value):
            raise ValueError(f"{where}.{column} must be a string, a number or null")
    return cast(Row, columns)


def _is_column_value(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return value is None or isinstance(value, str | int | float)
