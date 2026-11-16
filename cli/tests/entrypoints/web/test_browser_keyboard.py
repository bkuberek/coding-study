"""The page with the keyboard alone (docs/specs/web-ui.md#keyboard-and-accessibility), in each
engine of `tests/browsers.py`: the skip link, a view's shortcut, a visible focus on every stop,
a stop the status bar covers coming out from under it once it has the focus, a dialog that keeps
the focus, closes on Escape and gives the focus back, the file tree's menu,
the editor's name and the way out of it, Alt-Shift-click adding a cursor while Cmd-click and
Ctrl-click do not and Alt-drag still selects a rectangle, the live region that announces a run's
start and summary, and Escape in the results panel cancelling a run after its question.

The learner profile's controls, on a workspace with a profile: the profile chip of the Problems,
Guides and Mock views reached by Tab with a visible focus, Enter and Space widening with the focus
on its neighbor, `edit profile` after it landing on the Profile heading of Settings, the checkbox
groups operated with Space and Tab, the last language's note read through `aria-describedby`, and
the removal dialog: Keep the folder has the focus, Tab stays inside, Escape cancels and gives the
focus back to Save, the delete's second confirmation is reached with Tab and Enter, and a refused
delete is disabled with its reason tied to it.

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

from coding_study.domain.problem import Language
from tests.browsers import launched
from tests.profile_workspace import profiled_workspace, with_attempt_in_progress
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
    page.keyboard.press("Alt+5")
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


PROFILE_TABS = 14
CHIP = "chip-profile"
SEARCH = "#filter-search"
COMMAND = ".command-text"
MOCK_COMMAND = "form.mock-form .cmd"
SAVE = ".settings-bar button[type=submit]"
RESET = ".settings-bar button:has-text('Reset')"
STATUS = ".settings-bar p[role=status]"
SHEET = "dialog.sheet[open]"
ROLE = "#config-profile-job_roles"
LANGUAGE = "#profile-lang-"
SLUG = "two-sum"
SHOWN_ALL = "cstudy list --widen all"
LISTED = ".listing:not([aria-busy]) table.problems tbody tr"
GUIDES = "ul.guide-list > li, ul.path-cards > li"


@dataclass
class ProfileKeys:
    """What the keyboard did to the profile's controls, view by view."""

    problems_chip: dict[str, Any] = field(default_factory=dict[str, Any])
    problems_next_stop: dict[str, Any] = field(default_factory=dict[str, Any])
    enter_command: str = ""
    enter_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    enter_chip_count: int = -1
    space_command: str = ""
    space_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    edit_hash: str = ""
    edit_focus: str = ""
    guides_chip: dict[str, Any] = field(default_factory=dict[str, Any])
    guides_command: str = ""
    guides_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    mock_chip: dict[str, Any] = field(default_factory=dict[str, Any])
    mock_command: str = ""
    mock_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    first_role: dict[str, Any] = field(default_factory=dict[str, Any])
    roles_before: list[bool] = field(default_factory=list[bool])
    roles_after_space: list[bool] = field(default_factory=list[bool])
    second_role_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    changes_after_toggles: str = ""
    python_disabled: bool = False
    python_described_by: str = ""
    python_note: str = ""
    save_dialog: dict[str, Any] = field(default_factory=dict[str, Any])
    dialog_title: str = ""
    focus_outside_removal: list[str] = field(default_factory=list[str])
    escape_dialogs: int = -1
    escape_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    escape_status: str = ""
    delete_stop: dict[str, Any] = field(default_factory=dict[str, Any])
    second_step_focus: dict[str, Any] = field(default_factory=dict[str, Any])
    confirm_stop: dict[str, Any] = field(default_factory=dict[str, Any])
    confirm_enabled: bool = False
    back_stop: dict[str, Any] = field(default_factory=dict[str, Any])
    first_step_again: dict[str, Any] = field(default_factory=dict[str, Any])
    refused_delete_disabled: bool = False
    refused_reason: str = ""
    refused_described_by: str = ""
    refused_back: dict[str, Any] = field(default_factory=dict[str, Any])
    refused_stops: list[str] = field(default_factory=list[str])
    refused_escape_dialogs: int = -1


