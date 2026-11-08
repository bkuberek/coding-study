"""The page with the keyboard alone (docs/specs/web-ui.md#keyboard-and-accessibility), in each
engine of `tests/browsers.py`: the skip link, a view's shortcut, a visible focus on every stop,
a stop the status bar covers coming out from under it once it has the focus, a dialog that keeps
the focus, closes on Escape and gives the focus back, the file tree's menu,
the editor's name and the way out of it, Alt-Shift-click adding a cursor while Cmd-click and
Ctrl-click do not and Alt-drag still selects a rectangle, the live region that announces a run's
start and summary, and Escape in the results panel cancelling a run after its question.

WebKit moves the focus to links and buttons with Option-Tab, as Safari does unless its setting
"Press Tab to highlight each item" is on, so the steps press Alt+Tab there.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
EDITOR = ".panel:not([hidden]) .cm-content"
DIALOG = "dialog[open]"
START = ".practice-actions button.primary"
WAIT_MS = 60_000
RUN_WAIT_MS = 240_000
"""Generous for a run: the machine running the slow tests is often loaded."""
TAB_STOPS = 20
SHORT_WINDOW = 600
"""Short enough that the problem list runs on under the status bar, however few problems it has."""
FIRST_STOP_UNDER_THE_BAR = """() => {
    const bar = document.querySelector(".statusbar").getBoundingClientRect().top;
    const stops = [...document.querySelectorAll("table.problems tbody :is(a, button)")];
    const covered = stops.findIndex((stop) => stop.getBoundingClientRect().bottom > bar);
    if (covered < 1) return false;
    stops[covered - 1].focus();
    return true;
}"""
"""Focuses the stop before the first one the status bar covers; false when the bar covers none."""
UNDER_THE_BAR = """() => Math.max(0,
    Math.floor(document.activeElement.getBoundingClientRect().bottom)
    - document.querySelector(".statusbar").getBoundingClientRect().top)"""
"""How many pixels of the focused element the status bar covers, to the pixel a scroll rounds to."""
CLICK_INDENT = 40
"""Pixels from a line's left edge: inside the text of a starter file's first lines."""
DIALOG_TABS = 12
SLOW_TEST = "tests/test_slow.py"
SLOW_TEST_TEXT = "import time\n\n\ndef test_slow():\n    time.sleep(120)\n"
FOCUS = """() => {
    const element = document.activeElement;
    if (!element || element === document.body) return null;
    const style = getComputedStyle(element);
    const outlined = style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0;
    return {
        name: (element.getAttribute("aria-label") || element.textContent || "").trim(),
        id: element.id,
        role: element.getAttribute("role") || element.tagName.toLowerCase(),
        visible: outlined || style.boxShadow !== "none",
        inDialog: element.closest("dialog[open]") !== null,
        inEditor: element.closest(".cm-editor") !== null,
        path: element.dataset.path ?? null,
    };
}"""
"""What has the focus, and whether an outline or a ring shows it."""
TWO_FRAMES = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
"""The editor draws its cursors in a measure step after the event: a count waits two frames."""
ANNOUNCED = "() => document.querySelector('.sr-only[aria-live=polite]').textContent"


@dataclass
class Keys:
    first_stop: str = ""
    after_skip: str = ""
    view_by_shortcut: str = ""
    stops_without_focus_ring: list[str] = field(default_factory=list[str])
    focus_under_the_status_bar: int | None = None
    dialog_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    focus_outside_dialog: list[str] = field(default_factory=list[str])
    dialogs_after_escape: int = -1
    focus_after_dialog: str = ""
    menu_focus: str = ""
    focus_after_menu: str = ""
    editor_name: str = ""
    left_editor: bool = False
    cursors_after_plain_click: int = 0
    cursors_after_alt_shift_click: int = 0
    cursors_after_meta_click: int = 0
    cursors_after_control_click: int = 0
    cursors_after_alt_drag: int = 0
    announced_start: str = ""
    announced_end: str = ""
    cancel_question: str = ""
    cancelled: str = ""


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp(f"keys-{engine}") / "ws")
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
def keys(engine: str, server: RunningServer, workspace: Path) -> Keys:
    found = Keys()
    tab = "Alt+Tab" if engine == "webkit" else "Tab"
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _skip_and_shortcut(page, tab, found)
        _focus_rings(page, tab, found)
        _focus_under_the_status_bar(page, tab, found)
        _dialog(page, tab, found)
        _tree_and_editor(page, tab, found)
        _clicks(page, found)
        _announcements(page, found)
        _escape_cancels(page, workspace / "projects" / PROJECT / SLOW_TEST, found)
        browser.close()
    return found


def _skip_and_shortcut(page: Any, tab: str, found: Keys) -> None:
    page.keyboard.press(tab)
    found.first_stop = _focus(page)["name"]
    page.keyboard.press("Enter")
    found.after_skip = _focus(page)["id"]
    page.keyboard.press("Alt+4")
    page.wait_for_function("() => location.hash === '#/progress'")
    found.view_by_shortcut = page.evaluate("location.hash")


def _focus_rings(page: Any, tab: str, found: Keys) -> None:
    page.evaluate("location.hash = '#/'")
    page.wait_for_selector("table.problems tbody tr")
    page.focus("body")
    for _ in range(TAB_STOPS):
        page.keyboard.press(tab)
        focus = page.evaluate(FOCUS)
        if focus is not None and not focus["visible"]:
            found.stops_without_focus_ring.append(f"{focus['role']} {focus['name'][:30]}")


def _focus_under_the_status_bar(page: Any, tab: str, found: Keys) -> None:
    """Tabs from the stop above the status bar to the first stop it covers."""
    page.set_viewport_size({"width": 1440, "height": SHORT_WINDOW})
    page.evaluate("window.scrollTo(0, 0)")
    if page.evaluate(FIRST_STOP_UNDER_THE_BAR):
        page.keyboard.press(tab)
        found.focus_under_the_status_bar = page.evaluate(UNDER_THE_BAR)
    page.set_viewport_size({"width": 1440, "height": 900})


def _dialog(page: Any, tab: str, found: Keys) -> None:
    page.evaluate("location.hash = '#/problems/two-sum'")
    page.focus(START)
    page.keyboard.press("Enter")
    page.wait_for_selector(DIALOG)
    found.dialog_focus = _focus(page)
    for _ in range(DIALOG_TABS):
        page.keyboard.press(tab)
        focus = page.evaluate(FOCUS)
        if focus is not None and not focus["inDialog"]:
            found.focus_outside_dialog.append(f"{focus['role']} {focus['name'][:30]}")
    page.keyboard.press("Escape")
    page.wait_for_selector(DIALOG, state="detached")
    found.dialogs_after_escape = page.locator(DIALOG).count()
    found.focus_after_dialog = _focus(page)["name"]


def _tree_and_editor(page: Any, tab: str, found: Keys) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROJECT}'")
    page.click("a.button.primary")
    page.focus(FILE_BUTTON)
    page.keyboard.press("Shift+F10")
    page.wait_for_selector(".tree-menu [role=menuitem]")
    found.menu_focus = _focus(page)["role"]
    page.keyboard.press("Escape")
    found.focus_after_menu = _focus(page)["path"] or ""
    page.keyboard.press("Enter")
    page.wait_for_selector(EDITOR)
    page.focus(EDITOR)
    found.editor_name = _focus(page)["name"]
    page.keyboard.press("Escape")
    page.keyboard.press(tab)
    found.left_editor = not _focus(page)["inEditor"]


def _clicks(page: Any, found: Keys) -> None:
    lines = page.locator(f"{EDITOR} .cm-line")
    first, third = lines.nth(0).bounding_box(), lines.nth(2).bounding_box()
    assert first is not None
    assert third is not None
    at_first = (first["x"] + CLICK_INDENT, first["y"] + first["height"] / 2)
    at_third = (third["x"] + CLICK_INDENT, third["y"] + third["height"] / 2)
    _click(page, at_first)
    found.cursors_after_plain_click = _cursors(page)
    for modifier, name in (
        ("Alt+Shift", "cursors_after_alt_shift_click"),
        ("Meta", "cursors_after_meta_click"),
        ("Control", "cursors_after_control_click"),
    ):
        _click(page, at_first)
        _click(page, at_third, *modifier.split("+"))
        setattr(found, name, _cursors(page))
    _click(page, at_first)
    page.keyboard.down("Alt")
    page.mouse.move(*at_first)
    page.mouse.down()
    page.mouse.move(*at_third, steps=4)
    page.mouse.up()
    page.keyboard.up("Alt")
    found.cursors_after_alt_drag = _cursors(page)
    _click(page, at_first)


def _click(page: Any, at: tuple[float, float], *held: str) -> None:
    for key in held:
        page.keyboard.down(key)
    page.mouse.click(*at)
    for key in reversed(held):
        page.keyboard.up(key)


def _cursors(page: Any) -> int:
    page.evaluate(TWO_FRAMES)
    return page.locator(".panel:not([hidden]) .cm-cursor").count()


def _announcements(page: Any, found: Keys) -> None:
    page.focus(FILE_BUTTON)
    page.keyboard.press("ControlOrMeta+Enter")
    page.wait_for_function(f"() => ({ANNOUNCED})().startsWith('running ')")
    found.announced_start = page.evaluate(ANNOUNCED)
    page.wait_for_function(f"() => ({ANNOUNCED})().startsWith('run ended')", timeout=RUN_WAIT_MS)
    found.announced_end = page.evaluate(ANNOUNCED)


def _escape_cancels(page: Any, slow_test: Path, found: Keys) -> None:
    slow_test.write_text(SLOW_TEST_TEXT)
    try:
        page.wait_for_selector(".run-button.primary:not([disabled])")
        page.focus(FILE_BUTTON)
        page.keyboard.press("ControlOrMeta+Enter")
        page.wait_for_selector(".result-running:has-text('test_slow')", timeout=RUN_WAIT_MS)
        page.focus(".results-body")
        page.keyboard.press("Escape")
        found.cancel_question = page.wait_for_selector(f"{DIALOG} .question").inner_text()
        page.click(f"{DIALOG} button.danger")
        summary = page.wait_for_selector(".result-summary-text", timeout=RUN_WAIT_MS)
        found.cancelled = summary.inner_text()
    finally:
        slow_test.unlink(missing_ok=True)


def _focus(page: Any) -> dict[str, Any]:
    return page.evaluate(FOCUS) or {"name": "", "id": "", "role": "", "path": None}


def test_the_first_tab_reaches_the_skip_link(keys):
    assert keys.first_stop == "Skip to content"


def test_the_skip_link_moves_the_focus_to_the_view(keys):
    assert keys.after_skip == "main"


def test_alt_and_a_digit_open_a_view(keys):
    assert keys.view_by_shortcut == "#/progress"


def test_every_stop_shows_the_focus(keys):
    assert keys.stops_without_focus_ring == []


def test_a_stop_the_status_bar_covers_comes_out_from_under_it_with_the_focus(keys):
    assert keys.focus_under_the_status_bar == 0


def test_a_dialog_opened_by_the_keyboard_takes_the_focus(keys):
    assert keys.dialog_focus.get("inDialog") is True


def test_tab_keeps_the_focus_in_the_dialog(keys):
    assert keys.focus_outside_dialog == []


def test_escape_closes_the_dialog(keys):
    assert keys.dialogs_after_escape == 0


def test_a_closed_dialog_gives_the_focus_back_to_its_button(keys):
    assert keys.focus_after_dialog == "Start…"


def test_the_files_menu_opens_on_its_first_item(keys):
    assert keys.menu_focus == "menuitem"


def test_escape_closes_the_menu_and_gives_the_focus_back_to_the_file(keys):
    assert keys.focus_after_menu == FILE


def test_the_editor_is_named_after_its_file(keys):
    assert keys.editor_name == FILE


def test_escape_then_tab_leaves_the_editor(keys):
    assert keys.left_editor


def test_a_click_places_one_cursor(keys):
    assert keys.cursors_after_plain_click == 1


def test_alt_shift_click_adds_a_cursor(keys):
    assert keys.cursors_after_alt_shift_click == 2


def test_cmd_click_is_a_plain_click(keys):
    assert keys.cursors_after_meta_click == 1


def test_ctrl_click_is_a_plain_click(keys):
    assert keys.cursors_after_control_click == 1


def test_alt_drag_selects_a_rectangle(keys):
    assert keys.cursors_after_alt_drag == 3


def test_a_screen_reader_hears_a_run_start(keys):
    assert keys.announced_start == f"running cstudy test {PROJECT}; the same button now cancels it"


def test_a_screen_reader_hears_a_run_summary(keys):
    assert keys.announced_end.startswith("run ended: 0/2 passed · 2 errors · total ")


def test_escape_in_the_results_asks_before_cancelling_a_run(keys):
    assert keys.cancel_question == "cstudy stops it as Ctrl-C does and records nothing."


def test_escape_in_the_results_cancels_the_run_once_confirmed(keys):
    assert keys.cancelled == "interrupted"
