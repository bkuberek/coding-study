"""A run's diagnostic in a real browser (docs/specs/web-ui.md#attempt-view): a syntax error saved
from the editor and run from the page marks its line in the editor, the diagnostic in the results
jumps to that line, and a run once it is fixed clears the marker, in each engine of
`tests/browsers.py`.

The workspace shares the session's practice workspace's toolchains, so the project's suite runs
with the real pytest, whose collection error `cstudy test --events` reports as a `diagnostic`.
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
BROKEN_LINE = 15
"""`def deposit(…) -> int:`, whose colon the test deletes."""
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
SAVED_TAB = "[role=tab][aria-selected=true]:not(.is-modified)"
JUMP = ".result-diagnostics .diagnostic-jump"
WAIT_MS = 60_000
RUN_WAIT_MS = 240_000
"""Generous for a run: the machine running the slow tests is often loaded."""
MARKED_LINES = """editor => [...editor.querySelectorAll(":scope > .cm-line")]
    .flatMap((line, index) => line.querySelector(".cm-lintRange-error") ? [index + 1] : [])"""
"""The 1-based numbers of the lines an error marker underlines; the file is short enough for
CodeMirror to draw every line."""
GUTTER_MARKERS = ".panel:not([hidden]) .cm-lint-marker-error"
MARKERS = f".panel:not([hidden]) .cm-lintRange, {GUTTER_MARKERS}"
CURSOR_LINE = ".panel:not([hidden]) .cm-lineNumbers .cm-activeLineGutter"
FOCUS_IN_EDITOR = "() => document.activeElement?.closest('.cm-editor') !== null"


@dataclass
class Seen:
    marked_lines: list[int] = field(default_factory=list[int])
    gutter_markers: int = 0
    jumped_to: str = ""
    focus_in_editor: bool = False
    markers_after_the_fix: int = -1
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"diagnosed-{engine}") / "workspace"
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
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        _open_the_file(page, server)
        _break_the_line(page)
        _run_until(page, "LOAD FAILED")
        page.wait_for_selector(JUMP)
        found.marked_lines = page.locator(OPEN_EDITOR).evaluate(MARKED_LINES)
        found.gutter_markers = page.locator(GUTTER_MARKERS).count()
        page.click(OPEN_EDITOR)
        page.keyboard.press("ControlOrMeta+Home")
        page.click(JUMP)
        found.jumped_to = page.locator(CURSOR_LINE).inner_text()
        found.focus_in_editor = page.evaluate(FOCUS_IN_EDITOR)
        page.keyboard.press("End")
        page.keyboard.type(":")
        _save(page)
        _run_until(page, "passed")
        found.markers_after_the_fix = page.locator(MARKERS).count()
        browser.close()
    return found


def _open_the_file(page: Any, server: RunningServer) -> None:
    page.goto(server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    page.click(f"a.slug[href='#/problems/{PROJECT}']")
    page.click("a.button.primary")
    page.click(FILE_BUTTON)
    page.wait_for_selector(OPEN_EDITOR)


def _break_the_line(page: Any) -> None:
    """Deletes the colon that ends the line, then saves the file."""
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    for _ in range(BROKEN_LINE - 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("End")
    page.keyboard.press("Backspace")
    _save(page)


def _save(page: Any) -> None:
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(SAVED_TAB)


def _run_until(page: Any, summary: str) -> None:
    """Runs the tests from the page and waits for the run's summary to say `summary`."""
    page.click(".run-button.primary")
    page.wait_for_selector(f".result-summary-text:has-text('{summary}')", timeout=RUN_WAIT_MS)


def test_a_syntax_error_marks_its_line_in_the_editor(seen):
    assert seen.marked_lines == [BROKEN_LINE]


def test_a_syntax_error_marks_its_line_in_the_gutter(seen):
    assert seen.gutter_markers == 1


def test_the_diagnostic_in_the_results_jumps_to_its_line(seen):
    assert seen.jumped_to == str(BROKEN_LINE)


def test_the_jump_moves_the_focus_to_the_editor(seen):
    assert seen.focus_in_editor


def test_a_run_after_the_fix_clears_the_marker(seen):
    assert seen.markers_after_the_fix == 0


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors == []
