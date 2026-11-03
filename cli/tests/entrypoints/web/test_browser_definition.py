"""Go to definition and the library tab in a real browser
(docs/specs/web-ui.md#go-to-definition), in each engine of `tests/browsers.py`, against the scripted
fake language server: Cmd-click (Ctrl-click off macOS) and F12 move the cursor within the file, open
another file of the attempt in a tab and open a library file in a read-only tab with a badge and
its path; Ctrl-Minus goes back to where each jump started; the word under the pointer is
underlined and the pointer a hand while the key is held; a file over 4 MiB and the build area get a
note at the cursor, and an answer of nothing says `no definition found` in the status bar; and under
Vim `gd`, `Ctrl-]` and `Ctrl-o` do the same.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.preferences import Preferences
from tests.browsers import launched, watched
from tests.intelligence_lab import (
    ACTIVE_TAB,
    EDITOR,
    PANEL,
    PYTHON,
    READY,
    SERVES,
    Lab,
    Steps,
    intelligence_lab,
    open_attempt,
    point_at,
    store,
    wait_for_status,
)

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
CURSOR_LINE = f"{PANEL} .cm-lineNumbers .cm-activeLineGutter"
NOTE = ".cs-note"
PROJECT = "bank-project-python"
PROJECT_FILE_BUTTON = "button.tree-file[data-path='bank/bank.py']"
LIBRARY_STUB = "\n".join(f"# typeshed line {number}" for number in range(1, 40)) + "\n"
BIG = b"x\n" * (2 * 1024 * 1024 + 8)
"""A little over 4 MiB."""
STARTER = """\"\"\"Two Sum.\"\"\"


def target(): ...


