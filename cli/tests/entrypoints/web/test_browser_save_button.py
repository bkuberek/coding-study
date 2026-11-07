"""The Save button at the top right of the editor tabs (docs/specs/web-ui.md#editor), in each engine
of `tests/browsers.py`: a real button, named for the active file, that saves it through the save
the shortcut uses, disabled with nothing to save, when no file is open, and in a read-only editor.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped."""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
SAVE = "button.save-hint"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
MODIFIED_TAB = f"{ACTIVE_TAB}.is-modified"
SAVED_TAB = f"{ACTIVE_TAB}:not(.is-modified)"
BANNER = ".panel:not([hidden]) .file-banner.is-conflict"
WAIT_MS = 60_000
SHORTCUT = "() => /^Mac/.test(navigator.platform) ? '⌘S' : 'Ctrl-S'"


@dataclass
class Seen:
    disabled_with_no_file: bool = False
    disabled_with_nothing_to_save: bool = False
    enabled_with_an_edit: bool = False
    name_of_the_button: str = ""
    shortcut_shown: str = ""
    shortcut_of_the_platform: str = ""
    saved_on_disk: bool = False
    mark_after_a_click: int = -1
    disabled_after_saving: bool = False
    focus_after_saving: bool = False
    saved_by_the_keyboard: bool = False
    conflict_kept_their_file: bool = False
    conflict_banner: int = -1
    disabled_when_read_only: bool = False
    logged: list[str] = field(default_factory=list[str])
    errors_before_the_refusals: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"save-button-{engine}") / "workspace"
    )
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROJECT, "--no-open"],
        env=served_environment(root),
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return root


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path) -> Seen:
    found = Seen()
    file = workspace / "projects" / PROJECT / FILE
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.click(f"a.problem-link[href='#/problems/{PROJECT}']")
        page.click("a.button.primary")
        page.wait_for_selector(FILE_BUTTON)
        found.disabled_with_no_file = page.is_disabled(SAVE)
        page.click(FILE_BUTTON)
        page.wait_for_selector(f"{OPEN_EDITOR} .cm-line span")
        found.disabled_with_nothing_to_save = page.is_disabled(SAVE)
        _edit(page, "# saved by a click\n")
        found.enabled_with_an_edit = page.is_enabled(SAVE)
        found.name_of_the_button = page.get_attribute(SAVE, "aria-label") or ""
        found.shortcut_shown = page.locator(f"{SAVE} kbd").inner_text()
        found.shortcut_of_the_platform = page.evaluate(SHORTCUT)
        page.click(SAVE)
        page.wait_for_selector(SAVED_TAB)
        found.saved_on_disk = "# saved by a click" in file.read_text()
        found.mark_after_a_click = page.locator(MODIFIED_TAB).count()
        found.disabled_after_saving = page.is_disabled(SAVE)
        found.focus_after_saving = page.evaluate(
            "() => document.activeElement?.closest('.cm-editor') !== null"
        )
        _edit(page, "# saved by the keyboard\n")
        page.focus(SAVE)
        page.keyboard.press("Enter")
        page.wait_for_selector(SAVED_TAB)
        found.saved_by_the_keyboard = "# saved by the keyboard" in file.read_text()
        found.errors_before_the_refusals = list(found.logged)
        _a_conflict_stays_with_its_banner(page, file, found)
        _read_only_after_the_attempt_ended(page, found)
        browser.close()
    return found


def _edit(page: Any, text: str) -> None:
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type(text)
    page.wait_for_selector(MODIFIED_TAB)


def _a_conflict_stays_with_its_banner(page: Any, file: Path, found: Seen) -> None:
    """The browser logs the 412 of this save, as the 409 once the attempt ended."""
    _edit(page, "# mine\n")
    theirs = file.read_text() + "# theirs\n"
    file.write_text(theirs)
    page.wait_for_selector(BANNER)
    page.click(SAVE)
    page.wait_for_selector(f"{BANNER} button:focus")
    found.conflict_kept_their_file = file.read_text() == theirs
    found.conflict_banner = page.locator(BANNER).count()
    page.click(f"{BANNER} button:has-text('Reload theirs')")
    page.wait_for_selector(BANNER, state="hidden")


def _read_only_after_the_attempt_ended(page: Any, found: Seen) -> None:
    _edit(page, "# left unsaved\n")
    page.evaluate(
        """async (csrf) => {
          const attempt = location.hash.split("/").pop();
          await fetch(`/api/v1/attempts/${attempt}/done`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Cstudy-CSRF": csrf },
            body: JSON.stringify({ gave_up: true }),
          });
        }""",
        page.get_attribute("meta[name=cstudy-csrf]", "content"),
    )
    page.wait_for_selector(f"{SAVE}:disabled")
    found.disabled_when_read_only = page.is_disabled(SAVE)


def test_it_is_disabled_with_no_file_open(seen):
    assert seen.disabled_with_no_file


def test_it_is_disabled_with_nothing_to_save(seen):
    assert seen.disabled_with_nothing_to_save


def test_an_edit_enables_it(seen):
    assert seen.enabled_with_an_edit


def test_it_is_named_for_the_active_file(seen):
    assert seen.name_of_the_button == "Save bank.py"


def test_it_shows_the_shortcut_of_the_platform(seen):
    assert seen.shortcut_shown == seen.shortcut_of_the_platform


def test_a_click_writes_the_file_on_disk(seen):
    assert seen.saved_on_disk


def test_a_click_clears_the_unsaved_mark(seen):
    assert seen.mark_after_a_click == 0


def test_it_is_disabled_again_after_saving(seen):
    assert seen.disabled_after_saving


def test_the_focus_returns_to_the_editor_after_saving(seen):
    assert seen.focus_after_saving


def test_the_keyboard_reaches_and_presses_it(seen):
    assert seen.saved_by_the_keyboard


def test_a_conflict_writes_nothing_over_the_file_on_disk(seen):
    assert seen.conflict_kept_their_file


def test_a_conflict_keeps_its_banner(seen):
    assert seen.conflict_banner == 1


def test_it_is_disabled_once_the_editor_is_read_only(seen):
    assert seen.disabled_when_read_only


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors_before_the_refusals == []
