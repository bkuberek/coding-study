"""Go code intelligence in a real browser (docs/specs/web-ui.md#code-intelligence-in-the-editor,
ADR 0018 phase 3), in each engine of `tests/browsers.py`, against the scripted fake language server
playing gopls, which `cstudy serve` starts as `.cs/lsp/bin/gopls`, where `cstudy doctor --fix`
builds it: a Go file opens a session in `go/` that becomes ready; live errors are underlined with
gutter markers and the unused variable is faded; hover shows the signature as code and the
documentation as text, and its `file:` link into GOROOT is a button that opens the library tab at
the line it names; Cmd-click (Ctrl-click off macOS) moves the cursor within the file and opens
GOROOT's source in a read-only library tab; with `autocomplete` on, `.` lists gopls's items with
the documentation they carry beside them. Without gopls the status bar says so. No console error.

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
GO = ("two-sum", "go")
SLUG = GO[0]
SOURCE_FILE = "go/practice/two_sum/two_sum.go"
STARTER = """package two_sum

import "strings"

func TwoSum(nums []int, target int) []int {
\tvar unused int
\tparts := strings.Split("a b", " ")
\treturn helper(sqrt(len(parts)))
}

func helper(value int) []int { return []int{value} }
"""
LINES = STARTER.splitlines()
UNUSED_LINE = 5
SPLIT_LINE = 6
RETURN_LINE = 7
HELPER_LINE = 10
SPLIT = (SPLIT_LINE, LINES[SPLIT_LINE].index("Split") + 2)
HELPER = (RETURN_LINE, LINES[RETURN_LINE].index("helper") + 2)
GOROOT_STRINGS = """package strings

// Cut slices s around the first instance of sep.
func Cut(s, sep string) (before, after string, found bool) { return }

// Split slices s into all substrings separated by sep.
func Split(s, sep string) []string { return nil }
"""
CUT_LINE = 4
"""1-based: where gopls's link to `Cut` points, `#4,6`."""
SPLIT_DEFINITION_LINE = 6
"""0-based: where the definition of `Split` starts."""
SPLIT_SIGNATURE = "func strings.Split(s string, sep string) []string"
SPLIT_DOCUMENTATION = "Split slices s into all substrings separated by sep."
CAPABILITIES = {
    "textDocumentSync": {"openClose": True, "change": 2, "save": {}},
    "hoverProvider": True,
    "definitionProvider": True,
    "completionProvider": {"triggerCharacters": ["."]},
    "signatureHelpProvider": {"triggerCharacters": ["(", ","], "retriggerCharacters": [")"]},
}
"""gopls's own: its items carry their documentation, so it declares no `resolveProvider`."""
READY = "go · gopls · ready"
ERROR = f"{PANEL} .cm-lintRange-error"
GUTTER_MARKER = f"{PANEL} .cm-lint-marker-error"
UNNECESSARY = f"{PANEL} .cstudy-unnecessary"
HOVER = ".cm-tooltip-hover .cs-hover"
LIBRARY_LINK = f"{HOVER} button.cs-library-link"
LIST = ".cm-tooltip-autocomplete"
INFO = ".cm-completionInfo"
CURSOR_LINE = f"{PANEL} .cm-lineNumbers .cm-activeLineGutter"
INTERACTION_MS = 100
"""CodeMirror's `interactionDelay`, 75 ms, keeps a key pressed as the list appears from accepting
it, so Enter waits that long after the list shows."""


def _range(line: int, start: int, end: int) -> dict[str, object]:
    return {"start": {"line": line, "character": start}, "end": {"line": line, "character": end}}


def goroot_strings(base: Path) -> Path:
    """The source of `strings` in a GOROOT outside the workspace, as gopls names it."""
    return base / "goroot" / "src" / "strings" / "strings.go"


def script(base: Path, workspace: Path) -> Steps:
    """gopls's answers in its own shapes: a hover of markdown whose doc link is a `file:` URI with
    a 1-based line and column, unused names as errors tagged Unnecessary, and items that carry
    their documentation."""
    strings_go = goroot_strings(base).resolve().as_uri()
    definitions = [
        {
            "when": {"position": {"line": RETURN_LINE}},
            "result": [{"uri": "$uri", "range": _range(HELPER_LINE, 5, 11)}],
        },
        {
            "when": {"position": {"line": SPLIT_LINE}},
            "result": [{"uri": strings_go, "range": _range(SPLIT_DEFINITION_LINE, 5, 10)}],
        },
    ]
    hover = {
        "contents": {
            "kind": "markdown",
            "value": (
                f"```go\n{SPLIT_SIGNATURE}\n```\n\n---\n\n{SPLIT_DOCUMENTATION}\n\n"
                f"To split around the first instance of a separator, see "
                f"[Cut]({strings_go}#{CUT_LINE},6).\n"
            ),
        }
    }
    items = [
        {
            "label": "Cut",
            "kind": 3,
            "detail": "func(s string, sep string) (before string, after string, found bool)",
            "documentation": {
                "kind": "markdown",
                "value": "Cut slices s around the first instance of sep.",
            },
        },
        {
            "label": "Split",
            "kind": 3,
            "detail": "func(s string, sep string) []string",
            "documentation": {"kind": "markdown", "value": SPLIT_DOCUMENTATION},
        },
    ]
    diagnostics = [
        {
            "range": _range(RETURN_LINE, 15, 19),
            "severity": 1,
            "source": "compiler",
            "code": "UndeclaredName",
            "message": "undefined: sqrt",
        },
        {
            "range": _range(UNUSED_LINE, 5, 11),
            "severity": 1,
            "tags": [1],
            "source": "compiler",
            "code": "UnusedVar",
            "message": "declared and not used: unused",
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
    session_directory: str = ""
    errors_underlined: int = -1
    error_markers: int = -1
    faded: str = ""
    same_file_line: str = ""
    library_tab_path: str = ""
    library_badge: str = ""
    library_line: str = ""
    hover_code: str = ""
    hover_text: str = ""
    link_text: str = ""
    linked_tab_path: str = ""
    linked_line: str = ""
    completion_labels: list[str] = field(default_factory=list[str])
    completion_info: str = ""
    accepted_line: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"go-{engine}")
    goroot = goroot_strings(base)
    goroot.parent.mkdir(parents=True)
    goroot.write_text(GOROOT_STRINGS)
    on = Preferences(code_intelligence=True, autocomplete=True)
    with intelligence_lab(
        practice_workspace,
        base,
        lambda workspace: script(base, workspace),
        files={SOURCE_FILE: STARTER},
        preferences=on,
        problems=[GO],
        go_and_rust=True,
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
        _definitions(page, found)
        _hover_and_its_link(page, found)
        _completion(page, found)
        browser.close()
    return found


def _what_the_server_heard(lab: Lab, found: Seen) -> None:
    opened = next(m for m in lab.script.received() if m.get("method") == "textDocument/didOpen")
    found.opened_language = opened["params"]["textDocument"]["languageId"]
    call = lab.script.calls()[0]
    found.session_command = " ".join(call["arguments"])
    found.session_directory = call["cwd"]


def _diagnostics(page: Any, found: Seen) -> None:
    page.wait_for_selector(UNNECESSARY)
    found.errors_underlined = page.locator(ERROR).count()
    found.error_markers = page.locator(GUTTER_MARKER).count()
    found.faded = page.locator(UNNECESSARY).first.inner_text()


def _click_with_the_key(page: Any, line: int, column: int) -> None:
    point = point_at(page, line, column)
    page.keyboard.down("ControlOrMeta")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("ControlOrMeta")


def _back_to_the_file(page: Any) -> None:
    page.keyboard.press("Control+Minus")
    page.wait_for_function(
        "selector => document.querySelector(selector)?.title === 'two_sum.go'", arg=ACTIVE_TAB
    )
    wait_for_status(page, READY)


def _cursor_on_line(page: Any, line: int) -> str:
    page.wait_for_function(
        "([selector, line]) => document.querySelector(selector)?.textContent === String(line)",
        arg=[CURSOR_LINE, line],
    )
    return page.locator(CURSOR_LINE).inner_text()


def _definitions(page: Any, found: Seen) -> None:
    _click_with_the_key(page, *HELPER)
    found.same_file_line = _cursor_on_line(page, HELPER_LINE + 1)
    _click_with_the_key(page, *SPLIT)
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    found.library_tab_path = page.get_attribute(ACTIVE_TAB, "title")
    found.library_badge = page.locator(f"{ACTIVE_TAB} .badge").inner_text()
    found.library_line = _cursor_on_line(page, SPLIT_DEFINITION_LINE + 1)
    _back_to_the_file(page)


def _hover_and_its_link(page: Any, found: Seen) -> None:
    point = point_at(page, *SPLIT)
    page.mouse.move(point["x"], point["y"])
    page.wait_for_selector(LIBRARY_LINK)
    found.hover_code = page.locator(f"{HOVER} pre").first.inner_text()
    found.hover_text = page.locator(f"{HOVER} p").first.inner_text()
    found.link_text = page.locator(LIBRARY_LINK).inner_text()
    page.click(LIBRARY_LINK)
    page.wait_for_selector(HOVER, state="detached")
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    found.linked_tab_path = page.get_attribute(ACTIVE_TAB, "title")
    found.linked_line = _cursor_on_line(page, CUT_LINE)
    page.mouse.move(0, 0)
    _back_to_the_file(page)


def _completion(page: Any, found: Seen) -> None:
    point = point_at(page, HELPER_LINE, len(LINES[HELPER_LINE]) - 1)
    page.mouse.click(point["x"], point["y"])
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.keyboard.type("var cut = strings.")
    page.wait_for_selector(INFO)
    found.completion_labels = page.locator(f"{LIST} li .cm-completionLabel").all_inner_texts()
    found.completion_info = page.locator(INFO).inner_text()
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Enter")
    page.wait_for_selector(LIST, state="detached")
    found.accepted_line = page.locator(f"{EDITOR} .cm-line").nth(HELPER_LINE + 1).inner_text()


def test_a_go_file_opens_a_gopls_session_that_becomes_ready(seen):
    """Ready, followed by the counts once the server has published."""
    assert seen.ready.startswith(READY)


def test_gopls_opens_the_file_as_go(seen):
    assert seen.opened_language == "go"


def test_gopls_runs_from_the_lsp_bin_directory_where_go_install_put_it(seen):
    assert seen.session_command.endswith("/.cs/lsp/bin/gopls")


def test_gopls_runs_in_the_go_project(seen, lab):
    assert Path(seen.session_directory) == (lab.workspace / "go").resolve()


def test_live_errors_are_underlined_with_gutter_markers(seen):
    """gopls reports the unused variable as an error too, tagged Unnecessary."""
    assert (seen.errors_underlined, seen.error_markers) == (2, 2)


def test_the_unused_variable_is_faded(seen):
    assert seen.faded == "unused"


def test_a_click_with_the_key_goes_to_a_definition_in_the_file(seen):
    assert seen.same_file_line == str(HELPER_LINE + 1)


def test_goroot_opens_in_a_read_only_library_tab_at_the_definition(seen, lab):
    path = goroot_strings(lab.path.parent).resolve()
    assert (seen.library_tab_path, seen.library_badge, seen.library_line) == (
        str(path),
        "library",
        str(SPLIT_DEFINITION_LINE + 1),
    )


def test_hover_shows_the_signature_as_code_and_the_documentation_as_text(seen):
    assert (seen.hover_code.strip(), seen.hover_text.strip()) == (
        SPLIT_SIGNATURE,
        SPLIT_DOCUMENTATION,
    )


def test_the_documentation_link_into_goroot_is_a_button_named_by_its_text(seen):
    assert seen.link_text == "Cut"


def test_the_documentation_link_opens_the_library_tab_at_the_line_it_names(seen, lab):
    path = goroot_strings(lab.path.parent).resolve()
    assert (seen.linked_tab_path, seen.linked_line) == (str(path), str(CUT_LINE))


def test_completion_after_a_dot_lists_the_items_gopls_sent(seen):
    assert seen.completion_labels == ["Cut", "Split"]


def test_the_documentation_the_items_carry_shows_beside_the_list(seen):
    assert "Cut slices s around the first instance of sep." in seen.completion_info


def test_accepting_an_item_inserts_its_name(seen):
    assert seen.accepted_line.strip() == "var cut = strings.Cut"


def test_there_is_no_console_error(seen):
    assert seen.errors == []


# without gopls


@dataclass
class Unusable:
    segment: str
    sessions: int


@pytest.fixture(scope="module")
def without_gopls(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Unusable]:
    base = tmp_path_factory.mktemp(f"go-missing-{engine}")
    steps = ({"reply": "initialize", "result": {"capabilities": CAPABILITIES}},)
    with intelligence_lab(
        practice_workspace, base, steps, problems=[GO], go_and_rust=True
    ) as running:
        (running.workspace / ".cs" / "lsp" / "bin" / "gopls").unlink()
        with sync_api.sync_playwright() as playwright:
            browser = launched(playwright, engine)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(WAIT_MS)
            page.goto(running.server.login_url)
            page.wait_for_selector("table.problems tbody tr")
            open_attempt(page, running, SLUG)
            segment = wait_for_status(page, "no code intelligence for Go")
            browser.close()
        yield Unusable(segment, len(running.script.calls()))


def test_without_gopls_the_status_bar_says_it_is_not_installed(without_gopls):
    assert without_gopls.segment == "no code intelligence for Go: gopls is not installed · Health"


def test_without_gopls_no_session_starts(without_gopls):
    assert without_gopls.sessions == 0
