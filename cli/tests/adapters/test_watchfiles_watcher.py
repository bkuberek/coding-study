import asyncio
import threading
from pathlib import Path

import pytest

from coding_study.adapters.watchfiles_watcher import WatchfilesWatcher
from coding_study.application.attempt_changes import WatchedFolder

pytestmark = pytest.mark.slow

SAVE_AFTER_SECONDS = 0.3
GIVE_UP_AFTER_SECONDS = 5.0
QUIET_PERIOD_SECONDS = 1.0
SETTLE_SECONDS = 1.0
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


# project folders (docs/specs/installation-and-workspaces.md#project-folders)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "projects" / "bank-project-python"
    for directory in ("bank/ledger", "bank/__pycache__", ".pytest_cache", "node_modules"):
        (folder / directory).mkdir(parents=True)
    (folder / "bank" / "bank.py").write_text("class Bank: ...\n")
    return folder


def test_saving_a_nested_file_of_a_project_folder_yields(project):
    stop = threading.Event()
    threading.Timer(GIVE_UP_AFTER_SECONDS, stop.set).start()
    saved = project / "bank" / "ledger" / "entries.py"
    assert first_change(WatchfilesWatcher(stop_event=stop), project, stop, saved) is None


@pytest.mark.parametrize(
    "untracked",
    ["bank/__pycache__/bank.cpython-313.pyc", ".pytest_cache/lastfailed", "node_modules/x.js"],
)
def test_saving_an_untracked_file_of_a_project_folder_is_ignored(project, untracked):
    stop = threading.Event()
    threading.Timer(QUIET_PERIOD_SECONDS, stop.set).start()
    saved = project / untracked
    assert first_change(WatchfilesWatcher(stop_event=stop), project, stop, saved) == STOPPED


# several folders at once, for the web UI's notifications (docs/specs/web-ui.md#notifications)

WORKSPACE_FOLDERS = (
    WatchedFolder("projects/bank-project-python", True),
    WatchedFolder(".statements", False),
    WatchedFolder(".", False, frozenset({"progress.db", "progress.db-wal"})),
)


@pytest.fixture
def workspace(project: Path) -> Path:
    root = project.parents[1]
    (root / ".statements").mkdir()
    (root / ".statements" / "inner").mkdir()
    return root


def folder_change(root: Path, saved: Path, wait_seconds: float) -> str:
    """`yielded` when `folder_changes` yields within `wait_seconds` after `saved` is written,
    else STOPPED. It writes once the watch had time to report what the fixture just created,
    which macOS may still deliver to a new watch."""

    async def watch() -> str:
        stop = asyncio.Event()
        written = asyncio.Event()

        async def write_then_stop() -> None:
            await asyncio.sleep(SETTLE_SECONDS)
            saved.write_text("changed\n")
            written.set()
            await asyncio.sleep(wait_seconds)
            stop.set()

        writing = asyncio.create_task(write_then_stop())
        changes = WatchfilesWatcher().folder_changes(root, WORKSPACE_FOLDERS, stop)
        try:
            async for _ in changes:
                if written.is_set():
                    return "yielded"
            return STOPPED
        finally:
            await changes.aclose()
            writing.cancel()

    return asyncio.run(watch())


@pytest.mark.parametrize(
    "saved",
    [
        "projects/bank-project-python/bank/ledger/entries.py",
        ".statements/two-sum.md",
        "progress.db",
    ],
)
def test_saving_in_any_watched_folder_yields(workspace, saved):
    assert folder_change(workspace, workspace / saved, GIVE_UP_AFTER_SECONDS) == "yielded"


@pytest.mark.parametrize(
    "ignored",
    [
        "projects/bank-project-python/node_modules/x.js",
        ".statements/inner/nested.md",
        "progress.db-shm",
        "notes.md",
    ],
)
def test_saving_what_no_watched_folder_covers_is_ignored(workspace, ignored):
    assert folder_change(workspace, workspace / ignored, QUIET_PERIOD_SECONDS) == STOPPED