use_same = target()
use_library = sorted([1])
use_big = big()
use_build = secret()
use_nothing = nothing()
"""
LINES = STARTER.splitlines()
LINE_OF = {
    name: next(number for number, line in enumerate(LINES) if line.startswith(f"use_{name} ="))
    for name in ("same", "library", "big", "build", "nothing")
}
"""The 0-based line of each use in the starter file."""
DEFINITION_OF_TARGET = LINES.index("def target(): ...")
LIBRARY_FILE = ".cs/lsp/library/typeshed/stdlib/builtins.pyi"
LIBRARY_LINE = 20
TARGET_WORD = (LINE_OF["same"], 11)
"""The line and column at which `target` starts in `use_same = target()`."""


def location(uri: str, line: int) -> dict[str, object]:
    start = {"line": line, "character": 0}
    return {"uri": uri, "range": {"start": start, "end": {"line": line, "character": 1}}}


def script(workspace: Path) -> Steps:
    def at(use: str, result: object) -> dict[str, object]:
        return {"when": {"position": {"line": LINE_OF[use]}}, "result": result}

    link = {
        "targetUri": "$dir/models.py",
        "targetRange": location("", 0)["range"],
        "targetSelectionRange": location("", 0)["range"],
    }
    cases = [
        at("same", location("$uri", DEFINITION_OF_TARGET)),
        {"when": {"position": {"line": 0}}, "result": [link]},
        at("library", [location((workspace / LIBRARY_FILE).as_uri(), LIBRARY_LINE)]),
        at("big", location((workspace / "vendor" / "big.py").as_uri(), 120)),
        at("build", location((workspace / ".cs" / "build" / "solution.py").as_uri(), 0)),
        at("nothing", []),
    ]
    return (SERVES, {"answer": {"textDocument/definition": {"cases": cases}}})


@dataclass
class Seen:
    same_file_line: str = ""
    back_from_same_file: str = ""
    other_tab: str = ""
    other_tab_line: str = ""
    back_from_other_tab: str = ""
    back_to_tab: str = ""
    library_tab: str = ""
    library_badge: str = ""
    library_tab_path: str = ""
    library_note: str = ""
    library_line: str = ""
    library_label: str = ""
    library_readonly: str = ""
    library_text_after_typing: str = ""
    library_modified_marker: int = -1
    back_from_library_tab: str = ""
    back_from_library_line: str = ""
    big_note: str = ""
    tabs_after_big: int = -1
    note_after_key: int = -1
    build_status: str = ""
    build_notes: int = -1
    nothing_status: str = ""
    nothing_status_later: str = ""
    f12_line: str = ""
    link_text: str = ""
    link_cursor: str = ""
    link_after_release: int = -1
    plain_click_line: str = ""
    cursors_after_alt_shift_click: int = -1
    definitions_asked_by_alt_shift_click: int = -1
    vim_gd: str = ""
    vim_ctrl_o: str = ""
    vim_ctrl_bracket: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"definition-{engine}")
    files: dict[str, str | bytes] = {
        "python/practice/two_sum.py": STARTER,
        LIBRARY_FILE: LIBRARY_STUB,
        "vendor/big.py": BIG,
    }
    problems = [PYTHON, (PROJECT, None)]
    with intelligence_lab(
        practice_workspace, base, script, files=files, problems=problems
    ) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, lab: Lab) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(lab.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        open_attempt(page, lab)
        wait_for_status(page, READY)
        _in_the_file(page, found)
        _into_another_tab(page, lab, found)
        open_attempt(page, lab)
        wait_for_status(page, READY)
        _into_a_library(page, found)
        _refused(page, found)
        _the_link_while_the_key_is_held(page, lab, found)
        _vim(browser, lab, found)
        browser.close()
    return found


def _click_with_the_key(page: Any, line: int, column: int) -> None:
    point = point_at(page, line, column)
    page.keyboard.down("ControlOrMeta")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("ControlOrMeta")


def _cursor_line(page: Any) -> str:
    return page.locator(CURSOR_LINE).inner_text()


def _wait_for_line(page: Any, line: int) -> str:
    page.wait_for_function(
        "([selector, line]) => document.querySelector(selector)?.textContent === String(line)",
        arg=[CURSOR_LINE, line],
    )
    return _cursor_line(page)


def _back(page: Any) -> None:
    page.keyboard.press("Control+Minus")


def _in_the_file(page: Any, found: Seen) -> None:
    _click_with_the_key(page, LINE_OF["same"], 12)
    found.same_file_line = _wait_for_line(page, DEFINITION_OF_TARGET + 1)
    _back(page)
    found.back_from_same_file = _wait_for_line(page, LINE_OF["same"] + 1)
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    for _ in range(LINE_OF["same"]):
        page.keyboard.press("ArrowDown")
    for _ in range(12):
        page.keyboard.press("ArrowRight")
    page.keyboard.press("F12")
    found.f12_line = _wait_for_line(page, DEFINITION_OF_TARGET + 1)
    _back(page)
    _wait_for_line(page, LINE_OF["same"] + 1)


def _into_another_tab(page: Any, lab: Lab, found: Seen) -> None:
    """In the project, a definition in another file of its tree opens that file's tab."""
    open_attempt(page, lab, PROJECT, with_file=False)
    page.click(PROJECT_FILE_BUTTON)
    wait_for_status(page, READY)
    _click_with_the_key(page, 0, 3)
    page.wait_for_function(
        "selector => document.querySelector(selector)?.title === 'bank/models.py'",
        arg=ACTIVE_TAB,
    )
    found.other_tab = page.get_attribute(ACTIVE_TAB, "title")
    found.other_tab_line = _cursor_line(page)
    _back(page)
    page.wait_for_function(
        "selector => document.querySelector(selector)?.title === 'bank/bank.py'", arg=ACTIVE_TAB
    )
    found.back_to_tab = page.get_attribute(ACTIVE_TAB, "title")
    found.back_from_other_tab = _wait_for_line(page, 1)


def _into_a_library(page: Any, found: Seen) -> None:
    _click_with_the_key(page, LINE_OF["library"], 14)
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    found.library_tab = page.locator(ACTIVE_TAB).inner_text()
    found.library_badge = page.locator(f"{ACTIVE_TAB} .badge").inner_text()
    found.library_tab_path = page.get_attribute(ACTIVE_TAB, "title")
    found.library_note = page.locator(f"{PANEL} .library-note").inner_text()
    found.library_line = _wait_for_line(page, LIBRARY_LINE + 1)
    found.library_label = page.get_attribute(f"{PANEL} .cm-content", "aria-label")
    found.library_readonly = page.get_attribute(f"{PANEL} .cm-content", "aria-readonly")
    page.keyboard.type("typed")
    page.keyboard.press("ControlOrMeta+s")
    found.library_text_after_typing = "\n".join(page.locator(f"{PANEL} .cm-line").all_inner_texts())
    found.library_modified_marker = page.locator("[role=tab].is-modified").count()
    _back(page)
    page.wait_for_function(
        "selector => !document.querySelector(selector)?.querySelector('.badge')", arg=ACTIVE_TAB
    )
    found.back_from_library_tab = page.get_attribute(ACTIVE_TAB, "title")
    found.back_from_library_line = _wait_for_line(page, LINE_OF["library"] + 1)


