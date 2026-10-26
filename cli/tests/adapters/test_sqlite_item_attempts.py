from datetime import UTC, datetime

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.problem import Language

STARTED = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path) -> SqliteProgressStore:
    return SqliteProgressStore(tmp_path / "progress.db")


def add(store: SqliteProgressStore, language: Language | None):
    return store.add_attempt(NewAttempt("url-shortener", language, AttemptMode.NEW, STARTED))


def test_latest_attempt_without_a_language_finds_item_attempts(store):
    item = add(store, None)
    assert store.latest_attempt("url-shortener", None) == item


def test_latest_attempt_without_a_language_ignores_language_attempts(store):
    add(store, Language.PYTHON)
    assert store.latest_attempt("url-shortener", None) is None


def test_in_progress_attempt_without_a_language(store):
    item = add(store, None)
    assert store.in_progress_attempt("url-shortener", None) == item
