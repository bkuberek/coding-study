"""`guide_reads` in progress.db (docs/specs/progress-and-scheduling.md#schema): guides marked read
with `cstudy learn <guide> --done`."""

from datetime import timedelta
from pathlib import Path

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from tests.fakes import NOW


def test_a_guide_marked_read_is_read_from_then_on(tmp_path: Path):
    store = SqliteProgressStore(tmp_path / "progress.db")
    assert (store.mark_guide_read("hash-maps", NOW), store.guide_reads()) == (
        None,
        {"hash-maps": NOW},
    )


def test_marking_again_keeps_the_first_time(tmp_path: Path):
    store = SqliteProgressStore(tmp_path / "progress.db")
    store.mark_guide_read("hash-maps", NOW)
    assert store.mark_guide_read("hash-maps", NOW + timedelta(days=1)) == NOW


def test_a_reset_forgets_what_was_read(tmp_path: Path):
    store = SqliteProgressStore(tmp_path / "progress.db")
    store.mark_guide_read("hash-maps", NOW)
    store.clear()
    assert store.guide_reads() == {}


def test_an_export_carries_what_was_read(tmp_path: Path):
    store = SqliteProgressStore(tmp_path / "progress.db")
    store.mark_guide_read("hash-maps", NOW)
    restored = SqliteProgressStore(tmp_path / "restored.db")
    restored.restore(store.snapshot())
    assert restored.guide_reads() == {"hash-maps": NOW}