def _refused(page: Any, found: Seen) -> None:
    tabs = page.locator("[role=tab]").count()
    _click_with_the_key(page, LINE_OF["big"], 12)
    page.wait_for_selector(NOTE)
    found.big_note = page.locator(NOTE).inner_text()
    found.tabs_after_big = page.locator("[role=tab]").count() - tabs
    page.keyboard.press("Shift")
    page.wait_for_selector(NOTE, state="detached")
    found.note_after_key = page.locator(NOTE).count()
    _click_with_the_key(page, LINE_OF["build"], 14)
    found.build_status = wait_for_status(page, "no definition found")
    found.build_notes = page.locator(NOTE).count()
    page.wait_for_function(
        "selector => !document.querySelector(selector).textContent.startsWith('no definition')",
        arg=".statusbar .code-intelligence",
    )
    _click_with_the_key(page, LINE_OF["nothing"], 16)
    found.nothing_status = wait_for_status(page, "no definition found")
    page.wait_for_function(
        "selector => !document.querySelector(selector).textContent.startsWith('no definition')",
        arg=".statusbar .code-intelligence",
    )
    found.nothing_status_later = wait_for_status(page, READY)


def _the_link_while_the_key_is_held(page: Any, lab: Lab, found: Seen) -> None:
    point = point_at(page, *TARGET_WORD)
    page.mouse.move(point["x"], point["y"])
    page.keyboard.down("ControlOrMeta")
    page.mouse.move(point["x"] + 1, point["y"])
    page.wait_for_selector(".cs-definition-link")
    found.link_text = page.locator(".cs-definition-link").inner_text()
    found.link_cursor = page.evaluate(
        "selector => getComputedStyle(document.querySelector(selector)).cursor",
        f"{PANEL} .cm-content",
    )
    page.keyboard.up("ControlOrMeta")
    page.wait_for_selector(".cs-definition-link", state="detached")
    found.link_after_release = page.locator(".cs-definition-link").count()
    point = point_at(page, LINE_OF["same"], 12)
    page.mouse.click(point["x"], point["y"])
    found.plain_click_line = _wait_for_line(page, LINE_OF["same"] + 1)
    _alt_shift_click(page, lab, found)


def _alt_shift_click(page: Any, lab: Lab, found: Seen) -> None:
    """Whatever the setting says, Alt-Shift-click adds a cursor and asks for no definition."""
    asked = _definition_requests(lab)
    point = point_at(page, LINE_OF["library"], 3)
    page.keyboard.down("Alt")
    page.keyboard.down("Shift")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("Shift")
    page.keyboard.up("Alt")
    page.wait_for_function(
        "selector => document.querySelectorAll(selector).length === 2",
        arg=f"{PANEL} .cm-cursor",
    )
    found.cursors_after_alt_shift_click = page.locator(f"{PANEL} .cm-cursor").count()
    found.definitions_asked_by_alt_shift_click = _definition_requests(lab) - asked
    page.keyboard.press("Escape")


def _definition_requests(lab: Lab) -> int:
    return len([m for m in lab.script.received() if m.get("method") == "textDocument/definition"])


