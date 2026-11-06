"""The `autocomplete` preference governs all completion in the editor
(docs/specs/web-ui.md#autocomplete), in each engine of `tests/browsers.py`: with the defaults, and
with code intelligence off whatever `autocomplete` holds, Ctrl-Space and typing offer no list;
with both on, CodeMirror's own completion offers one, and Tab accepts from it; with no list, and
with autocomplete off, Tab indents. Bracket closing stays in every case.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
PREFERENCES = Path(".cs") / "serve" / "preferences.json"
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
EDITOR = ".panel:not([hidden]) .cm-editor"
CONTENT = f"{EDITOR} .cm-content"
LIST = ".cm-tooltip-autocomplete"
LOOKED_FOR = "\nprin"
INTERACTION_MS = 100
"""How long a key waits after the list shows: CodeMirror's `interactionDelay`, 75 ms, keeps a key
pressed as the list appears from accepting by accident, for Enter and Tab alike."""
SETTLE_MS = 600
"""What a list that is not coming is given to show up in: the completion source answers in the
same task, and the list is drawn within a frame or two."""


@dataclass
class Completion:
    """Whether a list showed in each state of the preferences."""

    defaults: int = -1
    typed_by_default: int = -1
    autocomplete_only: int = -1
    both: int = -1
    brackets_closed: str = ""
    tab_when_off: str = ""
    tab_with_a_list: str = ""
    tab_without_a_list: str = ""


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"completion-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def completion(engine: str, server: RunningServer) -> Completion:
    seen = Completion()
    workspace = Path(server.environment["CSTUDY_WORKSPACE"])
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("dialog", lambda dialog: dialog.accept())
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _start(page)
        seen.defaults = _list_on_ctrl_space(page)
        seen.typed_by_default = _list_after_typing(page)
        seen.brackets_closed = _closed_bracket(page)
        seen.tab_when_off = _tab_on_a_new_line(page)
        _store(workspace, code_intelligence=False, autocomplete=True)
        seen.autocomplete_only = _after_reload(page, _list_on_ctrl_space)
        _store(workspace, code_intelligence=True, autocomplete=True)
        seen.both = _after_reload(page, _list_on_ctrl_space)
        seen.tab_with_a_list = _tab_accepting(page)
        seen.tab_without_a_list = _tab_on_a_new_line(page)
        browser.close()
    return seen


def _start(page: Any) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.click(".practice-actions button.primary")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(CONTENT)


def _store(workspace: Path, **changes: bool) -> None:
    path = workspace / PREFERENCES
    document = json.loads(path.read_text()) if path.exists() else {"format": 1}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**document, **changes}) + "\n")


def _after_reload(page: Any, step: Any) -> int:
    page.reload()
    page.wait_for_selector(CONTENT)
    return step(page)


def _at_the_end(page: Any) -> None:
    page.click(CONTENT)
    page.keyboard.press("ControlOrMeta+End")


def _list_on_ctrl_space(page: Any) -> int:
    """Types `prin` at the end of the file, asks for completion, and counts the lists; the typing
    is undone, so the file is not modified when the page reloads."""
    _at_the_end(page)
    page.keyboard.insert_text(LOOKED_FOR)
    page.keyboard.press("Control+Space")
    page.wait_for_timeout(SETTLE_MS)
    shown = page.locator(LIST).count()
    page.keyboard.press("Escape")
    page.keyboard.press("ControlOrMeta+z")
    return shown


def _list_after_typing(page: Any) -> int:
    _at_the_end(page)
    page.keyboard.type("prin")
    page.wait_for_timeout(SETTLE_MS)
    shown = page.locator(LIST).count()
    for _ in range(4):
        page.keyboard.press("Backspace")
    return shown


def _closed_bracket(page: Any) -> str:
    _at_the_end(page)
    page.keyboard.type("(")
    typed = page.locator(f"{CONTENT} .cm-line").last.inner_text()
    page.keyboard.press("Backspace")
    page.keyboard.press("Delete")
    return typed


def _tab_on_a_new_line(page: Any) -> str:
    """Tab with no list open, on an empty line at the end of the file; the typing is undone."""
    _at_the_end(page)
    page.keyboard.insert_text("\nx = 1")
    page.keyboard.press("Tab")
    line = page.locator(f"{CONTENT} .cm-line").last.inner_text()
    page.keyboard.press("Shift+Tab")
    page.keyboard.press("ControlOrMeta+z")
    return line


def _tab_accepting(page: Any) -> str:
    """Tab with the list open, from the file's end; the typing is undone."""
    _at_the_end(page)
    page.keyboard.insert_text(LOOKED_FOR)
    page.keyboard.press("Control+Space")
    page.wait_for_selector(LIST)
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Tab")
    page.wait_for_selector(LIST, state="detached")
    line = page.locator(f"{CONTENT} .cm-line").last.inner_text()
    page.keyboard.press("ControlOrMeta+z")
    page.keyboard.press("ControlOrMeta+z")
    return line


def test_ctrl_space_offers_no_list_at_the_defaults(completion):
    assert completion.defaults == 0


def test_typing_offers_no_list_at_the_defaults(completion):
    assert completion.typed_by_default == 0


def test_brackets_still_close_at_the_defaults(completion):
    assert completion.brackets_closed.endswith("()")


def test_autocomplete_alone_offers_no_list(completion):
    assert completion.autocomplete_only == 0


def test_both_preferences_offer_the_editors_own_list(completion):
    assert completion.both == 1


def test_tab_accepts_the_selected_option_of_the_editors_own_list(completion):
    assert completion.tab_with_a_list.startswith("print")


def test_with_no_list_open_tab_indents_by_the_languages_unit(completion):
    assert completion.tab_without_a_list == "    x = 1"


def test_with_autocomplete_off_tab_indents(completion):
    assert completion.tab_when_off == "    x = 1"
