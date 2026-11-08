"""Java code intelligence in a real browser (docs/specs/web-ui.md#code-intelligence-in-the-
editor, ADR 0018 phase 2), in each engine of `tests/browsers.py`, against the scripted fake
language server playing JDT LS, which `cstudy serve` starts as the `java` of the selected JDK 25:
a Java file opens a session that becomes ready; a live error is underlined with a gutter marker and
unused code is faded; hover shows the documentation JDT LS sends as code and text; Cmd-click (Ctrl-
click off macOS) moves the cursor within the file, opens the runner's support code in a read-only
library tab, and names a class of the JDK in a note, since JDT LS names it by a `jdt://` URI; with
`autocomplete` on, `.` lists the server's items with the resolved documentation beside them. On a
JDK that JDT LS cannot run on, and without JDT LS, the status bar says why. No console error.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import shutil
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
    Lab,
    Steps,
    intelligence_lab,
    open_attempt,
    point_at,
    wait_for_status,
)
from tests.language_server_scripts import notification

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
JAVA = ("two-sum", "java")
SLUG = JAVA[0]
SOURCE_FILE = "jvm/java/src/main/java/practice/two_sum/Solution.java"
SUPPORT_FILE = ".cs/runtime/runners/jvm/support/src/main/java/cs/support/Support.java"
STARTER = """package practice.two_sum;

import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        List<Integer> seen = new ArrayList<>();
        int same = helper();
        Support.run();
        return null;
    }

    int helper() { return 0; }
}
"""
SUPPORT = """package cs.support;

public final class Support {
    public static void run() {}
}
"""
LINES = STARTER.splitlines()
SEEN_LINE = 6
SAME_LINE = 7
SUPPORT_LINE = 8
HELPER_LINE = 12
ARRAY_LIST = (SEEN_LINE, LINES[SEEN_LINE].index("ArrayList") + 2)
HELPER = (SAME_LINE, LINES[SAME_LINE].index("helper") + 2)
SUPPORT_CALL = (SUPPORT_LINE, LINES[SUPPORT_LINE].index("Support") + 2)
ADD_DOCUMENTATION = "Appends the specified element to the end of this list."
JDT_ARRAY_LIST = (
    "jdt://contents/java.base/java.util/ArrayList.java?=two_sum/%5C/jdk%5C/lib%5C/jrt-fs.jar"
    "%60java.base=/javadoc_location=/https:%5C/%5C/docs.oracle.com%5C/=/%3Cjava.util%28ArrayList.class"
)
CAPABILITIES = {
    "textDocumentSync": 2,
    "hoverProvider": True,
    "definitionProvider": True,
    "completionProvider": {"resolveProvider": True, "triggerCharacters": ["."]},
    "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
}
READY = "java · jdtls · ready"
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


def _location(uri: str, line: int) -> dict[str, object]:
    return {"uri": uri, "range": _range(line, 0, 1)}


def script(workspace: Path) -> Steps:
    """JDT LS's answers in their own shapes: a hover of marked strings, a `jdt://` class, items
    named as JDT LS names them, with the parameters and the type as label details."""
    support = (workspace / SUPPORT_FILE).as_uri()
    definitions = [
        {"when": {"position": {"line": SAME_LINE}}, "result": [_location("$uri", HELPER_LINE)]},
        {"when": {"position": {"line": SEEN_LINE}}, "result": [_location(JDT_ARRAY_LIST, 168)]},
        {"when": {"position": {"line": SUPPORT_LINE}}, "result": [_location(support, 3)]},
    ]
    hover = {
        "contents": [
            {"language": "java", "value": "boolean java.util.List.add(Integer e)"},
            ADD_DOCUMENTATION,
        ]
    }
    items = [
        {
            "label": "max",
            "labelDetails": {"detail": "(int a, int b)", "description": "int"},
            "kind": 2,
        },
        {
            "label": "min",
            "labelDetails": {"detail": "(int a, int b)", "description": "int"},
            "kind": 2,
        },
    ]
    resolved = {
        "label": "max",
        "detail": "int java.lang.Math.max(int a, int b)",
        "documentation": {"kind": "markdown", "value": "Returns the greater of two `int` values."},
    }
    diagnostics = [
        {
            "range": _range(SUPPORT_LINE, 8, 15),
            "severity": 1,
            "source": "Java",
            "code": "570425394",
            "message": "Support cannot be resolved",
        },
        {
            "range": _range(SEEN_LINE, 22, 26),
            "severity": 2,
            "tags": [1],
            "source": "Java",
            "code": "536870973",
            "message": "The value of the local variable seen is not used",
        },
    ]
    published = {"uri": "$uri", "diagnostics": diagnostics}
    return (
        {"reply": "initialize", "result": {"capabilities": CAPABILITIES}},
        {
            "answer": {
                "textDocument/definition": {"cases": definitions},
                "textDocument/hover": hover,
                "textDocument/completion": {"isIncomplete": False, "items": items},
                "completionItem/resolve": resolved,
            }
        },
        {"await": "textDocument/didOpen"},
        {"send": notification("textDocument/publishDiagnostics", published)},
    )


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
    library_tab_path: str = ""
    library_badge: str = ""
    jdk_class_note: str = ""
    completion_options: list[str] = field(default_factory=list[str])
    completion_info: str = ""
    accepted_line: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"java-{engine}")
    files = {SOURCE_FILE: STARTER, SUPPORT_FILE: SUPPORT}
    on = Preferences(code_intelligence=True, autocomplete=True)
    with intelligence_lab(
        practice_workspace, base, script, files=files, preferences=on, problems=[JAVA], jdk=25
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
    found.session_command = " ".join(lab.script.calls()[0]["arguments"])


def _diagnostics(page: Any, found: Seen) -> None:
    page.wait_for_selector(ERROR)
    found.errors_underlined = page.locator(ERROR).count()
    found.error_markers = page.locator(GUTTER_MARKER).count()
    page.wait_for_selector(UNNECESSARY)
    found.faded = page.locator(UNNECESSARY).first.inner_text()


def _hover(page: Any, found: Seen) -> None:
    point = point_at(page, SEEN_LINE, LINES[SEEN_LINE].index("List") + 1)
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
    _click_with_the_key(page, *ARRAY_LIST)
    page.wait_for_selector(NOTE)
    found.jdk_class_note = page.locator(NOTE).inner_text()
    page.keyboard.press("Shift")
    page.wait_for_selector(NOTE, state="detached")
    _click_with_the_key(page, *SUPPORT_CALL)
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    found.library_tab_path = page.get_attribute(ACTIVE_TAB, "title")
    found.library_badge = page.locator(f"{ACTIVE_TAB} .badge").inner_text()
    page.keyboard.press("Control+Minus")
    page.wait_for_function(
        "selector => document.querySelector(selector)?.title === 'Solution.java'", arg=ACTIVE_TAB
    )
    wait_for_status(page, READY)


def _completion(page: Any, found: Seen) -> None:
    point = point_at(page, HELPER_LINE, len(LINES[HELPER_LINE]) - 1)
    page.mouse.click(point["x"], point["y"])
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.keyboard.type("int top = Math.")
    page.wait_for_selector(INFO)
    found.completion_options = page.locator(f"{LIST} li").all_inner_texts()
    found.completion_info = page.locator(INFO).inner_text()
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Enter")
    page.wait_for_selector(LIST, state="detached")
    found.accepted_line = page.locator(f"{EDITOR} .cm-line").nth(HELPER_LINE + 1).inner_text()


def test_a_java_file_opens_a_jdtls_session_that_becomes_ready(seen):
    """Ready, followed by the counts once the server has published."""
    assert seen.ready.startswith(READY)


def test_jdtls_opens_the_file_as_java(seen):
    assert seen.opened_language == "java"


def test_jdtls_runs_on_the_selected_jdk_from_its_milestone_in_lsp(seen):
    assert ".cs/lsp/jdtls/plugins/org.eclipse.equinox.launcher_" in seen.session_command


def test_jdtls_keeps_its_workspace_in_a_data_directory_of_the_root(seen):
    assert "/.cs/lsp/jdtls-data/jvm/1/workspace" in seen.session_command


def test_a_live_error_is_underlined_with_a_gutter_marker(seen):
    assert (seen.errors_underlined, seen.error_markers) == (1, 1)


def test_an_unused_variable_is_faded(seen):
    assert seen.faded == "seen"


def test_hover_shows_the_signature_as_code_and_the_documentation_as_text(seen):
    assert (seen.hover_code.strip(), seen.hover_text.strip()) == (
        "boolean java.util.List.add(Integer e)",
        ADD_DOCUMENTATION,
    )


def test_a_click_with_the_key_goes_to_a_definition_in_the_file(seen):
    assert seen.same_file_line == str(HELPER_LINE + 1)


def test_the_runners_support_code_opens_in_a_read_only_library_tab(seen):
    assert (seen.library_tab_path, seen.library_badge) == (SUPPORT_FILE, "library")


def test_a_class_of_the_jdk_gets_a_note_naming_its_module_package_file_and_line(seen):
    assert seen.jdk_class_note == "java.base/java.util/ArrayList.java:169 · not a file: URI"


def test_completion_after_a_dot_lists_the_servers_items_with_their_parameters(seen):
    labels = [option.split("\n")[0] for option in seen.completion_options[:2]]
    assert [label[: len("max(int a, int b)")] for label in labels] == [
        "max(int a, int b)",
        "min(int a, int b)",
    ]


def test_the_selected_items_documentation_shows_beside_the_list(seen):
    assert "Returns the greater of two int values." in seen.completion_info


def test_accepting_an_item_inserts_its_name(seen):
    assert seen.accepted_line.strip() == "int top = Math.max"


def test_there_is_no_console_error(seen):
    assert seen.errors == []


# without a usable server


def _segment_of(engine: str, lab: Lab) -> str:
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.goto(lab.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        open_attempt(page, lab, SLUG)
        segment = wait_for_status(page, "no code intelligence for Java")
        browser.close()
    return segment


@dataclass
class Unusable:
    segment: str
    sessions: int


@pytest.fixture(scope="module")
def on_jdk_21(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Unusable]:
    base = tmp_path_factory.mktemp(f"java-jdk-21-{engine}")
    steps = ({"reply": "initialize", "result": {"capabilities": CAPABILITIES}},)
    with intelligence_lab(practice_workspace, base, steps, problems=[JAVA], jdk=21) as running:
        yield Unusable(_segment_of(engine, running), len(running.script.calls()))


@pytest.fixture(scope="module")
def without_jdtls(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Unusable]:
    """JDK 25 is selected, but `.cs/lsp/` holds no JDT LS."""
    base = tmp_path_factory.mktemp(f"java-missing-{engine}")
    steps = ({"reply": "initialize", "result": {"capabilities": CAPABILITIES}},)
    with intelligence_lab(practice_workspace, base, steps, problems=[JAVA], jdk=25) as running:
        shutil.rmtree(running.workspace / ".cs" / "lsp" / "jdtls")
        yield Unusable(_segment_of(engine, running), len(running.script.calls()))


def test_on_a_jdk_jdtls_cannot_run_on_the_status_bar_names_the_jdks_it_needs(on_jdk_21):
    assert on_jdk_21.segment == "no code intelligence for Java: needs JDK 25 or 26 · Health"


def test_on_a_jdk_jdtls_cannot_run_on_no_session_starts(on_jdk_21):
    assert on_jdk_21.sessions == 0


def test_without_jdtls_the_status_bar_says_it_is_not_installed(without_jdtls):
    assert without_jdtls.segment == (
        "no code intelligence for Java: jdtls is not installed · Health"
    )


def test_without_jdtls_no_session_starts(without_jdtls):
    assert without_jdtls.sessions == 0
