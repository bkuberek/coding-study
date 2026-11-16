"""The Settings view's removal dialog in a real browser (docs/specs/web-ui.md#settings-view), in
each engine of `tests/browsers.py`: a Save that removes a language asks first, before any store is
written; Keep the folder has the focus and goes on with the folder kept; Cancel and Escape write
nothing and keep the change staged; Delete the folder reads the preview and asks again, naming the
command, what goes with its counts, what stays and why, then deletes the folder; an attempt in
progress disables the delete with the CLI's reason tied to it while Keep stays available.

The workspaces are made by `cstudy init`, nothing is run. Playwright and its engines are set up as
`tests/browsers.py` says; without them the test is skipped.
"""

import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.config import DEFAULT_PROGRESS_DB
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
SAVE = ".settings-bar button[type=submit]"
STATUS = ".settings-bar p[role=status]"
COUNT = ".settings-count"
SHEET = "dialog.sheet[open]"
LANGUAGE = "#profile-lang-"
LISTED = ".listing:not([aria-busy]) table.problems tbody tr"
SLUG = "two-sum"


def _init(workspace: Path, *languages: str) -> Path:
    flags = [flag for language in languages for flag in ("--lang", language)]
    subprocess.run(
        [sys.executable, "-m", "coding_study", "init", str(workspace), *flags],
        env=served_environment(workspace),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return workspace


def _languages(workspace: Path) -> list[str]:
    return tomllib.loads((workspace / ".cs" / "workspace.toml").read_text())["languages"]


def _open_settings(page: Any) -> None:
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector(f"{LANGUAGE}python")


def _status(page: Any, text: str) -> str:
    page.wait_for_selector(f"{STATUS}:has-text('{text}')")
    return page.locator(STATUS).inner_text()


def _save(page: Any) -> None:
    page.click(SAVE)
    page.wait_for_selector(SHEET)


def _dialog_text(page: Any, selector: str) -> str:
    return _words(page.locator(f"{SHEET} {selector}").inner_text())


def _words(text: str) -> str:
    return " ".join(text.split())


@dataclass
class Removed:
    """What the dialog said and did, step by step."""

    title: str = ""
    first_command: str = ""
    first_buttons: list[str] = field(default_factory=list[str])
    first_focus: str = ""
    shared_command: str = ""
    shared_keep: str = ""
    shared_delete: list[str] = field(default_factory=list[str])
    cancel_status: str = ""
    marker_after_cancel: list[str] = field(default_factory=list[str])
    folder_after_cancel: bool = False
    count_after_cancel: str = ""
    box_after_cancel: bool = True
    escape_status: str = ""
    marker_after_escape: list[str] = field(default_factory=list[str])
    second_command: str = ""
    goes: list[str] = field(default_factory=list[str])
    stays: str = ""
    warning: str = ""
    delete_button: str = ""
    delete_enabled: bool = False
    focus_on_second: str = ""
    back_focus: str = ""
    dialog_closed: bool = False
    deleted_status: str = ""
    marker_after_delete: list[str] = field(default_factory=list[str])
    go_folder: bool = True
    go_work: bool = True
    notes_kept: bool = False
    projects_kept: bool = False
    progress_kept: bool = False
    kept_status: str = ""
    marker_after_keep: list[str] = field(default_factory=list[str])
    rust_folder: bool = False
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    languages = ("python", "go", "rust", "java", "kotlin")
    return _init(tmp_path_factory.mktemp(f"removal-{engine}") / "workspace", *languages)


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def removed(engine: str, workspace: Path, server: RunningServer) -> Removed:
    seen = Removed()
    marker = workspace / ".cs" / "workspace.toml"
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(LISTED)
        _open_settings(page)
        # A folder two languages share stays, and the dialog says so.
        page.uncheck(f"{LANGUAGE}java")
        _save(page)
        page.click(f"{SHEET} button:has-text('Delete the folder…')")
        page.wait_for_selector(f"{SHEET} .removal-keeps")
        seen.shared_command = _dialog_text(page, ".sheet-command")
        seen.shared_keep = _dialog_text(page, ".removal-keeps")
        seen.shared_delete = page.locator(f"{SHEET} .removal-goes li").all_inner_texts()
        page.click(f"{SHEET} button:has-text('Cancel')")
        page.wait_for_selector(SHEET, state="detached")
        page.check(f"{LANGUAGE}java")
        # The first step of a removal of Go.
        page.uncheck(f"{LANGUAGE}go")
        _save(page)
        seen.title = page.locator(f"{SHEET} h2").inner_text()
        seen.first_command = _dialog_text(page, ".sheet-command")
        seen.first_buttons = page.locator(f"{SHEET} .sheet-actions button").all_inner_texts()
        seen.first_focus = page.evaluate("document.activeElement?.textContent")
        # Cancel writes no store and keeps the change staged.
        page.click(f"{SHEET} button:has-text('Cancel')")
        page.wait_for_selector(SHEET, state="detached")
        seen.cancel_status = _status(page, "not saved")
        seen.marker_after_cancel = _languages(workspace)
        seen.folder_after_cancel = (workspace / "go").is_dir()
        seen.count_after_cancel = page.locator(COUNT).inner_text()
        seen.box_after_cancel = page.is_checked(f"{LANGUAGE}go")
        # So does Escape.
        _save(page)
        page.keyboard.press("Escape")
        page.wait_for_selector(SHEET, state="detached")
        seen.escape_status = _status(page, "not saved")
        seen.marker_after_escape = _languages(workspace)
        # The second step.
        _save(page)
        page.click(f"{SHEET} button:has-text('Delete the folder…')")
        page.wait_for_selector(f"{SHEET} .removal-goes")
        seen.second_command = _dialog_text(page, ".sheet-command")
        seen.goes = page.locator(f"{SHEET} .removal-goes li").all_inner_texts()
        seen.stays = _words(_dialog_text(page, ".quiet:has-text('Always stays')"))
        seen.warning = _dialog_text(page, ".question:has-text('undone')")
        seen.delete_button = page.locator(f"{SHEET} button.danger").inner_text()
        seen.delete_enabled = page.is_enabled(f"{SHEET} button.danger")
        seen.focus_on_second = page.evaluate("document.activeElement?.textContent")
        page.click(f"{SHEET} button:has-text('Back')")
        seen.back_focus = page.evaluate("document.activeElement?.textContent")
        page.click(f"{SHEET} button:has-text('Delete the folder…')")
        page.wait_for_selector(f"{SHEET} button.danger")
        notes = workspace / "notes"
        projects = workspace / "projects"
        progress = workspace / DEFAULT_PROGRESS_DB
        before = (notes.is_dir(), projects.is_dir(), progress.exists())
        page.click(f"{SHEET} button.danger")
        page.wait_for_selector(SHEET, state="detached")
        seen.dialog_closed = True
        seen.deleted_status = _status(page, "deleted")
        seen.marker_after_delete = _languages(workspace)
        seen.go_folder = (workspace / "go").exists()
        seen.go_work = (workspace / "go.work").exists()
        after = (notes.is_dir(), projects.is_dir(), progress.exists())
        seen.notes_kept, seen.projects_kept = after[0] == before[0], after[1] == before[1]
        seen.progress_kept = after[2] or not before[2]
        # Keep the folder goes on with the Save.
        page.uncheck(f"{LANGUAGE}rust")
        _save(page)
        page.click(f"{SHEET} button:has-text('Keep the folder')")
        page.wait_for_selector(SHEET, state="detached")
        seen.kept_status = _status(page, "rust removed").splitlines()[0]
        seen.marker_after_keep = _languages(workspace)
        seen.rust_folder = (workspace / "rust").is_dir()
        assert marker.is_file()
        browser.close()
    return seen


def test_a_save_that_removes_a_language_asks_in_a_dialog_titled_for_it(removed):
    assert removed.title == "Remove go from this workspace"
    assert removed.first_command == "as cstudy lang remove go"


def test_the_first_step_offers_keep_delete_and_cancel_with_the_focus_on_keep(removed):
    assert removed.first_buttons == ["Cancel", "Delete the folder…", "Keep the folder"]
    assert removed.first_focus == "Keep the folder"


def test_cancel_and_escape_write_no_store_and_keep_the_change_staged(removed):
    assert removed.cancel_status == removed.escape_status == "not saved"
    assert removed.marker_after_cancel == removed.marker_after_escape
    assert "go" in removed.marker_after_cancel
    assert removed.folder_after_cancel
    assert (removed.count_after_cancel, removed.box_after_cancel) == ("1 change", False)


def test_delete_the_folder_shows_the_command_the_page_runs(removed):
    assert removed.second_command == "as cstudy lang remove go --delete-folder"


def test_the_second_step_lists_the_folders_that_go_with_their_counts(removed):
    assert len(removed.goes) == 1
    assert re.fullmatch(r"go/ and go\.work · \d+ practice files?", removed.goes[0])


def test_the_second_step_says_what_stays_and_that_it_cannot_be_undone(removed):
    assert removed.stays == "Always stays: progress, .archive/, projects/ and notes/."
    assert removed.warning == "This can't be undone."


def test_the_delete_button_names_the_folders_and_the_focus_is_on_back(removed):
    assert removed.delete_button == "Delete go/ and go.work"
    assert removed.delete_enabled
    assert removed.focus_on_second == "Back"
    assert removed.back_focus == "Keep the folder"


def test_a_folder_a_remaining_language_uses_stays_and_the_dialog_says_why(removed):
    assert removed.shared_command == "as cstudy lang remove java --delete-folder"
    assert removed.shared_keep == "jvm/: kotlin still uses it"
    assert removed.shared_delete == []


def test_the_second_confirmation_deletes_the_folder_and_says_what_went(removed):
    assert re.fullmatch(
        r"languages saved in \.cs/workspace\.toml: go removed: "
        r"go/ and go\.work deleted \(\d+ practice files?\)",
        removed.deleted_status,
    )
    assert "go" not in removed.marker_after_delete
    assert (removed.go_folder, removed.go_work) == (False, False)


def test_a_deletion_leaves_progress_notes_and_projects_alone(removed):
    assert (removed.notes_kept, removed.projects_kept, removed.progress_kept) == (True, True, True)


def test_keep_the_folder_goes_on_with_the_save_and_leaves_the_folder(removed):
    assert removed.kept_status.endswith("rust removed: rust/ stays on disk")
    assert "rust" not in removed.marker_after_keep
    assert removed.rust_folder


def test_the_dialog_logs_no_error_or_warning(removed):
    assert removed.errors == []


@dataclass
class Busy:
    """A removal of a language with an attempt in progress."""

    delete_disabled: bool = False
    reason: str = ""
    reason_tied: bool = False
    first_step_after_back: str = ""
    marker_before_keep: list[str] = field(default_factory=list[str])
    kept_status: str = ""
    kept_lines: list[str] = field(default_factory=list[str])
    marker_after_keep: list[str] = field(default_factory=list[str])
    folder_kept: bool = False
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def go_workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = _init(tmp_path_factory.mktemp(f"removal-busy-{engine}") / "workspace", "python", "go")
    store = SqliteProgressStore(root / DEFAULT_PROGRESS_DB)
    store.add_attempt(NewAttempt(SLUG, Language.GO, AttemptMode.NEW, datetime.now(UTC)))
    return root


@pytest.fixture(scope="module")
def go_server(go_workspace: Path) -> Iterator[RunningServer]:
    with running_server(go_workspace) as running:
        yield running


@pytest.fixture(scope="module")
def busy(engine: str, go_workspace: Path, go_server: RunningServer) -> Busy:
    seen = Busy()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(go_server.login_url)
        page.wait_for_selector(LISTED)
        _open_settings(page)
        page.uncheck(f"{LANGUAGE}go")
        _save(page)
        page.click(f"{SHEET} button:has-text('Delete the folder…')")
        page.wait_for_selector(f"{SHEET} #removal-blocked")
        seen.delete_disabled = page.is_disabled(f"{SHEET} button.danger")
        seen.reason = _words(page.locator(f"{SHEET} #removal-blocked").inner_text())
        tied = page.get_attribute(f"{SHEET} button.danger", "aria-describedby")
        seen.reason_tied = tied == "removal-blocked"
        page.click(f"{SHEET} button:has-text('Back')")
        seen.first_step_after_back = page.evaluate("document.activeElement?.textContent")
        seen.marker_before_keep = _languages(go_workspace)
        page.click(f"{SHEET} button:has-text('Keep the folder')")
        page.wait_for_selector(SHEET, state="detached")
        seen.kept_status = _status(page, "go removed").splitlines()[0]
        seen.kept_lines = page.locator(f"{STATUS} span").all_inner_texts()
        seen.marker_after_keep = _languages(go_workspace)
        seen.folder_kept = (go_workspace / "go").is_dir()
        browser.close()
    return seen


def test_an_attempt_in_progress_disables_the_delete_with_the_clis_reason(busy):
    assert busy.delete_disabled
    assert busy.reason.startswith("cannot delete go/ and go.work: attempt ")
    assert "(two-sum, go) is in progress" in busy.reason
    assert busy.reason_tied


def test_keep_stays_available_and_removes_the_language_keeping_the_folder(busy):
    assert busy.first_step_after_back == "Keep the folder"
    assert busy.marker_before_keep == ["python", "go"]
    assert busy.marker_after_keep == ["python"]
    assert busy.folder_kept


def test_a_kept_removal_notes_the_attempt_still_running(busy):
    assert busy.kept_status.endswith("go removed: go/ and go.work stays on disk")
    assert any(
        line.startswith("note: attempt ") and "(two-sum, go) is in progress" in line
        for line in busy.kept_lines
    )


def test_the_refusal_logs_no_error_or_warning(busy):
    assert busy.errors == []
