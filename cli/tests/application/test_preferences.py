import pytest

from coding_study.application.preferences import read_preferences, save_preferences
from coding_study.domain.errors import UsageError
from coding_study.domain.preferences import Preferences


class MemoryPreferencesStore:
    """`.cs/serve/preferences.json` in memory: `None` is a missing or unreadable file."""

    def __init__(self, document: object = None) -> None:
        self.document = document
        self.writes = 0

    def read(self) -> object:
        return self.document

    def write(self, document: dict[str, object]) -> None:
        self.document = document
        self.writes += 1


def test_a_missing_file_means_the_defaults():
    assert read_preferences(MemoryPreferencesStore()) == Preferences()


def test_a_stored_document_is_read():
    store = MemoryPreferencesStore({"format": 1, "vim": True})
    assert read_preferences(store) == Preferences(vim=True)


def test_a_document_that_does_not_parse_means_the_defaults():
    store = MemoryPreferencesStore({"format": 1, "vim": "yes"})
    assert read_preferences(store) == Preferences()


def test_saving_returns_the_preferences():
    assert save_preferences(MemoryPreferencesStore(), {"vim": True}) == Preferences(vim=True)


def test_saving_writes_the_whole_document():
    store = MemoryPreferencesStore()
    save_preferences(store, {"vim": True})
    assert store.document == {
        "format": 1,
        "vim": True,
        "run_on_save": False,
        "typecheck": True,
        "theme": "system",
    }


def test_an_invalid_document_is_refused_and_nothing_is_written():
    store = MemoryPreferencesStore()
    with pytest.raises(UsageError):
        save_preferences(store, {"font": "serif"})
    assert store.writes == 0
