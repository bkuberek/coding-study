"""Completion and signature help from the language server in a real browser
(docs/specs/web-ui.md#autocomplete), in each engine of `tests/browsers.py`, against the scripted
fake language server.

With `autocomplete` off, typing and Ctrl-Space open no list and ask the server for nothing. With
both preferences on: typing a word, a trigger character and Ctrl-Space ask the server and show its
list; the selected item's panel shows the resolved detail and documentation, each item resolved
once however often it is selected; Enter and Tab each accept and insert the item's text, while
with no list open Tab indents and Shift-Tab takes it back;
`(` and `,` in a call open the signature help, whose bold parameter follows the cursor, which
Escape closes and Cmd or Ctrl-Shift-Space opens again. While the session has stopped, the editor's
own completion stands in, and Tab accepts from it too. Under Vim one Escape closes the list and
leaves insert mode, and Tab in insert mode accepts as it does without Vim.

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
    EDITOR,
    PANEL,
    READY,
    SERVES,
    Lab,
    intelligence_lab,
    open_attempt,
    store,
    wait_for_status,
)

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
LIST = ".cm-tooltip-autocomplete"
OPTIONS = f"{LIST} li"
INFO = ".cm-completionInfo"
SIGNATURE = ".cs-signature"
ACTIVE_PARAMETER = f"{SIGNATURE} .cs-active-parameter"
LAST_LINE = f"{EDITOR} .cm-line:last-child"
INTERACTION_MS = 100
"""How long a key waits after the list shows: CodeMirror's `interactionDelay`, 75 ms, keeps a key
pressed as the list appears from accepting by accident, for Enter and Tab alike."""
SETTLE_MS = 700
"""What a list that is not coming is given to show up in."""
ITEMS = [
    {"label": "heappush", "kind": 3, "sortText": "1"},
    {"label": "heappop", "kind": 3, "sortText": "2"},
    {"label": "heapify", "kind": 3, "sortText": "3"},
]
DOCUMENTS = {
    "heappush": ("(heap: list, item) -> None", "Push *item* onto the heap."),
    "heappop": ("(heap: list) -> Any", "Pop the smallest item."),
    "heapify": ("(x: list) -> None", "Transform a list into a heap."),
}


def signature(active: int) -> dict[str, Any]:
    return {
        "signatures": [
            {
                "label": "heappush(heap, item)",
                "parameters": [{"label": "heap"}, {"label": "item"}],
                "documentation": {"kind": "markdown", "value": "Push onto it."},
            }
        ],
        "activeSignature": 0,
        "activeParameter": active,
    }


ANSWERS: dict[str, object] = {
    "answer": {
        "textDocument/completion": {"isIncomplete": False, "items": ITEMS},
        "completionItem/resolve": {
            "cases": [
                {
                    "when": {"label": label},
                    "result": {
                        "label": label,
                        "detail": detail,
                        "documentation": {"kind": "markdown", "value": text},
                    },
                }
                for label, (detail, text) in DOCUMENTS.items()
            ]
        },
        "textDocument/signatureHelp": {
            "cases": [
                {"when": {"context": {"triggerCharacter": ","}}, "result": signature(1)},
                {"result": signature(0)},
            ]
        },
    }
}
SCRIPT = (SERVES, ANSWERS)
STOPPED_SCRIPT = (SERVES, {"err": "boom"}, {"exit": 3})
ON = Preferences(code_intelligence=True, autocomplete=True)


@dataclass
class Seen:
    off_lists: int = -1
    off_ctrl_space_lists: int = -1
    off_completion_requests: int = -1
    off_signature_helps: int = -1
    on_options: list[str] = field(default_factory=list[str])
    on_info: str = ""
    on_request_context: dict[str, Any] = field(default_factory=dict[str, Any])
    resolved_push: int = -1
    resolved_pop: int = -1
    accepted_line: str = ""
    tab_line: str = ""
    tab_list_after: int = -1
    tab_without_list: str = ""
    shift_tab_without_list: str = ""
    dot_requests: int = -1
    ctrl_space_options: int = -1
    ctrl_space_requests: int = -1
    signature_label: str = ""
    signature_documentation: str = ""
    first_parameter: str = ""
    second_parameter: str = ""
    signature_after_escape: int = -1
    signature_by_key: int = -1
    fallback_options: list[str] = field(default_factory=list[str])
    fallback_requests: int = -1
    fallback_tab_line: str = ""
    vim_tab_line: str = ""
    vim_list: int = -1
    vim_list_after_escape: int = -1
    vim_normal_after_escape: int = -1
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"autocomplete-{engine}")
    only_intelligence = Preferences(code_intelligence=True)
    with intelligence_lab(practice_workspace, base, SCRIPT, preferences=only_intelligence) as lab:
        yield lab


@pytest.fixture(scope="module")
def stopped_lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"autocomplete-stopped-{engine}")
    with intelligence_lab(practice_workspace, base, STOPPED_SCRIPT, preferences=ON) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, lab: Lab, stopped_lab: Lab) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = _page(browser, lab, found)
        _autocomplete_off(page, lab, found)
        store(lab, ON)
        page = _page(browser, lab, found)
        _list_and_panel(page, lab, found)
        _accepting(page, found)
        _triggers(page, lab, found)
        _signature(page, found)
        store(lab, Preferences(code_intelligence=True, autocomplete=True, vim=True))
        page = _page(browser, lab, found)
        _vim(page, found)
        _stopped(browser, stopped_lab, found)
        browser.close()
    return found


def _page(browser: Any, lab: Lab, found: Seen) -> Any:
    page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
    page.set_default_timeout(WAIT_MS)
    page.goto(lab.server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    open_attempt(page, lab)
    wait_for_status(page, READY)
    return page


def _requests(lab: Lab, method: str) -> list[dict[str, Any]]:
    return [message for message in lab.script.received() if message.get("method") == method]


def _at_the_end(page: Any) -> None:
    page.click(EDITOR)
    page.mouse.move(5, 5)
    page.keyboard.press("ControlOrMeta+End")


def _autocomplete_off(page: Any, lab: Lab, found: Seen) -> None:
    _at_the_end(page)
    page.keyboard.type("hea")
    page.wait_for_timeout(SETTLE_MS)
    found.off_lists = page.locator(LIST).count()
    page.keyboard.press("Control+Space")
    page.wait_for_timeout(SETTLE_MS)
    found.off_ctrl_space_lists = page.locator(LIST).count()
    page.keyboard.type("push(")
    page.wait_for_timeout(SETTLE_MS)
    found.off_signature_helps = page.locator(SIGNATURE).count()
    found.off_completion_requests = len(_requests(lab, "textDocument/completion"))


def _list_and_panel(page: Any, lab: Lab, found: Seen) -> None:
    _at_the_end(page)
    page.keyboard.press("Enter")
    page.keyboard.type("hea")
    page.wait_for_selector(INFO)
    found.on_options = page.locator(OPTIONS).all_inner_texts()
    found.on_info = page.locator(INFO).inner_text()
    found.on_request_context = _requests(lab, "textDocument/completion")[-1]["params"]["context"]
    page.keyboard.press("ArrowDown")
    page.wait_for_function(
        "text => document.querySelector('.cm-completionInfo')?.textContent.includes(text)",
        arg="Pop the smallest item",
    )
    page.keyboard.press("ArrowUp")
    page.wait_for_function(
        "text => document.querySelector('.cm-completionInfo')?.textContent.includes(text)",
        arg="Push item onto the heap",
    )
    labels = [message["params"]["label"] for message in _requests(lab, "completionItem/resolve")]
    found.resolved_push = labels.count("heappush")
    found.resolved_pop = labels.count("heappop")


def _accepting(page: Any, found: Seen) -> None:
    page.keyboard.press("Enter")
    page.wait_for_selector(LIST, state="detached")
    found.accepted_line = page.locator(LAST_LINE).inner_text()
    page.keyboard.press("Enter")
    page.keyboard.type("hea")
    page.wait_for_selector(LIST)
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Tab")
    page.wait_for_selector(LIST, state="detached")
    found.tab_line = page.locator(LAST_LINE).inner_text()
    found.tab_list_after = page.locator(LIST).count()
    page.keyboard.press("Tab")
    found.tab_without_list = page.locator(LAST_LINE).inner_text()
    page.keyboard.press("Shift+Tab")
    found.shift_tab_without_list = page.locator(LAST_LINE).inner_text()


def _triggers(page: Any, lab: Lab, found: Seen) -> None:
    page.keyboard.press("Enter")
    page.keyboard.type("heapq")
    page.keyboard.press("Escape")
    asked = len(_requests(lab, "textDocument/completion"))
    page.keyboard.type(".")
    page.wait_for_selector(LIST)
    triggered = [
        message
        for message in _requests(lab, "textDocument/completion")[asked:]
        if message["params"]["context"].get("triggerCharacter") == "."
    ]
    found.dot_requests = len(triggered)
    page.keyboard.press("Escape")
    page.keyboard.press("Enter")
    asked = len(_requests(lab, "textDocument/completion"))
    page.keyboard.press("Control+Space")
    page.wait_for_selector(LIST)
    found.ctrl_space_options = page.locator(OPTIONS).count()
    found.ctrl_space_requests = len(_requests(lab, "textDocument/completion")) - asked
    page.keyboard.press("Escape")


def _signature(page: Any, found: Seen) -> None:
    page.keyboard.press("Enter")
    page.keyboard.type("heappush(")
    page.wait_for_selector(SIGNATURE)
    found.signature_label = page.locator(f"{SIGNATURE} .cs-signature-label").inner_text()
    found.signature_documentation = page.locator(SIGNATURE).inner_text()
    found.first_parameter = page.locator(ACTIVE_PARAMETER).inner_text()
    page.keyboard.type("1")
    page.wait_for_timeout(SETTLE_MS)
    page.keyboard.type(",")
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent === 'item'",
        arg=ACTIVE_PARAMETER,
    )
    found.second_parameter = page.locator(ACTIVE_PARAMETER).inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(SIGNATURE, state="detached")
    found.signature_after_escape = page.locator(SIGNATURE).count()
    page.keyboard.press("ControlOrMeta+Shift+Space")
    page.wait_for_selector(SIGNATURE)
    found.signature_by_key = page.locator(SIGNATURE).count()
    page.keyboard.press("Escape")


def _vim(page: Any, found: Seen) -> None:
    """Tab in insert mode accepts; one Escape closes the list and leaves insert mode."""
    page.click(EDITOR)
    page.mouse.move(5, 5)
    page.keyboard.press("Escape")
    page.keyboard.press("G")
    page.keyboard.press("o")
    page.keyboard.type("hea")
    page.wait_for_selector(LIST)
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Tab")
    page.wait_for_selector(LIST, state="detached")
    found.vim_tab_line = page.locator(LAST_LINE).inner_text()
    page.keyboard.press("Enter")
    page.keyboard.type("hea")
    page.wait_for_selector(LIST)
    found.vim_list = page.locator(LIST).count()
    page.keyboard.press("Escape")
    page.wait_for_selector(LIST, state="detached")
    found.vim_list_after_escape = page.locator(LIST).count()
    page.wait_for_selector(f"{PANEL} .cm-vimMode")
    found.vim_normal_after_escape = page.locator(f"{PANEL} .cm-vimMode").count()


def _stopped(browser: Any, lab: Lab, found: Seen) -> None:
    """While the session has stopped, the editor's own completion stands in."""
    page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
    page.set_default_timeout(WAIT_MS)
    page.goto(lab.server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    open_attempt(page, lab)
    wait_for_status(page, "python · basedpyright · stopped")
    _at_the_end(page)
    page.keyboard.type("prin")
    page.wait_for_selector(LIST)
    found.fallback_options = page.locator(f"{LIST} .cm-completionLabel").all_inner_texts()
    found.fallback_requests = len(_requests(lab, "textDocument/completion"))
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Tab")
    page.wait_for_selector(LIST, state="detached")
    found.fallback_tab_line = page.locator(LAST_LINE).inner_text()


def test_with_autocomplete_off_typing_opens_no_list(seen):
    assert seen.off_lists == 0


def test_with_autocomplete_off_ctrl_space_opens_no_list(seen):
    assert seen.off_ctrl_space_lists == 0


def test_with_autocomplete_off_the_server_is_asked_for_no_completion(seen):
    assert seen.off_completion_requests == 0


def test_with_autocomplete_off_a_call_opens_no_signature_help(seen):
    assert seen.off_signature_helps == 0


def test_the_list_shows_the_servers_items(seen):
    assert all(name in " ".join(seen.on_options) for name in ("heappush", "heappop", "heapify"))


def test_a_word_typed_asks_for_completion_as_invoked(seen):
    assert seen.on_request_context["triggerKind"] == 1


def test_the_panel_shows_the_resolved_detail_and_documentation(seen):
    assert "(heap: list, item) -> None" in seen.on_info
    assert "Push item onto the heap." in seen.on_info


def test_each_item_is_resolved_once_however_often_it_is_selected(seen):
    assert (seen.resolved_push, seen.resolved_pop) == (1, 1)


def test_enter_inserts_the_items_text_in_place_of_the_typed_word(seen):
    assert seen.accepted_line == "heappush"


def test_tab_accepts_the_selected_item_in_place_of_the_typed_word(seen):
    assert seen.tab_line == "heappush"


def test_tab_closes_the_list_it_accepts_from(seen):
    assert seen.tab_list_after == 0


def test_with_no_list_open_tab_indents_the_line(seen):
    assert seen.tab_without_list == "    heappush"


def test_with_no_list_open_shift_tab_takes_the_indent_back(seen):
    assert seen.shift_tab_without_list == "heappush"


def test_tab_accepts_from_the_editors_own_completion_while_the_session_has_stopped(seen):
    assert seen.fallback_tab_line.startswith("print")


def test_tab_in_vim_insert_mode_accepts_the_selected_item(seen):
    assert seen.vim_tab_line == "heappush"


def test_a_trigger_character_asks_as_a_trigger(seen):
    assert seen.dot_requests >= 1


def test_ctrl_space_asks_and_shows_the_list_anywhere(seen):
    assert (seen.ctrl_space_options, seen.ctrl_space_requests) == (3, 1)


def test_the_open_parenthesis_of_a_call_opens_the_signature_help(seen):
    assert seen.signature_label == "heappush(heap, item)"
    assert "Push onto it." in seen.signature_documentation


def test_the_first_parameter_is_bold_at_first(seen):
    assert seen.first_parameter == "heap"


def test_the_bold_parameter_follows_the_cursor_through_the_call(seen):
    assert seen.second_parameter == "item"


def test_escape_closes_the_signature_help(seen):
    assert seen.signature_after_escape == 0


def test_cmd_or_ctrl_shift_space_opens_the_signature_help(seen):
    assert seen.signature_by_key == 1


def test_under_vim_the_list_opens_in_insert_mode(seen):
    assert seen.vim_list == 1


def test_under_vim_one_escape_closes_the_list_and_leaves_insert_mode(seen):
    assert (seen.vim_list_after_escape, seen.vim_normal_after_escape) == (0, 1)


def test_while_the_session_is_stopped_the_editors_own_completion_stands_in(seen):
    assert "print" in " ".join(seen.fallback_options)
    assert seen.fallback_requests == 0


def test_the_page_logs_no_error_for_autocomplete(seen):
    assert seen.errors == []