@pytest.fixture(scope="module")
def profile_server(
    engine: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[RunningServer]:
    workspace = profiled_workspace(tmp_path_factory.mktemp(f"keys-profile-{engine}"))
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def refused_server(
    engine: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[RunningServer]:
    base = profiled_workspace(tmp_path_factory.mktemp(f"keys-refused-{engine}"))
    with running_server(with_attempt_in_progress(base, SLUG, Language.GO)) as running:
        yield running


def _press_tab_to(page: Any, tab: str, wanted: str, limit: int = PROFILE_TABS) -> None:
    """Tabs until the element with the id `wanted` has the focus; fails after `limit` stops."""
    for _ in range(limit):
        page.keyboard.press(tab)
        if page.evaluate("document.activeElement?.id") == wanted:
            return
    raise AssertionError(f"Tab did not reach #{wanted} in {limit} stops")


def _command_is(page: Any, command: str, where: str = COMMAND) -> None:
    page.wait_for_function(
        "([where, expected]) => document.querySelector(where)?.textContent === expected",
        arg=[where, command],
    )


def _on_the_chip(page: Any, tab: str, route: str, ready: str, start: str) -> dict[str, Any]:
    """Opens `route`, puts the focus on `start` and Tabs to the profile chip."""
    page.evaluate("route => { location.hash = route }", route)
    page.wait_for_selector(ready)
    page.wait_for_selector(f"#{CHIP}")
    page.focus(start)
    _press_tab_to(page, tab, CHIP)
    return _focus(page)


def _chips_by_the_keyboard(page: Any, tab: str, shift_tab: str, found: ProfileKeys) -> None:
    found.problems_chip = _on_the_chip(page, tab, "#/", LISTED, SEARCH)
    page.keyboard.press(tab)
    found.problems_next_stop = _focus(page)
    page.keyboard.press(shift_tab)
    page.keyboard.press("Enter")
    _command_is(page, SHOWN_ALL)
    found.enter_command = page.locator(COMMAND).inner_text()
    found.enter_focus = _focus(page)
    found.enter_chip_count = page.locator(f"#{CHIP}").count()
    # Space does what Enter does, from a fresh route with the profile back.
    page.evaluate("location.hash = '#/'")
    page.wait_for_selector(f"#{CHIP}")
    page.focus(f"#{CHIP}")
    page.keyboard.press("Space")
    _command_is(page, SHOWN_ALL)
    found.space_command = page.locator(COMMAND).inner_text()
    found.space_focus = _focus(page)
    # `edit profile` follows the chip and lands on the Profile heading.
    page.evaluate("location.hash = '#/'")
    page.wait_for_selector(f"#{CHIP}")
    page.focus(f"#{CHIP}")
    page.keyboard.press(tab)
    page.keyboard.press("Enter")
    page.wait_for_selector("#profile-heading:focus")
    found.edit_hash = page.evaluate("location.hash")
    found.edit_focus = page.evaluate("document.activeElement?.id")
    found.guides_chip = _on_the_chip(page, tab, "#/guides", GUIDES, SEARCH)
    page.keyboard.press("Enter")
    _command_is(page, "cstudy learn --widen all")
    found.guides_command = page.locator(COMMAND).inner_text()
    found.guides_focus = _focus(page)
    found.mock_chip = _on_the_chip(page, tab, "#/mock", "form.mock-form", "main")
    page.keyboard.press("Space")
    _command_is(page, "cstudy mock --widen all", MOCK_COMMAND)
    found.mock_command = page.locator(MOCK_COMMAND).inner_text()
    found.mock_focus = _focus(page)


def _checkbox_groups(page: Any, tab: str, found: ProfileKeys) -> None:
    page.evaluate("location.hash = '#/settings/profile'")
    page.wait_for_selector("#profile-heading:focus")
    roles = page.locator(f"{ROLE} input[type=checkbox]")
    first, second = roles.nth(0), roles.nth(1)
    first.focus()
    found.first_role = _focus(page)
    found.roles_before = [first.is_checked(), second.is_checked()]
    page.keyboard.press("Space")
    page.keyboard.press(tab)
    found.second_role_focus = _focus(page)
    page.keyboard.press("Space")
    found.roles_after_space = [first.is_checked(), second.is_checked()]
    found.changes_after_toggles = page.locator(".settings-count").inner_text()
    page.click(RESET)
    page.wait_for_selector(f"{ROLE}-backend:checked")
    # Unchecking go leaves python the last language: disabled, its note tied to it.
    page.focus(f"{LANGUAGE}go")
    page.keyboard.press("Space")
    found.python_disabled = page.is_disabled(f"{LANGUAGE}python")
    found.python_described_by = page.get_attribute(f"{LANGUAGE}python", "aria-describedby") or ""
    note = page.locator(f"#{found.python_described_by}") if found.python_described_by else None
    found.python_note = note.inner_text() if note else ""


def _removal_dialog(page: Any, tab: str, shift_tab: str, found: ProfileKeys) -> None:
    page.focus(SAVE)
    page.keyboard.press("Enter")
    page.wait_for_selector(SHEET)
    found.save_dialog = _focus(page)
    found.dialog_title = page.locator(f"{SHEET} h2").inner_text()
    for _ in range(DIALOG_TABS):
        page.keyboard.press(tab)
        focus = page.evaluate(FOCUS)
        if focus is not None and not focus["inDialog"]:
            found.focus_outside_removal.append(f"{focus['role']} {focus['name'][:30]}")
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    page.wait_for_selector(f"{STATUS}:has-text('not saved')")
    found.escape_dialogs = page.locator(SHEET).count()
    found.escape_focus = _focus(page)
    found.escape_status = page.locator(STATUS).inner_text()
    # The second confirmation: Delete the folder, then Back, then the delete itself.
    page.keyboard.press("Enter")
    page.wait_for_selector(SHEET)
    page.keyboard.press(shift_tab)
    found.delete_stop = _focus(page)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{SHEET} .removal-goes")
    found.second_step_focus = _focus(page)
    page.keyboard.press(tab)
    found.confirm_stop = _focus(page)
    found.confirm_enabled = page.is_enabled(f"{SHEET} button.danger")
    page.keyboard.press(shift_tab)
    found.back_stop = _focus(page)
    page.keyboard.press("Enter")
    found.first_step_again = _focus(page)
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    page.click(RESET)


def _refused_removal(page: Any, tab: str, shift_tab: str, found: ProfileKeys) -> None:
    page.evaluate("location.hash = '#/settings/profile'")
    page.wait_for_selector(f"{LANGUAGE}go")
    page.focus(f"{LANGUAGE}go")
    page.keyboard.press("Space")
    page.focus(SAVE)
    page.keyboard.press("Enter")
    page.wait_for_selector(SHEET)
    page.keyboard.press(shift_tab)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{SHEET} #removal-blocked")
    found.refused_delete_disabled = page.is_disabled(f"{SHEET} button.danger")
    found.refused_reason = " ".join(page.locator(f"{SHEET} #removal-blocked").inner_text().split())
    found.refused_described_by = (
        page.get_attribute(f"{SHEET} button.danger", "aria-describedby") or ""
    )
    found.refused_back = _focus(page)
    for _ in range(3):
        page.keyboard.press(tab)
        found.refused_stops.append(_focus(page)["name"])
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    found.refused_escape_dialogs = page.locator(SHEET).count()


@pytest.fixture(scope="module")
def profile_keys(
    engine: str, profile_server: RunningServer, refused_server: RunningServer
) -> ProfileKeys:
    found = ProfileKeys()
    tab = "Alt+Tab" if engine == "webkit" else "Tab"
    shift_tab = "Alt+Shift+Tab" if engine == "webkit" else "Shift+Tab"
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.goto(profile_server.login_url)
        page.wait_for_selector(LISTED)
        _chips_by_the_keyboard(page, tab, shift_tab, found)
        _checkbox_groups(page, tab, found)
        _removal_dialog(page, tab, shift_tab, found)
        page.goto(refused_server.login_url)
        page.wait_for_selector(LISTED)
        _refused_removal(page, tab, shift_tab, found)
        browser.close()
    return found


def test_tab_reaches_the_profile_chip_with_a_visible_focus_and_its_name(profile_keys):
    for chip in (profile_keys.problems_chip, profile_keys.guides_chip, profile_keys.mock_chip):
        assert chip["id"] == CHIP
        assert chip["visible"]
        assert chip["name"].startswith("Show all ")


def test_edit_profile_is_the_next_stop_after_the_chip_with_a_visible_focus(profile_keys):
    assert profile_keys.problems_next_stop["name"] == "edit profile"
    assert profile_keys.problems_next_stop["visible"]


def test_enter_on_the_chip_widens_and_the_focus_goes_to_its_neighbor(profile_keys):
    assert profile_keys.enter_command == SHOWN_ALL
    assert profile_keys.enter_focus["id"] == "chip-widen-lang"
    assert profile_keys.enter_focus["visible"]
    assert profile_keys.enter_chip_count == 0


def test_space_on_the_chip_widens_too(profile_keys):
    assert profile_keys.space_command == SHOWN_ALL
    assert profile_keys.space_focus["id"] == "chip-widen-lang"


def test_edit_profile_by_the_keyboard_lands_on_the_profile_heading(profile_keys):
    assert profile_keys.edit_hash == "#/settings/profile"
    assert profile_keys.edit_focus == "profile-heading"


def test_the_guides_and_mock_chips_widen_by_the_keyboard_with_the_focus_on_a_neighbor(
    profile_keys,
):
    assert profile_keys.guides_command == "cstudy learn --widen all"
    assert profile_keys.mock_command == "cstudy mock --widen all"
    for focus in (profile_keys.guides_focus, profile_keys.mock_focus):
        assert focus["id"].startswith("chip-widen-")
        assert focus["visible"]


def test_a_checkbox_group_is_operated_with_space_and_tab(profile_keys):
    assert profile_keys.first_role["role"] == "input"
    assert profile_keys.first_role["visible"]
    assert profile_keys.second_role_focus["role"] == "input"
    assert profile_keys.second_role_focus["visible"]
    assert profile_keys.roles_after_space == [not state for state in profile_keys.roles_before]
    assert profile_keys.changes_after_toggles == "1 change"


def test_the_last_language_is_disabled_and_its_note_is_tied_to_it(profile_keys):
    assert profile_keys.python_disabled
    assert profile_keys.python_note == "a workspace needs at least one language"


def test_a_save_that_removes_a_language_opens_a_dialog_with_the_focus_on_keep(profile_keys):
    assert profile_keys.dialog_title == "Remove go from this workspace"
    assert profile_keys.save_dialog["name"] == "Keep the folder"
    assert profile_keys.save_dialog["inDialog"]
    assert profile_keys.save_dialog["visible"]


def test_tab_keeps_the_focus_in_the_removal_dialog(profile_keys):
    assert profile_keys.focus_outside_removal == []


def test_escape_cancels_the_removal_and_gives_the_focus_back_to_save(profile_keys):
    assert profile_keys.escape_dialogs == 0
    assert profile_keys.escape_focus["name"] == "Save"
    assert profile_keys.escape_status == "not saved"


def test_the_delete_and_its_second_confirmation_are_reached_by_the_keyboard(profile_keys):
    assert profile_keys.delete_stop["name"] == "Delete the folder…"
    assert profile_keys.second_step_focus["name"] == "Back"
    assert profile_keys.confirm_stop["name"] == "Delete go/ and go.work"
    assert profile_keys.confirm_stop["visible"]
    assert profile_keys.confirm_enabled


def test_back_returns_to_the_first_step_with_the_focus_on_keep(profile_keys):
    assert profile_keys.back_stop["name"] == "Back"
    assert profile_keys.first_step_again["name"] == "Keep the folder"


def test_a_refused_delete_is_disabled_with_its_reason_tied_to_it(profile_keys):
    assert profile_keys.refused_delete_disabled
    assert profile_keys.refused_reason.startswith("cannot delete go/ and go.work: attempt ")
    assert profile_keys.refused_described_by == "removal-blocked"


def test_tab_skips_a_disabled_delete_and_stays_in_the_dialog(profile_keys):
    assert profile_keys.refused_back["name"] == "Back"
    assert "Cancel" in profile_keys.refused_stops
    assert not any(name.startswith("Delete go") for name in profile_keys.refused_stops)
    assert profile_keys.refused_escape_dialogs == 0
