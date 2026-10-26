"""progress.db in SQLite (docs/specs/progress-and-scheduling.md#schema).

Numbered migrations in `migrations/` (`0001_init.sql`, ...) run in order on first use;
`meta.schema_version` records the last one applied. Timestamps are ISO 8601 UTC strings.
"""

import sqlite3
from collections import defaultdict
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from datetime import UTC, date, datetime
from importlib import resources
from pathlib import Path
from typing import Any

from coding_study.adapters.sqlite import bench_rows
from coding_study.domain.attempts import (
    Attempt,
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.bench_records import BenchOutcome, BenchRunRecord
from coding_study.domain.bench_verdict import PastRun, Verdict
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.progress_export import ColumnValue, ProgressSnapshot
from coding_study.domain.progress_stats import LatestBench
from coding_study.domain.scheduling import ProblemProgress, ReviewState, ScheduleEntry

SCHEMA_VERSION_KEY = "schema_version"
META_TABLE = "meta"
TABLE_ORDER = ("attempts", "test_runs", "schedule", "bench_runs")
"""Snapshot and restore order: attempts before the rows that reference them."""
MIGRATIONS_PACKAGE = "coding_study.adapters.sqlite"
MIGRATIONS_DIRECTORY = "migrations"
MIGRATION_SUFFIX = ".sql"

_LATEST_FIRST = "ORDER BY started_at DESC, id DESC LIMIT 1"
_ATTEMPT_UPDATE = """
UPDATE attempts SET status = :status, ended_at = :ended_at, first_pass_at = :first_pass_at,
  time_limit_s = :time_limit_s, rating = :rating, grade = :grade, hints_used = :hints_used,
  solution_revealed = :solution_revealed, level_unlocked = :level_unlocked,
  stub_path = :stub_path, archive_path = :archive_path, notes = :notes
WHERE id = :id
"""
_TEST_RUN_INSERT = """
INSERT INTO test_runs (attempt_id, ran_at, code_hash, total, passed, failed, errored, timed_out,
  tle, time_limit, duration_ms)
VALUES (:attempt_id, :ran_at, :code_hash, :total, :passed, :failed, :errored, :timed_out, :tle,
  :time_limit, :duration_ms)
"""
_LATEST_USER_BENCHES = """
SELECT slug, lang, verdict, ran_at FROM bench_runs AS run
WHERE attempt_id IS NOT NULL AND id = (
  SELECT id FROM bench_runs
  WHERE slug = run.slug AND lang = run.lang AND attempt_id IS NOT NULL
  ORDER BY ran_at DESC, id DESC LIMIT 1
)
ORDER BY slug, lang
"""
_SCHEDULE_UPSERT = """
INSERT OR REPLACE INTO schedule (slug, ease, interval_days, reps, lapses, due_on, last_grade,
  updated_at)
VALUES (:slug, :ease, :interval_days, :reps, :lapses, :due_on, :last_grade, :updated_at)
"""


class SqliteProgressStore:
    """`ProgressStore`; one short-lived connection per call."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._migrated = False

    def add_attempt(self, attempt: NewAttempt) -> Attempt:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO attempts (slug, lang, mode, status, started_at, time_limit_s, "
                "stub_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.slug,
                    attempt.language,
                    attempt.mode,
                    AttemptStatus.IN_PROGRESS,
                    _instant_text(attempt.started_at),
                    attempt.time_limit_s,
                    attempt.stub_path,
                ),
            )
            row = connection.execute("SELECT * FROM attempts WHERE id = ?", (cursor.lastrowid,))
            return _attempt(row.fetchone())

    def update_attempt(self, attempt: Attempt) -> None:
        with self._connection() as connection:
            connection.execute(_ATTEMPT_UPDATE, _attempt_fields(attempt))

    def active_attempt(self, slug: str | None = None) -> Attempt | None:
        if slug is None:
            return self._one_attempt("status = ?", (AttemptStatus.IN_PROGRESS,))
        return self._one_attempt("status = ? AND slug = ?", (AttemptStatus.IN_PROGRESS, slug))

    def in_progress_attempt(self, slug: str, language: Language | None) -> Attempt | None:
        return self._one_attempt(
            "status = ? AND slug = ? AND lang IS ?", (AttemptStatus.IN_PROGRESS, slug, language)
        )

    def latest_attempt(self, slug: str, language: Language | None) -> Attempt | None:
        return self._one_attempt("slug = ? AND lang IS ?", (slug, language))

    def add_test_run(self, run: RunRecord) -> None:
        tally = run.tally
        with self._connection() as connection:
            connection.execute(
                _TEST_RUN_INSERT,
                {
                    "attempt_id": run.attempt_id,
                    "ran_at": _instant_text(run.ran_at),
                    "code_hash": run.code_hash,
                    "total": tally.total,
                    "passed": tally.passed,
                    "failed": tally.failed,
                    "errored": tally.errored,
                    "timed_out": tally.timed_out,
                    "tle": tally.tle,
                    "time_limit": run.time_limit,
                    "duration_ms": run.duration_ms,
                },
            )

    def latest_test_run(self, attempt_id: int) -> RunRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM test_runs WHERE attempt_id = ? ORDER BY ran_at DESC, id DESC "
                "LIMIT 1",
                (attempt_id,),
            ).fetchone()
        return _run_record(row) if row is not None else None

    def schedule_entry(self, slug: str) -> ScheduleEntry | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM schedule WHERE slug = ?", (slug,)).fetchone()
        return _schedule_entry(row) if row is not None else None

    def save_schedule_entry(self, entry: ScheduleEntry) -> None:
        with self._connection() as connection:
            connection.execute(
                _SCHEDULE_UPSERT,
                {
                    "slug": entry.slug,
                    "ease": entry.state.ease,
                    "interval_days": entry.state.interval_days,
                    "reps": entry.state.reps,
                    "lapses": entry.state.lapses,
                    "due_on": entry.due_on.isoformat(),
                    "last_grade": int(entry.last_grade),
                    "updated_at": _instant_text(entry.updated_at),
                },
            )

    def problem_progress(self) -> Mapping[str, ProblemProgress]:
        with self._connection() as connection:
            statuses = connection.execute("SELECT DISTINCT slug, status FROM attempts").fetchall()
            schedules = connection.execute("SELECT * FROM schedule").fetchall()
        by_slug: defaultdict[str, set[AttemptStatus]] = defaultdict(set)
        for row in statuses:
            by_slug[row["slug"]].add(AttemptStatus(row["status"]))
        entries = {row["slug"]: _schedule_entry(row) for row in schedules}
        return {
            slug: ProblemProgress(frozenset(by_slug.get(slug, ())), entries.get(slug))
            for slug in sorted(by_slug.keys() | entries.keys())
        }

    def attempts_in_progress(self) -> tuple[Attempt, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM attempts WHERE status = ? ORDER BY started_at, id",
                (AttemptStatus.IN_PROGRESS,),
            ).fetchall()
        return tuple(_attempt(row) for row in rows)

    def finished_attempts(self) -> tuple[Attempt, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM attempts WHERE status IN (?, ?) ORDER BY ended_at, id",
                (AttemptStatus.PASSED, AttemptStatus.FAILED),
            ).fetchall()
        return tuple(_attempt(row) for row in rows)

    def add_bench_run(self, run: BenchRunRecord) -> None:
        with self._connection() as connection:
            bench_rows.insert_bench_run(connection, run)

    def bench_history(self, slug: str, language: Language) -> tuple[PastRun, ...]:
        with self._connection() as connection:
            return bench_rows.bench_history(connection, slug, language)

    def latest_bench_outcome(self, attempt_id: int) -> BenchOutcome | None:
        with self._connection() as connection:
            return bench_rows.latest_outcome(connection, attempt_id)

    def latest_bench_verdicts(self) -> tuple[LatestBench, ...]:
        with self._connection() as connection:
            rows = connection.execute(_LATEST_USER_BENCHES).fetchall()
        return tuple(
            LatestBench(
                row["slug"],
                Language(row["lang"]),
                Verdict(row["verdict"]),
                _required_instant(row["ran_at"]),
            )
            for row in rows
        )

    def snapshot(self) -> ProgressSnapshot:
        with self._connection() as connection:
            return ProgressSnapshot(
                _schema_version(connection),
                {
                    table: tuple(
                        dict(row)
                        for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
                    )
                    for table in _data_tables(connection)
                },
            )

    def restore(self, snapshot: ProgressSnapshot) -> None:
        with self._connection() as connection:
            _require_restorable(connection, snapshot)
            for table in _data_tables(connection):
                columns = _columns(connection, table)
                for number, row in enumerate(snapshot.tables.get(table, ()), start=1):
                    _insert_row(connection, table, columns, number, row)

    def _one_attempt(self, condition: str, parameters: tuple[object, ...]) -> Attempt | None:
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT * FROM attempts WHERE {condition} {_LATEST_FIRST}", parameters
            ).fetchone()
        return _attempt(row) if row is not None else None

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            if not self._migrated:
                _migrate(connection)
                self._migrated = True
            with connection:
                yield connection
        finally:
            connection.close()


def _migrate(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    applied = _schema_version(connection)
    for number, script in _migrations():
        if number <= applied:
            continue
        connection.executescript(script)
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (SCHEMA_VERSION_KEY, str(number)),
            )


def _schema_version(connection: sqlite3.Connection) -> int:
    has_meta = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if has_meta is None:
        return 0
    row = connection.execute(
        "SELECT value FROM meta WHERE key = ?", (SCHEMA_VERSION_KEY,)
    ).fetchone()
    return int(row["value"]) if row is not None else 0


def _data_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Every table but `meta`, parents before the tables that reference them."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {row["name"] for row in rows} - {META_TABLE}
    known = [name for name in TABLE_ORDER if name in names]
    return (*known, *sorted(names - set(known)))


def _columns(connection: sqlite3.Connection, table: str) -> frozenset[str]:
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return frozenset(row["name"] for row in rows)


def _require_restorable(connection: sqlite3.Connection, snapshot: ProgressSnapshot) -> None:
    current = _schema_version(connection)
    if snapshot.schema_version > current:
        raise UsageError(
            f"the export uses progress.db schema {snapshot.schema_version}, "
            f"which is newer than this cstudy ({current}); update cstudy first"
        )
    tables = _data_tables(connection)
    unknown = next((table for table in snapshot.tables if table not in tables), None)
    if unknown is not None:
        raise UsageError(f'unknown table "{unknown}" in the export')
    if any(connection.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone() for table in tables):
        raise UsageError("progress.db already holds progress; import needs an empty database")


def _insert_row(
    connection: sqlite3.Connection,
    table: str,
    columns: frozenset[str],
    number: int,
    row: Mapping[str, ColumnValue],
) -> None:
    unknown = next((column for column in row if column not in columns), None)
    if unknown is not None:
        raise UsageError(f'unknown column "{unknown}" in {table} row {number}')
    names = ", ".join(f'"{column}"' for column in row)
    placeholders = ", ".join("?" for _ in row)
    try:
        connection.execute(
            f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})', tuple(row.values())
        )
    except sqlite3.Error as error:
        raise UsageError(f"cannot import {table} row {number}: {error}") from None


def _migrations() -> list[tuple[int, str]]:
    directory = resources.files(MIGRATIONS_PACKAGE) / MIGRATIONS_DIRECTORY
    scripts = sorted(
        (entry for entry in directory.iterdir() if entry.name.endswith(MIGRATION_SUFFIX)),
        key=lambda entry: entry.name,
    )
    return [(_migration_number(entry.name), entry.read_text(encoding="utf-8")) for entry in scripts]


def _migration_number(file_name: str) -> int:
    return int(file_name.partition("_")[0])


def _instant_text(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat()


def _instant(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text is not None else None


def _required_instant(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _optional[T](value: Any, convert: Callable[[Any], T]) -> T | None:
    return convert(value) if value is not None else None


def _attempt(row: sqlite3.Row) -> Attempt:
    return Attempt(
        id=row["id"],
        slug=row["slug"],
        language=_optional(row["lang"], Language),
        mode=AttemptMode(row["mode"]),
        status=AttemptStatus(row["status"]),
        started_at=_required_instant(row["started_at"]),
        ended_at=_instant(row["ended_at"]),
        first_pass_at=_instant(row["first_pass_at"]),
        time_limit_s=row["time_limit_s"],
        rating=_optional(row["rating"], Rating),
        grade=_optional(row["grade"], Grade),
        hints_used=row["hints_used"],
        solution_revealed=bool(row["solution_revealed"]),
        level_unlocked=row["level_unlocked"],
        stub_path=row["stub_path"],
        archive_path=row["archive_path"],
        notes=row["notes"],
    )


def _attempt_fields(attempt: Attempt) -> dict[str, object]:
    return {
        "id": attempt.id,
        "status": attempt.status,
        "ended_at": _optional_instant_text(attempt.ended_at),
        "first_pass_at": _optional_instant_text(attempt.first_pass_at),
        "time_limit_s": attempt.time_limit_s,
        "rating": attempt.rating,
        "grade": _optional(attempt.grade, int),
        "hints_used": attempt.hints_used,
        "solution_revealed": int(attempt.solution_revealed),
        "level_unlocked": attempt.level_unlocked,
        "stub_path": attempt.stub_path,
        "archive_path": attempt.archive_path,
        "notes": attempt.notes,
    }


def _optional_instant_text(instant: datetime | None) -> str | None:
    return _instant_text(instant) if instant is not None else None


def _run_record(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        attempt_id=row["attempt_id"],
        ran_at=_required_instant(row["ran_at"]),
        code_hash=row["code_hash"],
        tally=Tally(
            total=row["total"],
            passed=row["passed"],
            failed=row["failed"],
            errored=row["errored"],
            timed_out=row["timed_out"],
            tle=row["tle"],
        ),
        duration_ms=row["duration_ms"],
        time_limit=row["time_limit"],
    )


def _schedule_entry(row: sqlite3.Row) -> ScheduleEntry:
    return ScheduleEntry(
        slug=row["slug"],
        state=ReviewState(
            ease=row["ease"],
            interval_days=row["interval_days"],
            reps=row["reps"],
            lapses=row["lapses"],
        ),
        due_on=date.fromisoformat(row["due_on"]),
        last_grade=Grade(row["last_grade"]),
        updated_at=_required_instant(row["updated_at"]),
    )
