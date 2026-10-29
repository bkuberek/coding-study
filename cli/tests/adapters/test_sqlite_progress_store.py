import sqlite3
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from importlib import resources
from pathlib import Path

import pytest

from coding_study.adapters.sqlite.progress_store import (
    MIGRATIONS_DIRECTORY,
    MIGRATIONS_PACKAGE,
    SqliteProgressStore,
)
from coding_study.domain.attempts import (
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ProblemProgress, ReviewState, ScheduleEntry

STARTED = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    return tmp_path / "progress.db"


@pytest.fixture
def store(database: Path) -> SqliteProgressStore:
    return SqliteProgressStore(database)


def new_attempt(
    slug: str = "two-sum", language: Language | None = Language.PYTHON, minutes: int = 0
) -> NewAttempt:
    return NewAttempt(
        slug=slug,
        language=language,
        mode=AttemptMode.NEW,
        started_at=STARTED + timedelta(minutes=minutes),
        time_limit_s=1500,
        stub_path="python/practice/two_sum.py",
    )


def run_record(attempt_id: int, passed: int = 2, minutes: int = 1) -> RunRecord:
    return RunRecord(
        attempt_id=attempt_id,
        ran_at=STARTED + timedelta(minutes=minutes),
        code_hash="abc",
        tally=Tally(total=2, passed=passed, failed=2 - passed),
        duration_ms=840,
    )


def test_creates_the_database_with_the_phase_tables(store, database):
    store.active_attempt()
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"meta", "attempts", "test_runs", "schedule"} <= tables


def test_records_the_schema_version(store, database):
    store.active_attempt()
    migrations = resources.files(MIGRATIONS_PACKAGE) / MIGRATIONS_DIRECTORY
    latest = max(int(entry.name.partition("_")[0]) for entry in migrations.iterdir())
    with sqlite3.connect(database) as connection:
        version = connection.execute("SELECT value FROM meta WHERE key = 'schema_version'")
        assert version.fetchone() == (str(latest),)


def test_reopening_an_existing_database_keeps_its_rows(store, database):
    store.add_attempt(new_attempt())
    assert SqliteProgressStore(database).active_attempt() is not None


def test_added_attempts_are_in_progress(store):
    assert store.add_attempt(new_attempt()).status is AttemptStatus.IN_PROGRESS


def test_added_attempts_keep_their_fields(store):
    attempt = store.add_attempt(new_attempt())
    assert (attempt.slug, attempt.language, attempt.started_at, attempt.time_limit_s) == (
        "two-sum",
        Language.PYTHON,
        STARTED,
        1500,
    )


def test_attempts_without_a_language_are_allowed(store):
    assert store.add_attempt(new_attempt(language=None)).language is None


@pytest.mark.parametrize("language", list(Language))
def test_attempts_in_every_language_are_allowed(store, language):
    assert store.add_attempt(new_attempt(language=language)).language is language


def database_before_go_and_rust(database: Path) -> None:
    """A progress database at schema version 3, with an attempt and its test run."""
    migrations = resources.files(MIGRATIONS_PACKAGE) / MIGRATIONS_DIRECTORY
    scripts = sorted(
        (entry for entry in migrations.iterdir() if entry.name.endswith(".sql")),
        key=lambda entry: entry.name,
    )
    with sqlite3.connect(database) as connection:
        for script in scripts[:3]:
            connection.executescript(script.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO meta (key, value) VALUES ('schema_version', '3')")
        connection.execute(
            "INSERT INTO attempts (id, slug, lang, mode, status, started_at) "
            "VALUES (7, 'two-sum', 'java', 'new', 'in_progress', '2026-10-24T10:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO test_runs (attempt_id, ran_at, code_hash, total, passed, failed, "
            "errored, timed_out, tle, duration_ms) "
            "VALUES (7, '2026-10-24T10:01:00+00:00', 'abc', 2, 2, 0, 0, 0, 0, 840)"
        )


def test_migrating_keeps_attempts_and_their_test_runs(database):
    database_before_go_and_rust(database)
    store = SqliteProgressStore(database)
    assert (store.active_attempt(), store.latest_test_run(7)) != (None, None)
    assert store.add_attempt(new_attempt(language=Language.GO)).language is Language.GO


def test_migrated_test_runs_still_require_an_existing_attempt(database):
    database_before_go_and_rust(database)
    with pytest.raises(sqlite3.IntegrityError):
        SqliteProgressStore(database).add_test_run(run_record(999))


def test_attempt_ids_increase(store):
    first, second = store.add_attempt(new_attempt()), store.add_attempt(new_attempt())
    assert second.id > first.id


def test_no_active_attempt_in_an_empty_database(store):
    assert store.active_attempt() is None


def test_active_attempt_is_the_most_recently_started(store):
    store.add_attempt(new_attempt("two-sum", minutes=0))
    latest = store.add_attempt(new_attempt("lru-cache", minutes=5))
    assert store.active_attempt() == latest


def test_active_attempt_ignores_finished_attempts(store):
    first = store.add_attempt(new_attempt("two-sum", minutes=0))
    finished = store.add_attempt(new_attempt("lru-cache", minutes=5))
    store.update_attempt(replace(finished, status=AttemptStatus.PASSED))
    assert store.active_attempt() == first


def test_active_attempt_for_a_slug(store):
    wanted = store.add_attempt(new_attempt("two-sum", minutes=0))
    store.add_attempt(new_attempt("lru-cache", minutes=5))
    assert store.active_attempt("two-sum") == wanted


def test_in_progress_attempt_matches_slug_and_language(store):
    store.add_attempt(new_attempt(language=Language.KOTLIN))
    wanted = store.add_attempt(new_attempt(language=Language.PYTHON))
    assert store.in_progress_attempt("two-sum", Language.PYTHON) == wanted


def test_in_progress_attempt_is_none_after_abandoning(store):
    attempt = store.add_attempt(new_attempt())
    store.update_attempt(replace(attempt, status=AttemptStatus.ABANDONED))
    assert store.in_progress_attempt("two-sum", Language.PYTHON) is None


def test_latest_attempt_includes_finished_attempts(store):
    attempt = store.add_attempt(new_attempt())
    finished = replace(attempt, status=AttemptStatus.FAILED)
    store.update_attempt(finished)
    assert store.latest_attempt("two-sum", Language.PYTHON) == finished


def test_update_stores_every_mutable_field(store):
    attempt = store.add_attempt(new_attempt())
    updated = replace(
        attempt,
        status=AttemptStatus.PASSED,
        ended_at=STARTED + timedelta(minutes=20),
        first_pass_at=STARTED + timedelta(minutes=15),
        rating=Rating.OK,
        grade=Grade.OK,
        hints_used=1,
        solution_revealed=True,
        level_unlocked=2,
        archive_path=".archive/two-sum/1-python",
        notes="used a map",
    )
    store.update_attempt(updated)
    assert store.latest_attempt("two-sum", Language.PYTHON) == updated


def test_latest_test_run_of_an_attempt(store):
    attempt = store.add_attempt(new_attempt())
    store.add_test_run(run_record(attempt.id, passed=1, minutes=1))
    store.add_test_run(run_record(attempt.id, passed=2, minutes=2))
    assert store.latest_test_run(attempt.id) == run_record(attempt.id, passed=2, minutes=2)


def test_no_test_run_yet(store):
    attempt = store.add_attempt(new_attempt())
    assert store.latest_test_run(attempt.id) is None


def test_test_runs_keep_the_time_limit(store):
    attempt = store.add_attempt(new_attempt())
    record = replace(run_record(attempt.id), time_limit="5x")
    store.add_test_run(record)
    assert store.latest_test_run(attempt.id) == record


def test_test_runs_require_an_existing_attempt(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_test_run(run_record(999))


def schedule_entry(interval: int = 3) -> ScheduleEntry:
    return ScheduleEntry(
        slug="two-sum",
        state=ReviewState(ease=2.35, interval_days=interval, reps=1, lapses=0),
        due_on=date(2026, 10, 27),
        last_grade=Grade.OK,
        updated_at=STARTED,
    )


def test_no_schedule_entry_for_a_new_problem(store):
    assert store.schedule_entry("two-sum") is None


def test_saved_schedule_entries_round_trip(store):
    store.save_schedule_entry(schedule_entry())
    assert store.schedule_entry("two-sum") == schedule_entry()


def test_saving_a_schedule_entry_replaces_the_previous_one(store):
    store.save_schedule_entry(schedule_entry(interval=3))
    store.save_schedule_entry(schedule_entry(interval=7))
    assert store.schedule_entry("two-sum") == schedule_entry(interval=7)


def test_problem_progress_collects_attempt_statuses_and_schedule(store):
    attempt = store.add_attempt(new_attempt())
    store.update_attempt(replace(attempt, status=AttemptStatus.PASSED))
    store.add_attempt(new_attempt())
    store.save_schedule_entry(schedule_entry())
    expected = ProblemProgress(
        frozenset({AttemptStatus.PASSED, AttemptStatus.IN_PROGRESS}), schedule_entry()
    )
    assert store.problem_progress() == {"two-sum": expected}


def test_problem_progress_is_empty_without_attempts(store):
    assert store.problem_progress() == {}


def finish(store: SqliteProgressStore, status: AttemptStatus, minutes: int) -> None:
    attempt = store.add_attempt(new_attempt(minutes=minutes))
    ended = STARTED + timedelta(minutes=minutes + 5)
    store.update_attempt(replace(attempt, status=status, ended_at=ended, grade=Grade.OK))


def test_finished_attempts_are_the_passed_and_failed_ones_by_end_time(store):
    finish(store, AttemptStatus.FAILED, minutes=30)
    finish(store, AttemptStatus.ABANDONED, minutes=20)
    finish(store, AttemptStatus.PASSED, minutes=10)
    store.add_attempt(new_attempt(minutes=40))
    assert [attempt.status for attempt in store.finished_attempts()] == [
        AttemptStatus.PASSED,
        AttemptStatus.FAILED,
    ]
