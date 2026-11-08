"""Rust code intelligence in a real browser (docs/specs/web-ui.md#code-intelligence-in-the-editor,
ADR 0018 phase 3), in each engine of `tests/browsers.py`, against the scripted fake language server
playing rust-analyzer, which `cstudy serve` finds on PATH: a Rust file opens a session in `rust/`
that becomes ready. rust-analyzer answers for its own diagnostics, so the page pulls them
(`textDocument/diagnostic`) once the file opens and after each change, and publishes those of
`cargo check` after a save: the pulled error and the published unused variable, faded, show
together, and the server's refresh makes the page pull again, which replaces only the pulled ones.
Hover shows the documentation; Cmd-click (Ctrl-click off macOS) opens the standard library's source
in a read-only library tab; with `autocomplete` on, `.` lists the items with their resolved
documentation. With only rustup's proxy on PATH, the status bar and Settings say how to add it. No
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
from tests.language_server_scripts import fake_rustup_proxy, notification, request

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
RUST = ("two-sum", "rust")
SLUG = RUST[0]
SOURCE_FILE = "rust/practice/two_sum.rs"
STARTER = """pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let seen = nums.len();
    let top = sqrt(target);
    helper(top)
}

fn helper(value: i32) -> Vec<i32> {
    vec![value]
}
"""
LINES = STARTER.splitlines()
SEEN_LINE = 1
SQRT_LINE = 2
LAST_LINE = 7
LEN = (SEEN_LINE, LINES[SEEN_LINE].index("len") + 1)
SLICE_SOURCE = "\n".join(
    [
        "impl<T> [T] {",
        "    /// Returns the number of elements in the slice.",
        "    pub const fn len(&self) -> usize {",
        "        ptr::metadata(self)",
        "    }",
        "}",
    ]
)
LEN_DEFINITION_LINE = 2
LEN_DOCUMENTATION = "Returns the number of elements in the slice."
CAPABILITIES = {
    "textDocumentSync": {"openClose": True, "change": 2, "save": {}},
    "hoverProvider": True,
    "definitionProvider": True,
    "completionProvider": {"resolveProvider": True, "triggerCharacters": [":", ".", "'", "("]},
    "signatureHelpProvider": {"triggerCharacters": ["(", ",", "<"]},
    "diagnosticProvider": {
        "identifier": "rust-analyzer",
        "interFileDependencies": True,
        "workspaceDiagnostics": False,
    },
}
"""rust-analyzer's own: it declares a diagnostic provider whatever the client says."""
READY = "rust · rust-analyzer · ready"
PULLED = f"{READY} · 1 error"
PULLED_AND_PUBLISHED = f"{READY} · 1 error · 1 warning"
REFRESHED = f"{READY} · 1 warning"
REFRESH_GATE = "refresh"
ERROR = f"{PANEL} .cm-lintRange-error"
UNNECESSARY = f"{PANEL} .cstudy-unnecessary"
SAVED_TAB = f"{ACTIVE_TAB}:not(.is-modified)"
HOVER = ".cm-tooltip-hover .cs-hover"
LIST = ".cm-tooltip-autocomplete"
INFO = ".cm-completionInfo"
CURSOR_LINE = f"{PANEL} .cm-lineNumbers .cm-activeLineGutter"
INTERACTION_MS = 100
"""CodeMirror's `interactionDelay`, 75 ms, keeps a key pressed as the list appears from accepting
it, so Enter waits that long after the list shows."""


def _range(line: int, start: int, end: int) -> dict[str, object]:
    return {"start": {"line": line, "character": start}, "end": {"line": line, "character": end}}


def slice_source(base: Path) -> Path:
    """The standard library's source of `[T]::len`, outside the workspace, as rustup installs it."""
    return base / "sysroot" / "lib/rustlib/src/rust/library/core/src/slice/mod.rs"


