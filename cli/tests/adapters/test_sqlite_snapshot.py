"""progress.db snapshots for `cstudy export` and restores for `cstudy import`."""

import re
from dataclasses import replace

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.domain.progress_export import ProgressSnapshot
from coding_study.domain.submissions import LevelUnlock
from tests.fakes import NOW, make_environment
from tests.stats_fixture import fill_progress

TABLES = ("attempts", "test_runs", "schedule", "bench_runs", "submissions", "level_unlocks")


@pytest.fixture
def store(tmp_path):
    """An empty database, apart from the filled one."""
    return SqliteProgressStore(tmp_path / "empty" / "progress.db")


@pytest.fixture
def filled(content_root):
    environment = make_environment(content_root)
    fill_progress(environment)
    return environment.progress


def test_a_snapshot_names_every_table_but_meta(store):
    assert tuple(store.snapshot().tables) == TABLES


def test_a_snapshot_records_the_schema_version(store):
    assert store.snapshot().schema_version == 5


def test_a_snapshot_holds_every_row(filled):
    assert filled.snapshot().row_counts() == {
        "attempts": 6,
        "test_runs": 4,
        "schedule": 3,
        "bench_runs": 3,
        "submissions": 0,
        "level_unlocks": 0,
    }


def test_a_snapshot_keeps_rows_as_stored(store):
    store.add_attempt(NewAttempt("two-sum", Language.KOTLIN, AttemptMode.NEW, NOW))
    assert store.snapshot().tables["attempts"][0] == {
        "id": 1,
        "slug": "two-sum",
        "lang": "kotlin",
        "mode": "new",
        "status": "in_progress",
        "started_at": "2026-10-24T10:00:00+00:00",
        "ended_at": None,
        "first_pass_at": None,
        "time_limit_s": None,
        "rating": None,
        "grade": None,
        "hints_used": 0,
        "solution_revealed": 0,
        "level_unlocked": None,
        "stub_path": None,
        "archive_path": None,
        "notes": None,
    }


def test_a_restored_snapshot_equals_the_original(filled, store):
    snapshot = filled.snapshot()
    store.restore(snapshot)
    assert store.snapshot() == snapshot


def test_restoring_keeps_attempt_ids_for_later_attempts(filled, store):
    store.restore(filled.snapshot())
    added = store.add_attempt(NewAttempt("two-sum", Language.PYTHON, AttemptMode.NEW, NOW))
    assert added.id == 7


def test_restoring_into_a_database_with_progress_is_refused(filled):
    with pytest.raises(UsageError, match="already holds progress"):
        filled.restore(filled.snapshot())


def test_an_export_carries_level_unlocks(store):
    attempt = store.add_attempt(NewAttempt("bank", Language.PYTHON, AttemptMode.NEW, NOW))
    store.add_level_unlock(LevelUnlock(attempt.id, 1, NOW))
    assert store.snapshot().tables["level_unlocks"] == (
        {"attempt_id": attempt.id, "level": 1, "unlocked_at": NOW.isoformat()},
    )


def test_a_refused_restore_changes_nothing(filled):
    before = filled.snapshot()
    with pytest.raises(UsageError):
        filled.restore(before)
    assert filled.snapshot() == before


def test_a_snapshot_from_a_newer_schema_is_refused(store):
    with pytest.raises(
        UsageError, match=re.escape("schema 6, which is newer than this cstudy (5)")
    ):
        store.restore(ProgressSnapshot(6, {}))


def test_an_unknown_table_is_refused(store):
    with pytest.raises(UsageError, match='unknown table "scores"'):
        store.restore(ProgressSnapshot(3, {"scores": ()}))


def test_an_unknown_column_is_refused(store):
    with pytest.raises(UsageError, match='unknown column "colour" in attempts'):
        store.restore(ProgressSnapshot(3, {"attempts": ({"colour": "red"},)}))


def test_a_row_sqlite_rejects_is_refused_and_nothing_is_imported(filled, store):
    snapshot = filled.snapshot()
    rows = list(snapshot.tables["schedule"])
    rows[1] = {**rows[1], "ease": None}
    broken = replace(snapshot, tables={**snapshot.tables, "schedule": tuple(rows)})
    with pytest.raises(UsageError, match="schedule row 2"):
        store.restore(broken)
    assert store.snapshot().row_counts() == dict.fromkeys(TABLES, 0)
