import threading
from pathlib import Path

import pytest

from coding_study.adapters.watchfiles_watcher import WatchfilesWatcher

pytestmark = pytest.mark.slow

SAVE_AFTER_SECONDS = 0.3
GIVE_UP_AFTER_SECONDS = 5.0
QUIET_PERIOD_SECONDS = 1.0
STOPPED = "stopped"


def first_change(watcher: WatchfilesWatcher, path: Path, stop: threading.Event, save: Path):
    """The first item `changes(path)` yields after `save` is written, or STOPPED."""
    timer = threading.Timer(SAVE_AFTER_SECONDS, lambda: save.write_text("changed\n"))
    timer.start()
    try:
        return next(watcher.changes(path), STOPPED)
    finally:
        timer.cancel()
        stop.set()


def test_saving_the_watched_file_yields(tmp_path):
    target = tmp_path / "two_sum.py"
    target.write_text("original\n")
    stop = threading.Event()
    threading.Timer(GIVE_UP_AFTER_SECONDS, stop.set).start()
    assert first_change(WatchfilesWatcher(stop_event=stop), target, stop, target) is None


def test_saving_another_file_in_the_directory_is_ignored(tmp_path):
    target = tmp_path / "two_sum.py"
    target.write_text("original\n")
    stop = threading.Event()
    threading.Timer(QUIET_PERIOD_SECONDS, stop.set).start()
    other = tmp_path / "lru_cache.py"
    assert first_change(WatchfilesWatcher(stop_event=stop), target, stop, other) == STOPPED


def test_saving_inside_a_watched_directory_yields(tmp_path):
    package = tmp_path / "two_sum"
    package.mkdir()
    stop = threading.Event()
    threading.Timer(GIVE_UP_AFTER_SECONDS, stop.set).start()
    saved = package / "Solution.java"
    assert first_change(WatchfilesWatcher(stop_event=stop), package, stop, saved) is None