def script(base: Path) -> Steps:
    """rust-analyzer's answers in its own shapes: its diagnostics answered on request, `cargo
    check`'s published after a save, then, once the test lets it, a refresh with the error fixed.
    Items carry no documentation until they are resolved."""
    mod_rs = slice_source(base).resolve().as_uri()
    native = {
        "range": _range(SQRT_LINE, 14, 18),
        "severity": 1,
        "source": "rust-analyzer",
        "code": "E0425",
        "message": "cannot find function `sqrt` in this scope",
    }
    unused = {
        "range": _range(SEEN_LINE, 8, 12),
        "severity": 2,
        "tags": [1],
        "source": "rustc",
        "code": "unused_variables",
        "message": "unused variable: `seen`",
    }
    hover = {
        "contents": {
            "kind": "markdown",
            "value": (
                "```rust\ncore::slice\n```\n\n```rust\npub const fn len(&self) -> usize\n```\n\n"
                f"---\n\n{LEN_DOCUMENTATION}\n"
            ),
        }
    }
    definition = [{"uri": mod_rs, "range": _range(LEN_DEFINITION_LINE, 17, 20)}]
    items = [{"label": "len()", "kind": 2}, {"label": "to_vec()", "kind": 2}]
    resolved = {
        "label": "len()",
        "detail": "pub const fn len(&self) -> usize",
        "documentation": {"kind": "markdown", "value": LEN_DOCUMENTATION},
    }
    published = {"uri": "$uri", "diagnostics": [unused]}
    return (
        {"reply": "initialize", "result": {"capabilities": CAPABILITIES}},
        {
            "answer": {
                "textDocument/diagnostic": {"kind": "full", "items": [native]},
                "textDocument/hover": hover,
                "textDocument/definition": definition,
                "textDocument/completion": {"isIncomplete": True, "items": items},
                "completionItem/resolve": resolved,
            }
        },
        {"await": "textDocument/didSave"},
        {"send": notification("textDocument/publishDiagnostics", published)},
        {"wait_for": str(base / REFRESH_GATE)},
        {"answer": {"textDocument/diagnostic": {"kind": "full", "items": []}}},
        {"send": request("ra-refresh", "workspace/diagnostic/refresh")},
    )


