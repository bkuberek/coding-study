"""Diagnostics in a real browser, in each engine of `tests/browsers.py`.

A run's diagnostic (docs/specs/web-ui.md#attempt-view): a syntax error saved from the editor and
run from the page marks its line in the editor, the diagnostic in the results jumps to that
line, and a run once it is fixed clears the marker. The workspace shares the session's practice
workspace's toolchains, so the project's suite runs with the real pytest, whose collection error
`cstudy test --events` reports as a `diagnostic`.

Live diagnostics (docs/specs/web-ui.md#live-diagnostics), against the scripted fake language
server: an error is underlined and has a gutter marker, a warning and information their own,
a hint has neither, unused code is faded and deprecated code struck through, the tooltip names
the source, the status bar counts, F8 and Shift-F8 skip hints, Cmd or Ctrl-Shift-M lists them
all, and under Vim `]d` and `[d` do what F8 and Shift-F8 do.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped."""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.preferences import Preferences
from tests.browsers import launched, watched
from tests.intelligence_lab import (
    EDITOR,
    SERVES,
    Lab,
    intelligence_lab,
    open_attempt,
    store,
    wait_for_status,
)
from tests.language_server_scripts import notification
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


TYPED = "total = 1\nlegacy = 2\nplain = 3\n"
"""Lines 6 to 8 of the starter file, which has five lines and a last empty one (6 lines)."""
PUBLISHED = [
    {
        "range": {"start": {"line": 3, "character": 4}, "end": {"line": 3, "character": 11}},
        "severity": 1,
        "source": "basedpyright",
        "code": "reportUndefinedVariable",
        "message": '"two_sum" is not defined',
    },
    {
        "range": {"start": {"line": 4, "character": 4}, "end": {"line": 4, "character": 9}},
        "severity": 2,
        "source": "basedpyright",
        "code": "reportUnreachable",
        "message": "Code is unreachable",
    },
    {
        "range": {"start": {"line": 0, "character": 3}, "end": {"line": 0, "character": 6}},
        "severity": 3,
        "source": "basedpyright",
        "message": "Docstring starts with a capital",
    },
    {
        "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 5}},
        "severity": 4,
        "tags": [1],
        "source": "basedpyright",
        "message": '"total" is not accessed',
    },
    {
        "range": {"start": {"line": 6, "character": 0}, "end": {"line": 6, "character": 6}},
        "severity": 4,
        "tags": [2],
        "source": "basedpyright",
        "message": '"legacy" is deprecated',
    },
]
FIRST_THREE = PUBLISHED[:3]
OPENED: dict[str, object] = {"await": "textDocument/didOpen"}


def publication(diagnostics: list[dict[str, Any]]) -> dict[str, object]:
    params = {"uri": "$uri", "diagnostics": diagnostics}
    return {"send": notification("textDocument/publishDiagnostics", params)}


LIVE_SCRIPT = (
    SERVES,
    OPENED,
    {"await": "textDocument/didChange"},
    publication(PUBLISHED),
)
VIM_SCRIPT = (SERVES, OPENED, publication(FIRST_THREE))
CURSOR_LINE_NUMBER = f"{EDITOR.rsplit(' ', 1)[0]} .cm-lineNumbers .cm-activeLineGutter"
PANEL_ITEMS = ".cm-panel-lint li"
SELECTED_TEXT = "() => window.getSelection()?.toString() ?? ''"
LINT_RANGE_STYLE = """selector => {
  const style = getComputedStyle(document.querySelector(selector));
  return {
    image: style.backgroundImage,
    opacity: style.opacity,
    decoration: style.textDecorationLine,
  };
}"""


@dataclass
class LiveSeen:
    status: str = ""
    underlined: dict[str, int] = field(default_factory=dict[str, int])
    gutter_markers: dict[str, int] = field(default_factory=dict[str, int])
    all_gutter_markers: int = -1
    faded: dict[str, str] = field(default_factory=dict[str, str])
    struck: dict[str, str] = field(default_factory=dict[str, str])
    hint_image: str = ""
    tooltip: str = ""
    visits: list[str] = field(default_factory=list[str])
    visits_back: list[str] = field(default_factory=list[str])
    panel_items: int = -1
    vim_lines: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def live_lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"live-{engine}")
    with intelligence_lab(practice_workspace, base, LIVE_SCRIPT) as lab:
        yield lab


