"""`submissions` and `level_unlocks` in progress.db
(docs/specs/progress-and-scheduling.md#schema)."""

import sqlite3
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path

import pytest

from coding_study.adapters.sqlite.progress_store import (
    MIGRATIONS_DIRECTORY,
    MIGRATIONS_PACKAGE,
    SqliteProgressStore,
)
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.submissions import LevelTally, LevelUnlock, SubmissionRecord

STARTED = datetime(2026, 10, 30, 17, 0, tzinfo=UTC)
PROJECT_MIGRATION = "0005_project_problems.sql"


@pytest.fixture
def store(tmp_path: Path) -> SqliteProgressStore:
    return SqliteProgressStore(tmp_path / "progress.db")


@pytest.fixture
def attempt_id(store: SqliteProgressStore) -> int:
    attempt = NewAttempt(
        "bank-project-python", Language.PYTHON, AttemptMode.NEW, STARTED, None, "projects/bank"
    )
    return store.add_attempt(attempt).id


def submission(attempt_id: int, minutes: int = 1, every_level: bool = True) -> SubmissionRecord:
    return SubmissionRecord(
        attempt_id=attempt_id,
        submitted_at=STARTED + timedelta(minutes=minutes),
        code_hash="f00d",
        graded_up_to=2,
        every_level=every_level,
        levels=(LevelTally(1, 2, 2, 3, 3), LevelTally(2, 2, 2, 3, 2)),
        tally=Tally(total=10, passed=9, failed=1),
        duration_ms=420,
    )


def test_a_submission_reads_back_as_stored(store, attempt_id):
    stored = submission(attempt_id)
    store.add_submission(stored)
    assert store.submissions(attempt_id) == (stored,)


def test_submissions_come_back_earliest_first(store, attempt_id):
    later, earlier = submission(attempt_id, minutes=5), submission(attempt_id, minutes=2)
    store.add_submission(later)
    store.add_submission(earlier)
    assert store.submissions(attempt_id) == (earlier, later)


def test_submissions_belong_to_their_attempt(store, attempt_id):
    store.add_submission(submission(attempt_id))
    assert store.submissions(attempt_id + 1) == ()


def test_a_submission_needs_an_existing_attempt(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_submission(submission(999))


def test_the_levels_column_holds_json_per_level(store, attempt_id, tmp_path):
    store.add_submission(submission(attempt_id))
    with sqlite3.connect(tmp_path / "progress.db") as connection:
        (levels,) = connection.execute("SELECT levels FROM submissions").fetchone()
    assert levels.startswith(
        '[{"level": 1, "total": 5, "passed": 5, "visible_total": 2, "visible_passed": 2, '
        '"hidden_total": 3, "hidden_passed": 3}'
    )


def test_level_unlocks_come_back_by_level(store, attempt_id):
    second = LevelUnlock(attempt_id, 2, STARTED + timedelta(minutes=30))
    first = LevelUnlock(attempt_id, 1, STARTED)
    store.add_level_unlock(second)
    store.add_level_unlock(first)
    assert store.level_unlocks(attempt_id) == (first, second)


def test_a_level_opens_once(store, attempt_id):
    store.add_level_unlock(LevelUnlock(attempt_id, 1, STARTED))
    store.add_level_unlock(LevelUnlock(attempt_id, 1, STARTED + timedelta(minutes=1)))
    assert store.level_unlocks(attempt_id) == (LevelUnlock(attempt_id, 1, STARTED),)


def test_the_project_migration_can_run_twice(tmp_path):
    script = resources.files(MIGRATIONS_PACKAGE) / MIGRATIONS_DIRECTORY / PROJECT_MIGRATION
    store = SqliteProgressStore(tmp_path / "progress.db")
    store.active_attempt()
    with sqlite3.connect(tmp_path / "progress.db") as connection:
        connection.executescript(script.read_text(encoding="utf-8"))
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"submissions", "level_unlocks", "submissions_by_attempt"} <= tables