@dataclass
class Seen:
    ready: str = ""
    opened_language: str = ""
    session_command: str = ""
    session_directory: str = ""
    pulls: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    pulled: str = ""
    pulled_error: str = ""
    pulled_and_published: str = ""
    faded: str = ""
    refreshed: str = ""
    errors_after_refresh: int = -1
    faded_after_refresh: str = ""
    hover_code: str = ""
    hover_text: str = ""
    library_tab_path: str = ""
    library_badge: str = ""
    library_line: str = ""
    completion_labels: list[str] = field(default_factory=list[str])
    completion_info: str = ""
    accepted_line: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"rust-{engine}")
    source = slice_source(base)
    source.parent.mkdir(parents=True)
    source.write_text(SLICE_SOURCE)
    on = Preferences(code_intelligence=True, autocomplete=True)
    with intelligence_lab(
        practice_workspace,
        base,
        script(base),
        files={SOURCE_FILE: STARTER},
        preferences=on,
        problems=[RUST],
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
        _pulled_and_published(page, lab, found)
        _hover_and_definition(page, found)
        _completion(page, found)
        browser.close()
    return found


def _what_the_server_heard(lab: Lab, found: Seen) -> None:
    opened = next(m for m in lab.script.received() if m.get("method") == "textDocument/didOpen")
    found.opened_language = opened["params"]["textDocument"]["languageId"]
    call = lab.script.calls()[0]
    found.session_command = " ".join(call["arguments"])
    found.session_directory = call["cwd"]


def _pulled_and_published(page: Any, lab: Lab, found: Seen) -> None:
    found.pulled = wait_for_status(page, PULLED)
    found.pulled_error = page.locator(ERROR).first.inner_text()
    found.pulls = [
        message["params"]
        for message in lab.script.received()
        if message.get("method") == "textDocument/diagnostic"
    ]
    point = point_at(page, LAST_LINE, len(LINES[LAST_LINE]) - 1)
    page.mouse.click(point["x"], point["y"])
    page.keyboard.press("End")
    page.keyboard.type(" ")
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(SAVED_TAB)
    found.pulled_and_published = wait_for_status(page, PULLED_AND_PUBLISHED)
    found.faded = page.locator(UNNECESSARY).first.inner_text()
    lab.script.gate(REFRESH_GATE).touch()
    found.refreshed = wait_for_status(page, REFRESHED)
    found.errors_after_refresh = page.locator(ERROR).count()
    found.faded_after_refresh = page.locator(UNNECESSARY).first.inner_text()


def _hover_and_definition(page: Any, found: Seen) -> None:
    point = point_at(page, *LEN)
    page.mouse.move(point["x"], point["y"])
    page.wait_for_selector(HOVER)
    found.hover_code = page.locator(f"{HOVER} pre").nth(1).inner_text()
    found.hover_text = page.locator(f"{HOVER} p").first.inner_text()
    page.mouse.move(0, 0)
    page.keyboard.press("Escape")
    page.keyboard.down("ControlOrMeta")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("ControlOrMeta")
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    found.library_tab_path = page.get_attribute(ACTIVE_TAB, "title")
    found.library_badge = page.locator(f"{ACTIVE_TAB} .badge").inner_text()
    page.wait_for_function(
        "([selector, line]) => document.querySelector(selector)?.textContent === String(line)",
        arg=[CURSOR_LINE, LEN_DEFINITION_LINE + 1],
    )
    found.library_line = page.locator(CURSOR_LINE).inner_text()
    page.keyboard.press("Control+Minus")
    page.wait_for_function(
        "selector => document.querySelector(selector)?.title === 'two_sum.rs'", arg=ACTIVE_TAB
    )
    wait_for_status(page, READY)


def _completion(page: Any, found: Seen) -> None:
    point = point_at(page, SEEN_LINE, len(LINES[SEEN_LINE]) - 1)
    page.mouse.click(point["x"], point["y"])
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.keyboard.type("let count = nums.")
    page.wait_for_selector(INFO)
    found.completion_labels = page.locator(f"{LIST} li .cm-completionLabel").all_inner_texts()
    found.completion_info = page.locator(INFO).inner_text()
    page.wait_for_timeout(INTERACTION_MS)
    page.keyboard.press("Enter")
    page.wait_for_selector(LIST, state="detached")
    found.accepted_line = page.locator(f"{EDITOR} .cm-line").nth(SEEN_LINE + 1).inner_text()


def test_a_rust_file_opens_a_rust_analyzer_session_that_becomes_ready(seen):
    assert seen.ready.startswith(READY)


def test_rust_analyzer_opens_the_file_as_rust(seen):
    assert seen.opened_language == "rust"


def test_rust_analyzer_runs_from_path(seen):
    assert seen.session_command.endswith("/rust-analyzer")


def test_rust_analyzer_runs_in_the_rust_project(seen, lab):
    assert Path(seen.session_directory) == (lab.workspace / "rust").resolve()


def test_the_page_pulls_the_diagnostics_of_the_file_it_opened_naming_the_provider(seen, lab):
    uri = (lab.workspace / SOURCE_FILE).resolve().as_uri()
    assert seen.pulls[0] == {"textDocument": {"uri": uri}, "identifier": "rust-analyzer"}


def test_a_pulled_error_is_underlined_and_counted(seen):
    assert (seen.pulled, seen.pulled_error) == (PULLED, "sqrt")


def test_cargo_checks_published_warning_shows_beside_the_pulled_error(seen):
    assert seen.pulled_and_published == PULLED_AND_PUBLISHED


def test_cargo_checks_unused_variable_is_faded(seen):
    assert seen.faded == "seen"


def test_a_refresh_pulls_again_and_replaces_only_the_pulled_diagnostics(seen):
    assert (seen.refreshed, seen.errors_after_refresh, seen.faded_after_refresh) == (
        REFRESHED,
        0,
        "seen",
    )


def test_hover_shows_the_signature_as_code_and_the_documentation_as_text(seen):
    assert (seen.hover_code.strip(), seen.hover_text.strip()) == (
        "pub const fn len(&self) -> usize",
        LEN_DOCUMENTATION,
    )


def test_the_standard_library_opens_in_a_read_only_library_tab_at_the_definition(seen, lab):
    path = slice_source(lab.path.parent).resolve()
    assert (seen.library_tab_path, seen.library_badge, seen.library_line) == (
        str(path),
        "library",
        str(LEN_DEFINITION_LINE + 1),
    )


def test_completion_after_a_dot_lists_the_servers_items(seen):
    assert seen.completion_labels[:2] == ["len()", "to_vec()"]


def test_the_selected_items_resolved_documentation_shows_beside_the_list(seen):
    assert LEN_DOCUMENTATION in seen.completion_info


def test_accepting_an_item_inserts_its_label(seen):
    assert seen.accepted_line.strip() == "let count = nums.len()"


def test_there_is_no_console_error(seen):
    assert seen.errors == []


# with only rustup's proxy on PATH


@dataclass
class Unusable:
    segment: str
    settings_row: str
    sessions: int


@pytest.fixture(scope="module")
def behind_the_proxy(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Unusable]:
    base = tmp_path_factory.mktemp(f"rust-proxy-{engine}")
    steps = ({"reply": "initialize", "result": {"capabilities": CAPABILITIES}},)
    with intelligence_lab(
        practice_workspace, base, steps, problems=[RUST], go_and_rust=True
    ) as running:
        fake_rustup_proxy(running.path)
        with sync_api.sync_playwright() as playwright:
            browser = launched(playwright, engine)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(WAIT_MS)
            page.goto(running.server.login_url)
            page.wait_for_selector("table.problems tbody tr")
            open_attempt(page, running, SLUG)
            segment = wait_for_status(page, "no code intelligence for Rust")
            page.evaluate("location.hash = '#/settings'")
            page.wait_for_selector("ul.languages li a")
            rows = page.locator("ul.languages li").all_inner_texts()
            browser.close()
        rust_row = next(row.replace("\n", " ") for row in rows if row.startswith("Rust"))
        yield Unusable(segment, rust_row, len(running.script.calls()))


def test_behind_the_proxy_the_status_bar_says_rust_analyzer_is_not_installed(behind_the_proxy):
    assert behind_the_proxy.segment == (
        "no code intelligence for Rust: rust-analyzer is not installed · Health"
    )


def test_behind_the_proxy_settings_says_how_to_add_rust_analyzer(behind_the_proxy):
    assert behind_the_proxy.settings_row == (
        "Rust not installed: run rustup component add rust-analyzer"
    )


def test_behind_the_proxy_no_session_starts(behind_the_proxy):
    assert behind_the_proxy.sessions == 0
