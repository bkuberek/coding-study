"""Kotlin code intelligence in a real browser (docs/specs/web-ui.md#code-intelligence-in-the-
editor, ADR 0018, Kotlin revisited), in each engine of `tests/browsers.py`, against the scripted
fake language server playing the Kotlin LSP, which `cstudy serve` starts as the launcher of its
build in `.cs/lsp/`: a Kotlin file opens a session that becomes ready; the page pulls its
diagnostics, which come empty while the server imports and then, after the server asks for a
refresh, as an underlined error with a gutter marker and faded unused code; hover shows the KDoc
the server sends as code and text; Cmd-click (Ctrl-click off macOS) moves the cursor within the
file and names a source of the standard library in a note, since the Kotlin LSP names it by a
`jar:` URI; with `autocomplete` on, `.` lists the server's items with the resolved documentation
beside them. With the license not accepted, the status bar says so and no session starts. No
console error.

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
    Lab,
    Steps,
    intelligence_lab,
    open_attempt,
    point_at,
    wait_for_status,
)
from tests.language_server_scripts import request

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
KOTLIN = ("two-sum", "kotlin")
SLUG = KOTLIN[0]
SOURCE_FILE = "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt"
STARTER = """package practice.two_sum

class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        val seen = mutableListOf<Int>()
        val same = helper()
        return intArrayOf(same)
    }

    fun helper(): Int = 0
}
"""
LINES = STARTER.splitlines()
SEEN_LINE = 4
SAME_LINE = 5
HELPER_LINE = 9
MUTABLE_LIST = (SEEN_LINE, LINES[SEEN_LINE].index("mutableListOf") + 2)
HELPER = (SAME_LINE, LINES[SAME_LINE].index("helper") + 2)
STANDARD_LIBRARY = (
    "jar:///home/me/.gradle/caches/modules-2/files-2.1/org.jetbrains.kotlin/kotlin-stdlib/2.4.21/"
    "31672572/kotlin-stdlib-2.4.21-sources.jar!/kotlin/collections/Collections.kt"
)
ADD_DOCUMENTATION = "Adds the specified element to the end of this list."
CAPABILITIES = {
    "textDocumentSync": {"openClose": True, "change": 2, "save": {"includeText": False}},
    "hoverProvider": True,
    "definitionProvider": True,
    "completionProvider": {"resolveProvider": True, "triggerCharacters": ["."]},
    "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
    "diagnosticProvider": {"interFileDependencies": True, "workspaceDiagnostics": False},
}
"""The Kotlin LSP's own, as the spike's `initialize` answered: diagnostics only when asked."""
READY = "kotlin · kotlin-lsp · ready"
NOT_ACCEPTED = "no code intelligence for Kotlin: kotlin-lsp's license is not accepted"
ERROR = f"{PANEL} .cm-lintRange-error"
GUTTER_MARKER = f"{PANEL} .cm-lint-marker-error"
UNNECESSARY = f"{PANEL} .cstudy-unnecessary"
HOVER = ".cm-tooltip-hover .cs-hover"
NOTE = ".cs-note"
LIST = ".cm-tooltip-autocomplete"
INFO = ".cm-completionInfo"
CURSOR_LINE = f"{PANEL} .cm-lineNumbers .cm-activeLineGutter"
INTERACTION_MS = 100
"""CodeMirror's `interactionDelay`, 75 ms, keeps a key pressed as the list appears from accepting
it, so Enter waits that long after the list shows."""


def _range(line: int, start: int, end: int) -> dict[str, object]:
    return {"start": {"line": line, "character": start}, "end": {"line": line, "character": end}}


def script(_workspace: Path) -> Steps:
    """The Kotlin LSP's answers in their own shapes: no diagnostics while it imports, a refresh,
    then the file's; hover as KDoc with the declaration in a code block; the standard library by
    a `jar:` URI; items named as the Kotlin LSP names them."""
    definitions = [
        {"when": {"position": {"line": SAME_LINE}}, "result": [_location("$uri", HELPER_LINE)]},
        {"when": {"position": {"line": SEEN_LINE}}, "result": [_location(STANDARD_LIBRARY, 141)]},
    ]
    hover = {
        "contents": {
            "kind": "markdown",
            "value": f"{ADD_DOCUMENTATION}\n\n```kotlin\nfun add(element: E): Boolean\n```\n",
        }
    }
    items = [
        {"label": "add", "labelDetails": {"detail": "(element: Int)"}, "kind": 2},
        {"label": "addAll", "labelDetails": {"detail": "(elements: Collection<Int>)"}, "kind": 2},
    ]
    resolved = {
        "label": "add",
        "detail": "fun add(element: Int): Boolean",
        "documentation": {"kind": "markdown", "value": ADD_DOCUMENTATION},
    }
    diagnostics = [
        {
            "range": _range(SAME_LINE, 19, 25),
            "severity": 1,
            "source": "Kotlin",
            "message": "Unresolved reference 'helper'.",
        },
        {
            "range": _range(SEEN_LINE, 12, 16),
            "severity": 2,
            "tags": [1],
            "source": "Kotlin",
            "message": "Variable 'seen' is never used",
        },
    ]
    return (
        {"reply": "initialize", "result": {"capabilities": CAPABILITIES}},
        {
            "answer": {
                "textDocument/definition": {"cases": definitions},
                "textDocument/hover": hover,
                "textDocument/completion": {"isIncomplete": True, "items": items},
                "completionItem/resolve": resolved,
            }
        },
        {"reply": "textDocument/diagnostic", "result": {"kind": "full", "items": []}},
        {"answer": {"textDocument/diagnostic": {"kind": "full", "items": diagnostics}}},
        {"send": request("kotlin-imported", "workspace/diagnostic/refresh")},
    )


def _location(uri: str, line: int) -> dict[str, object]:
    return {"uri": uri, "range": _range(line, 0, 1)}


@dataclass
class Seen:
    ready: str = ""
    opened_language: str = ""
    session_command: str = ""
    errors_underlined: int = -1
    error_markers: int = -1
    faded: str = ""
    hover_code: str = ""
    hover_text: str = ""
    same_file_line: str = ""
    library_note: str = ""
    completion_options: list[str] = field(default_factory=list[str])
    completion_info: str = ""
    accepted_line: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"kotlin-{engine}")
    on = Preferences(code_intelligence=True, autocomplete=True)
    with intelligence_lab(
        practice_workspace,
        base,
        script,
        files={SOURCE_FILE: STARTER},
        preferences=on,
        problems=[KOTLIN],
        jdk=25,
        kotlin_license=True,
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
        open_attempt(page, lab, SLUG)
        found.ready = wait_for_status(page, READY)
        _what_the_server_heard(lab, found)
        _diagnostics(page, found)
        _hover(page, found)
        _definitions(page, found)
        _completion(page, found)
        browser.close()
    return found


def _what_the_server_heard(lab: Lab, found: Seen) -> None:
    opened = next(m for m in lab.script.received() if m.get("method") == "textDocument/didOpen")
    found.opened_language = opened["params"]["textDocument"]["languageId"]
    calls = [call for call in lab.script.calls() if "intellij-server" in call["arguments"][0]]
    found.session_command = " ".join(calls[0]["arguments"])


def _diagnostics(page: Any, found: Seen) -> None:
    page.wait_for_selector(ERROR)
    found.errors_underlined = page.locator(ERROR).count()
    found.error_markers = page.locator(GUTTER_MARKER).count()
    page.wait_for_selector(UNNECESSARY)
    found.faded = page.locator(UNNECESSARY).first.inner_text()


def _hover(page: Any, found: Seen) -> None:
    point = point_at(page, SEEN_LINE, LINES[SEEN_LINE].index("Int") + 1)
    page.mouse.move(point["x"], point["y"])
    page.wait_for_selector(HOVER)
    found.hover_code = page.locator(f"{HOVER} pre").first.inner_text()
    found.hover_text = page.locator(f"{HOVER} p").first.inner_text()
    page.mouse.move(0, 0)
    page.keyboard.press("Escape")


def _click_with_the_key(page: Any, line: int, column: int) -> None:
    point = point_at(page, line, column)
    page.keyboard.down("ControlOrMeta")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("ControlOrMeta")


def _definitions(page: Any, found: Seen) -> None:
    _click_with_the_key(page, *HELPER)
    page.wait_for_function(
        "([selector, line]) => document.querySelector(selector)?.textContent === String(line)",
        arg=[CURSOR_LINE, HELPER_LINE + 1],
    )
    found.same_file_line = page.locator(CURSOR_LINE).inner_text()
    _click_with_the_key(page, *MUTABLE_LIST)
    page.wait_for_selector(NOTE)
    found.library_note = page.locator(NOTE).inner_text()
    page.keyboard.press("Shift")
    page.wait_for_selector(NOTE, state="detached")


def _completion(page: Any, found: Seen) -> None:
    point = point_at(page, SAME_LINE, len(LINES[SAME_LINE]) - 1)
    page.mouse.click(point["x"], point["y"])
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.keyboard.type("seen.")
    page.wait_for_selector(INFO)
    found.completion_options = page.locator(f"{LIST} li").all_inner_texts()
    found.completion_info = page.locator(INFO).inner_text()
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Enter")
    page.wait_for_selector(LIST, state="detached")
    found.accepted_line = page.locator(f"{EDITOR} .cm-line").nth(SAME_LINE + 1).inner_text()


def test_a_kotlin_file_opens_a_kotlin_lsp_session_that_becomes_ready(seen):
    assert seen.ready.startswith(READY)


def test_the_kotlin_lsp_opens_the_file_as_kotlin(seen):
    assert seen.opened_language == "kotlin"


def test_the_kotlin_lsp_runs_from_its_build_with_its_index_in_a_data_directory_of_the_root(seen):
    launcher, *options = seen.session_command.split(" ")
    assert (
        launcher.endswith("/kotlin-lsp/kotlin-server-263.7084.0/bin/intellij-server"),
        options[0],
    ) == (
        True,
        "--stdio",
    )


def test_the_index_is_in_the_first_data_directory_of_the_jvm_project(seen):
    assert seen.session_command.endswith("/.cs/lsp/kotlin-lsp-data/jvm/1/system")


def test_a_pulled_error_is_underlined_with_a_gutter_marker_once_the_server_asks_again(seen):
    assert (seen.errors_underlined, seen.error_markers) == (1, 1)


def test_an_unused_variable_is_faded(seen):
    assert seen.faded == "seen"


def test_hover_shows_the_declaration_as_code_and_the_kdoc_as_text(seen):
    assert (seen.hover_code, seen.hover_text) == ("fun add(element: E): Boolean", ADD_DOCUMENTATION)


def test_a_click_with_the_key_goes_to_a_definition_in_the_file(seen):
    assert seen.same_file_line == str(HELPER_LINE + 1)


def test_a_source_of_the_standard_library_gets_a_note_naming_its_jar_and_path(seen):
    assert (
        "kotlin-stdlib-2.4.21-sources.jar!/kotlin/collections/Collections.kt" in seen.library_note
    )


def test_completion_after_a_dot_lists_the_servers_items(seen):
    assert [option.split("\n")[0] for option in seen.completion_options][:2] == ["add", "addAll"]


def test_the_selected_items_documentation_shows_beside_the_list(seen):
    assert ADD_DOCUMENTATION in seen.completion_info


def test_accepting_an_item_inserts_its_name(seen):
    assert seen.accepted_line.strip() == "seen.add"


def test_there_is_no_console_error(seen):
    assert seen.errors == []


# The license not accepted


@dataclass
class Refused:
    segment: str
    sessions: int


@pytest.fixture(scope="module")
def without_the_license(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Refused:
    base = tmp_path_factory.mktemp(f"kotlin-unaccepted-{engine}")
    with (
        intelligence_lab(
            practice_workspace,
            base,
            script,
            files={SOURCE_FILE: STARTER},
            problems=[KOTLIN],
            jdk=25,
            kotlin_license=False,
        ) as running,
        sync_api.sync_playwright() as playwright,
    ):
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.goto(running.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        open_attempt(page, running, SLUG)
        segment = wait_for_status(page, NOT_ACCEPTED)
        browser.close()
        return Refused(segment, len(running.script.calls()))


def test_without_the_license_the_status_bar_says_it_is_not_accepted(without_the_license):
    assert without_the_license.segment.startswith(NOT_ACCEPTED)


def test_without_the_license_no_session_starts(without_the_license):
    assert without_the_license.sessions == 0