def _vim(browser: Any, lab: Lab, found: Seen) -> None:
    """With Vim on, `gd` and `Ctrl-]` go to the definition, `Ctrl-o` back by the jump list."""
    store(lab, Preferences(code_intelligence=True, vim=True))
    page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
    page.set_default_timeout(WAIT_MS)
    page.goto(lab.server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    open_attempt(page, lab)
    wait_for_status(page, READY)
    page.click(EDITOR)
    page.keyboard.press("Escape")
    page.keyboard.press("g")
    page.keyboard.press("g")
    for _ in range(LINE_OF["same"]):
        page.keyboard.press("j")
    for _ in range(12):
        page.keyboard.press("l")
    page.keyboard.press("g")
    page.keyboard.press("d")
    found.vim_gd = _wait_for_line(page, DEFINITION_OF_TARGET + 1)
    page.keyboard.press("Control+o")
    found.vim_ctrl_o = _wait_for_line(page, LINE_OF["same"] + 1)
    page.keyboard.press("Control+]")
    found.vim_ctrl_bracket = _wait_for_line(page, DEFINITION_OF_TARGET + 1)


def test_cmd_or_ctrl_click_moves_the_cursor_to_a_definition_in_the_file(seen):
    assert seen.same_file_line == str(DEFINITION_OF_TARGET + 1)


def test_back_returns_to_where_the_jump_started(seen):
    assert seen.back_from_same_file == str(LINE_OF["same"] + 1)


def test_f12_goes_to_the_definition_too(seen):
    assert seen.f12_line == str(DEFINITION_OF_TARGET + 1)


def test_a_definition_in_another_file_of_the_attempt_opens_its_tab(seen):
    assert seen.other_tab == "bank/models.py"


def test_the_cursor_is_at_the_definition_in_that_tab(seen):
    assert seen.other_tab_line == "1"


def test_back_returns_to_the_tab_the_jump_started_in(seen):
    assert (seen.back_to_tab, seen.back_from_other_tab) == ("bank/bank.py", "1")


def test_a_library_definition_opens_a_tab_with_a_library_badge(seen):
    assert seen.library_badge == "library"


def test_the_library_tab_names_the_files_path(seen):
    assert seen.library_tab_path == LIBRARY_FILE


def test_the_library_tab_shows_its_path_and_that_it_is_read_only(seen):
    assert seen.library_note.endswith(f"{LIBRARY_FILE} · read-only")


def test_the_cursor_is_at_the_library_definition(seen):
    assert seen.library_line == str(LIBRARY_LINE + 1)


def test_the_library_editor_names_its_path_and_says_read_only_to_screen_readers(seen):
    assert (seen.library_label, seen.library_readonly) == (LIBRARY_FILE, "true")


def test_a_library_file_cannot_be_edited_or_saved(seen):
    assert "typed" not in seen.library_text_after_typing
    assert seen.library_modified_marker == 0


def test_back_from_a_library_tab_returns_to_the_attempt_file(seen):
    assert (seen.back_from_library_tab, seen.back_from_library_line) == (
        "two_sum.py",
        str(LINE_OF["library"] + 1),
    )


def test_a_file_over_4_mib_gets_a_note_with_its_line_and_reason(seen):
    assert seen.big_note == "vendor/big.py:121 · over 4 MiB"


def test_a_refused_file_opens_no_tab(seen):
    assert seen.tabs_after_big == 0


def test_the_note_closes_on_the_next_key(seen):
    assert seen.note_after_key == 0


def test_a_definition_in_the_build_area_is_no_location(seen):
    assert (seen.build_status, seen.build_notes) == ("no definition found", 0)


def test_no_location_says_so_in_the_status_bar_for_a_moment(seen):
    assert (seen.nothing_status, seen.nothing_status_later) == ("no definition found", READY)


def test_the_word_under_the_pointer_is_underlined_while_the_key_is_held(seen):
    assert seen.link_text == "target"


def test_the_pointer_is_a_hand_while_the_key_is_held(seen):
    assert seen.link_cursor == "pointer"


def test_the_underline_goes_when_the_key_is_released(seen):
    assert seen.link_after_release == 0


def test_a_plain_click_only_moves_the_cursor(seen):
    assert seen.plain_click_line == str(LINE_OF["same"] + 1)


def test_under_vim_gd_goes_to_the_definition(seen):
    assert seen.vim_gd == str(DEFINITION_OF_TARGET + 1)


def test_under_vim_ctrl_o_goes_back_through_the_jump_list(seen):
    assert seen.vim_ctrl_o == str(LINE_OF["same"] + 1)


def test_under_vim_ctrl_bracket_goes_to_the_definition(seen):
    assert seen.vim_ctrl_bracket == str(DEFINITION_OF_TARGET + 1)


def test_alt_shift_click_adds_a_cursor_with_code_intelligence_on(seen):
    assert (seen.cursors_after_alt_shift_click, seen.definitions_asked_by_alt_shift_click) == (2, 0)


def test_the_page_logs_no_error_for_go_to_definition(seen):
    assert seen.errors == []
