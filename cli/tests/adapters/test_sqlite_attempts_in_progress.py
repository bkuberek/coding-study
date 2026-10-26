"""The progress.db query behind the `cstudy mock` lock."""

from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, AttemptStatus, NewAttempt
from coding_study.domain.problem import Language
from tests.fakes import NOW


@pytest.fixture
def store(tmp_path):
    return SqliteProgressStore(tmp_path / "progress.db")


def start(store, slug: str, minutes_later: int = 0):
    started_at = NOW + timedelta(minutes=minutes_later)
    return store.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.MOCK, started_at))


def test_attempts_in_progress_are_earliest_first(store):
    start(store, "b", minutes_later=5)
    start(store, "a")
    assert [attempt.slug for attempt in store.attempts_in_progress()] == ["a", "b"]


def test_finished_attempts_are_not_in_progress(store):
    attempt = start(store, "a")
    store.update_attempt(replace(attempt, status=AttemptStatus.PASSED, ended_at=NOW))
    assert store.attempts_in_progress() == ()


def test_attempts_in_progress_keep_their_mode(store):
    start(store, "a")
    assert store.attempts_in_progress()[0].mode is AttemptMode.MOCK