@pytest.fixture(scope="module")
def live(engine: str, live_lab: Lab) -> LiveSeen:
    found = LiveSeen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(live_lab.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _typed_and_published(page, live_lab, found)
        _underlines_and_markers(page, found)
        _tooltip(page, found)
        _keys(page, found)
        _vim_keys(browser, live_lab, found)
        browser.close()
    return found


def _typed_and_published(page: Any, lab: Lab, found: LiveSeen) -> None:
    """Types three lines, which the fake server waits for before it publishes."""
    open_attempt(page, lab)
    wait_for_status(page, "python · basedpyright · ready")
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.insert_text(TYPED)
    found.status = wait_for_status(page, "python · basedpyright · ready · 1 error")


def _underlines_and_markers(page: Any, found: LiveSeen) -> None:
    panel = ".panel:not([hidden])"
    for severity in ("error", "warning", "info", "hint"):
        found.underlined[severity] = page.locator(f"{panel} .cm-lintRange-{severity}").count()
    for severity in ("error", "warning", "info"):
        found.gutter_markers[severity] = page.locator(f"{panel} .cm-lint-marker-{severity}").count()
    found.all_gutter_markers = page.locator(f"{panel} .cm-lint-marker").count()
    found.faded = page.evaluate(LINT_RANGE_STYLE, f"{panel} .cstudy-unnecessary")
    found.struck = page.evaluate(LINT_RANGE_STYLE, f"{panel} .cstudy-deprecated")
    found.hint_image = page.evaluate(LINT_RANGE_STYLE, f"{panel} .cm-lintRange-hint")["image"]


def _tooltip(page: Any, found: LiveSeen) -> None:
    page.hover(".panel:not([hidden]) .cm-lintRange-error")
    page.wait_for_selector(".cm-tooltip-lint")
    found.tooltip = page.locator(".cm-tooltip-lint").first.inner_text()
    page.mouse.move(0, 0)


def _keys(page: Any, found: LiveSeen) -> None:
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    found.visits = _visits(page, "F8", 4)
    found.visits_back = _visits(page, "Shift+F8", 4)
    page.keyboard.press("ControlOrMeta+Shift+m")
    page.wait_for_selector(PANEL_ITEMS)
    found.panel_items = page.locator(PANEL_ITEMS).count()
    page.keyboard.press("Escape")


def _visits(page: Any, key: str, times: int) -> list[str]:
    """The text each press of `key` selects. The keys fetch their code at the first press, so a
    press is answered a moment later: each waits for the selection to differ from the last."""
    visited: list[str] = []
    previous = page.evaluate(SELECTED_TEXT)
    for _ in range(times):
        page.keyboard.press(key)
        page.wait_for_function(
            "previous => (window.getSelection()?.toString() ?? '') !== previous", arg=previous
        )
        previous = page.evaluate(SELECTED_TEXT)
        visited.append(previous)
    return visited


def _vim_keys(browser: Any, lab: Lab, found: LiveSeen) -> None:
    """With Vim on, `]d` and `[d` move the cursor to the next and previous diagnostic."""
    lab.script.play(*VIM_SCRIPT)
    store(lab, Preferences(code_intelligence=True, vim=True))
    page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
    page.set_default_timeout(WAIT_MS)
    page.goto(lab.server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    open_attempt(page, lab)
    wait_for_status(page, "python · basedpyright · ready · 1 error")
    page.click(EDITOR)
    page.keyboard.press("Escape")
    page.keyboard.press("g")
    page.keyboard.press("g")
    for keys, line in ((("]", "d"), "1"), (("]", "d"), "4"), (("]", "d"), "5"), (("[", "d"), "4")):
        for key in keys:
            page.keyboard.press(key)
        page.wait_for_function(
            "([selector, line]) => document.querySelector(selector)?.textContent === line",
            arg=[CURSOR_LINE_NUMBER, line],
        )
        found.vim_lines.append(page.locator(CURSOR_LINE_NUMBER).inner_text())


def test_the_status_bar_counts_errors_warnings_and_information(live):
    assert live.status == "python · basedpyright · ready · 1 error · 1 warning · 1 info"


def test_an_error_is_underlined(live):
    assert live.underlined["error"] == 1


def test_a_warning_is_underlined(live):
    assert live.underlined["warning"] == 1


def test_information_is_underlined(live):
    assert live.underlined["info"] == 1


def test_a_hint_is_drawn_without_an_underline(live):
    assert live.hint_image == "none"


def test_each_severity_has_its_gutter_marker(live):
    assert live.gutter_markers == {"error": 1, "warning": 1, "info": 1}


def test_a_hint_has_no_gutter_marker(live):
    assert live.all_gutter_markers == 3


def test_unused_code_is_faded(live):
    assert float(live.faded["opacity"]) < 1


def test_deprecated_code_is_struck_through(live):
    assert "line-through" in live.struck["decoration"]


def test_the_tooltip_names_the_servers_source_and_code(live):
    assert "basedpyright reportUndefinedVariable" in live.tooltip


def test_f8_visits_the_diagnostics_in_order_skips_hints_and_wraps(live):
    assert live.visits == ["Two", "two_sum", "raise", "Two"]


def test_shift_f8_visits_them_backwards_and_wraps(live):
    assert live.visits_back == ["raise", "two_sum", "Two", "raise"]


def test_the_lint_panel_lists_every_diagnostic_hints_too(live):
    assert live.panel_items == 5


def test_under_vim_the_diagnostic_keys_move_the_cursor(live):
    assert live.vim_lines == ["1", "4", "5", "4"]


def test_the_page_logs_no_error_for_live_diagnostics(live):
    assert live.errors == []
