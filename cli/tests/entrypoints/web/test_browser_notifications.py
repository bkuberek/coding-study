"""Changes from elsewhere in a real browser (docs/specs/web-ui.md#attempt-view): a file edited on
disk while its tab has no unsaved edits shows the new version in place and keeps the cursor; edited
again while the tab has unsaved edits, it shows the conflict banner and keeps them; a second tab of
the same attempt takes a save of the first and shows the run the first started.

Playwright is in the optional `browser` dependency group (`uv sync --group browser`, then
`uv run --group browser playwright install chromium`); without either the test is skipped."""

import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
CONFLICT = ".panel:not([hidden]) .file-banner.is-conflict:not([hidden])"
THIRD_LINE = "from bank.models import Account"
TYPED = "Z"
SAVED_IN_FIRST_TAB = "# saved in the first tab"
WAIT_MS = 60_000
EDIT_RETRY_MS = 3_000
"""How long one edit on disk waits to show before the next, while the server's watch starts."""
RUN_WAIT_MS = 240_000
"""Generous for a run: the machine running the slow tests is often loaded."""
EDITOR_HAS = f"text => document.querySelector('{OPEN_EDITOR}')?.innerText.includes(text)"
"""Whether the open editor shows `text`."""


@dataclass
class Seen:
    reloaded: bool = False
    reloaded_unsaved: int = -1
    typed_line: str = ""
    conflict: bool = False
    edits_kept: bool = False
    second_tab_reloaded: bool = False
    second_tab_summary: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("notified") / "workspace")
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
def seen(server: RunningServer, workspace: Path) -> Seen:
    found = Seen()
    edited = workspace / "projects" / PROJECT / FILE
    original = edited.read_text()
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as error:
            pytest.skip(f"no Chromium for Playwright: {error.message.splitlines()[0]}")
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        first = _opened(context, server, found)
        attempt = first.evaluate("location.hash")
        _cursor_on_the_third_line(first)
        found.reloaded = _edit_until_shown(first, edited, original)
        found.reloaded_unsaved = first.locator("[role=tab].is-modified").count()
        first.keyboard.type(TYPED)
        found.typed_line = _line_with(first, THIRD_LINE)
        _replace(edited, f"# edited again on disk\n{original}")
        first.wait_for_selector(CONFLICT)
        found.conflict = True
        found.edits_kept = TYPED + THIRD_LINE in first.locator(OPEN_EDITOR).inner_text()
        first.click(f"{CONFLICT} button:has-text('Reload theirs')")
        first.wait_for_selector(CONFLICT, state="detached")
        second = context.new_page()
        _watch_console(second, found)
        second.set_default_timeout(WAIT_MS)
        second.goto(f"{server.address}/{attempt}")
        second.click(FILE_BUTTON)
        second.wait_for_selector(OPEN_EDITOR)
        _save_at_the_end(first)
        second.wait_for_function(EDITOR_HAS, arg=SAVED_IN_FIRST_TAB)
        found.second_tab_reloaded = True
        first.click(".run-button.primary")
        summary = second.wait_for_selector(".result-summary-text", timeout=RUN_WAIT_MS)
        found.second_tab_summary = summary.inner_text()
        browser.close()
    return found


def _opened(context: Any, server: RunningServer, found: Seen) -> Any:
    """A tab logged in, on the project's attempt, with the file open in the editor."""
    page = context.new_page()
    page.set_default_timeout(WAIT_MS)
    _watch_console(page, found)
    page.goto(server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    page.click(f"a.slug[href='#/problems/{PROJECT}']")
    page.click("a.button.primary")
    page.click(FILE_BUTTON)
    page.wait_for_selector(OPEN_EDITOR)
    return page


def _cursor_on_the_third_line(page: Any) -> None:
    """At the start of the third line; the arrows keep the column the click gave, Home drops it."""
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Home")


def _edit_until_shown(page: Any, edited: Path, original: str) -> bool:
    """Writes a new first line until the editor shows it, since the server's watch may still be
    starting; whether it did before the deadline."""
    deadline = time.monotonic() + WAIT_MS / 1000
    edit = 0
    while time.monotonic() < deadline:
        edit += 1
        marker = f"# edited on disk {edit}"
        _replace(edited, f"{marker}\n{original}")
        try:
            page.wait_for_function(EDITOR_HAS, arg=marker, timeout=EDIT_RETRY_MS)
        except sync_api.TimeoutError:
            continue
        return True
    return False


def _replace(edited: Path, text: str) -> None:
    """Writes `text` over the file at once, as editors save: a new file renamed over it, so no
    half-written file is ever read. The new file is made in the workspace's root, where the server
    watches only the progress database."""
    written = edited.parents[3] / f"{edited.name}.saved"
    written.write_text(text)
    written.replace(edited)


def _line_with(page: Any, text: str) -> str:
    lines = page.locator(f"{OPEN_EDITOR} .cm-line").all_inner_texts()
    return next((line for line in lines if text in line), "")


def _save_at_the_end(page: Any) -> None:
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type(f"\n{SAVED_IN_FIRST_TAB}\n")
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector("[role=tab][aria-selected=true]:not(.is-modified)")


def _watch_console(page: Any, found: Seen) -> None:
    page.on("console", lambda message: _console(found, message))
    page.on("pageerror", lambda error: found.errors.append(str(error)))


def _console(found: Seen, message: Any) -> None:
    if message.type in ("error", "warning"):
        found.errors.append(f"{message.type}: {message.text}")


def test_a_file_edited_on_disk_shows_in_its_tab(seen):
    assert seen.reloaded


def test_a_tab_that_took_the_version_on_disk_has_no_unsaved_edits(seen):
    assert seen.reloaded_unsaved == 0


def test_a_tab_that_took_the_version_on_disk_keeps_the_cursor(seen):
    assert seen.typed_line == TYPED + THIRD_LINE


def test_a_file_edited_on_disk_under_unsaved_edits_shows_the_conflict_banner(seen):
    assert seen.conflict


def test_the_conflict_banner_keeps_the_unsaved_edits(seen):
    assert seen.edits_kept


def test_a_second_tab_takes_a_save_of_the_first(seen):
    assert seen.second_tab_reloaded


def test_a_second_tab_shows_the_run_the_first_started(seen):
    assert seen.second_tab_summary.startswith("0/2 passed")


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors == []
