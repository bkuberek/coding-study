"""The code-intelligence client in a real browser
(docs/specs/web-ui.md#code-intelligence-in-the-editor), in each engine of `tests/browsers.py`,
against a real `cstudy serve` whose language server is the scripted fake
(`tests/fake_language_server.py`) behind a `node` on `PATH`: a Python file opens a session that
becomes ready; the server hears `initialize`, `didOpen` with the tab's text, `didChange` after
typing, `didSave` after a save and `didClose` after the tab closes; a second visible tab holds a
session of its own and still saves; a TypeScript file whose server is not installed and a Kotlin
file say so in the status bar; a server that exits stops the session with Restart, which opens it
again; the Settings view lists each language; the Health view shows the `code intelligence` rows;
and turning the preference off closes the session. No console error and no Content Security
Policy violation.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.domain.preferences import Preferences, preferences_document
from tests.browsers import launched, save_preferences, watched
from tests.language_server_scripts import ScriptedServer, fake_node, install_fake_basedpyright
from tests.scripted_runs import eventually
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
SEGMENT = ".statusbar .code-intelligence"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
EDITOR = ".panel:not([hidden]) .cm-content"
SAVED_TAB = f"{ACTIVE_TAB}:not(.is-modified)"
PYTHON = ("two-sum", "python")
TYPESCRIPT = ("lru-cache", "typescript")
KOTLIN = ("invert-binary-tree", "kotlin")
ROOT = Path("python") / "practice"
"""The tree's root for a single-file Python attempt; the server's own root is `python/`."""
CAPABILITIES = {"capabilities": {"textDocumentSync": 2}}
SERVES = {"reply": "initialize", "result": CAPABILITIES}
EXITS_AFTER_INITIALIZING: tuple[dict[str, object], ...] = (
    SERVES,
    {"err": "boom"},
    {"exit": 3},
)
READY = "python · basedpyright · ready"
STOPPED = "python · basedpyright · stopped: exit 3 · Restart"
NOT_INSTALLED = (
    "no code intelligence for TypeScript: typescript-language-server is not installed · Health"
)
NO_SERVER = "no code intelligence for Kotlin yet"
TEXT_OF = "selector => document.querySelector(selector)?.textContent ?? null"
PREFERENCE = "#pref-code_intelligence"


@dataclass
class Seen:
    """What the tabs and the fake server showed at each step."""

    ready: str = ""
    uri: str = ""
    methods_of_the_file: list[str] = field(default_factory=list[str])
    original_text: str = ""
    opened_text: str = ""
    opened_language: str = ""
    editor_text: str = ""
    changed_text: str = ""
    saved_uri: str = ""
    closed_uri: str = ""
    segment_after_close: int = -1
    sessions_of_two_tabs: int = 0
    first_tab_still: str = ""
    second_tab_ready: str = ""
    second_tab_saved: bool = False
    initializes: int = 0
    not_installed: str = ""
    health_link: str = ""
    health_checks: list[str] = field(default_factory=list[str])
    health_python: str = ""
    no_server: str = ""
    languages: list[str] = field(default_factory=list[str])
    languages_link: str = ""
    stopped: str = ""
    stopped_title: str = ""
    restarted: str = ""
    exits_when_turned_off: int = 0
    segment_when_off: int = -1
    sessions_when_off: int = -1
    errors: list[str] = field(default_factory=list[str])


@dataclass
class Lab:
    workspace: Path
    script: ScriptedServer
    variables: dict[str, str]
    attempts: dict[str, int]


@pytest.fixture(scope="module")
def lab(engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Lab:
    base = tmp_path_factory.mktemp(f"intelligence-{engine}")
    workspace = workspace_like(practice_workspace, base / "workspace")
    for slug, language in (PYTHON, TYPESCRIPT, KOTLIN):
        _cstudy(workspace, "start", slug, "--lang", language, "--no-open")
    install_fake_basedpyright(workspace)
    FsPreferencesStore(workspace).write(preferences_document(Preferences(code_intelligence=True)))
    script = ScriptedServer(base / "server.json")
    script.play(SERVES)
    return Lab(workspace, script, {"PATH": fake_node(base / "bin", script)}, {})


def _cstudy(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )


@pytest.fixture(scope="module")
def server(lab: Lab) -> Iterator[RunningServer]:
    with running_server(lab.workspace, variables=lab.variables) as running:
        lab.attempts.update(opened_page(running).attempts)
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, lab: Lab, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        first = watched(context.new_page(), found.errors)
        first.set_default_timeout(WAIT_MS)
        first.goto(server.login_url)
        first.wait_for_selector("table.problems tbody tr")
        _one_file(first, lab, found)
        _two_tabs(context, first, server, lab, found)
        _file_closes(first, lab, found)
        _languages_without_a_server(first, lab, found)
        _settings_and_health(first, found)
        _stopped_and_restarted(first, lab, found)
        _turned_off(first, lab, found)
        browser.close()
    return found


def _open_attempt(page: Any, lab: Lab, slug: str) -> None:
    page.evaluate("id => { location.hash = `#/attempts/${id}` }", lab.attempts[slug])
    page.wait_for_selector(EDITOR)


def _status(page: Any, text: str) -> str:
    """Waits until the status bar's segment says exactly `text`; returns it."""
    page.wait_for_function(
        "([selector, text]) => document.querySelector(selector)?.textContent === text",
        arg=[SEGMENT, text],
    )
    return page.eval_on_selector(SEGMENT, "element => element.textContent")


def _document(page: Any) -> str:
    """The text of the editor in front, as CodeMirror holds it."""
    lines = page.locator(f"{EDITOR} .cm-line").all_inner_texts()
    return "\n".join(lines)


def _messages(lab: Lab, method: str) -> list[dict[str, Any]]:
    return [message for message in lab.script.received() if message.get("method") == method]


def _document_messages(lab: Lab, method: str) -> list[dict[str, Any]]:
    return [message["params"]["textDocument"] for message in _messages(lab, method)]


def _one_file(page: Any, lab: Lab, found: Seen) -> None:
    _open_attempt(page, lab, PYTHON[0])
    found.ready = _status(page, READY)
    path = page.get_attribute(ACTIVE_TAB, "title")
    found.uri = (lab.workspace / ROOT / path).resolve().as_uri()
    opened = eventually(lambda: _document_messages(lab, "textDocument/didOpen"), bool)[0]
    found.opened_text = opened["text"]
    found.opened_language = opened["languageId"]
    found.initializes = len(_messages(lab, "initialize"))
    found.original_text = _document(page)
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("# typed\n")
    changes = eventually(lambda: _messages(lab, "textDocument/didChange"), bool)[0]
    found.changed_text = changes["params"]["contentChanges"][0]["text"]
    found.editor_text = _document(page)
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(SAVED_TAB)
    found.saved_uri = eventually(lambda: _document_messages(lab, "textDocument/didSave"), bool)[0][
        "uri"
    ]
    found.methods_of_the_file = [
        message["method"]
        for message in lab.script.received()
        if message.get("params", {}).get("textDocument", {}).get("uri") == found.uri
    ]


def _two_tabs(context: Any, first: Any, server: RunningServer, lab: Lab, found: Seen) -> None:
    """A second visible tab on the same attempt holds a session of its own, and both save."""
    second = watched(context.new_page(), found.errors)
    second.set_default_timeout(WAIT_MS)
    second.goto(f"{server.address}/")
    second.wait_for_selector("table.problems tbody tr")
    _open_attempt(second, lab, PYTHON[0])
    found.second_tab_ready = _status(second, READY)
    found.sessions_of_two_tabs = len(eventually(lab.script.pids, lambda pids: len(pids) >= 2))
    found.first_tab_still = _status(first, READY)
    second.click(EDITOR)
    second.keyboard.press("ControlOrMeta+End")
    second.keyboard.type("# second\n")
    second.keyboard.press("ControlOrMeta+s")
    second.wait_for_selector(SAVED_TAB)
    found.second_tab_saved = True
    second.close()


def _file_closes(page: Any, lab: Lab, found: Seen) -> None:
    page.click(f"{ACTIVE_TAB} .tab-close")
    found.closed_uri = eventually(lambda: _document_messages(lab, "textDocument/didClose"), bool)[
        0
    ]["uri"]
    found.segment_after_close = page.locator(SEGMENT).count()


def _languages_without_a_server(page: Any, lab: Lab, found: Seen) -> None:
    _open_attempt(page, lab, TYPESCRIPT[0])
    found.not_installed = _status(page, NOT_INSTALLED)
    found.health_link = page.get_attribute(f"{SEGMENT} a", "href")
    _open_attempt(page, lab, KOTLIN[0])
    found.no_server = _status(page, NO_SERVER)


def _settings_and_health(page: Any, found: Seen) -> None:
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector("ul.languages li a")
    found.languages = [
        text.replace("\n", " ") for text in page.locator("ul.languages li").all_inner_texts()
    ]
    found.languages_link = page.get_attribute("ul.languages li a", "href")
    page.evaluate("location.hash = '#/health'")
    page.wait_for_selector("table.checks", timeout=240_000)
    found.health_checks = page.locator("td.check-name").all_inner_texts()
    row = page.locator("tr", has=page.locator("td.check-name", has_text="code intelligence python"))
    found.health_python = row.locator("td.check-detail").inner_text()


def _stopped_and_restarted(page: Any, lab: Lab, found: Seen) -> None:
    """A server that exits right after initializing stops the session; Restart opens it again."""
    lab.script.play(*EXITS_AFTER_INITIALIZING)
    page.reload()
    page.wait_for_selector("table.checks")
    _open_attempt(page, lab, PYTHON[0])
    found.stopped = _status(page, STOPPED)
    found.stopped_title = page.get_attribute(SEGMENT, "title")
    lab.script.play(SERVES)
    page.click(f"{SEGMENT} button")
    found.restarted = _status(page, READY)


def _turned_off(page: Any, lab: Lab, found: Seen) -> None:
    """Turning the preference off closes the session at once, also with the view left."""
    exits = len(_messages(lab, "exit"))
    pids = len(lab.script.pids())
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector(PREFERENCE)
    page.uncheck(PREFERENCE)
    save_preferences(page)
    found.exits_when_turned_off = (
        len(eventually(lambda: _messages(lab, "exit"), lambda m: len(m) > exits)) - exits
    )
    _open_attempt(page, lab, PYTHON[0])
    page.wait_for_timeout(1000)
    found.segment_when_off = page.locator(SEGMENT).count()
    found.sessions_when_off = len(lab.script.pids()) - pids


def test_the_session_becomes_ready(seen):
    assert seen.ready == READY


def test_the_server_is_initialized_once_per_session(seen):
    assert seen.initializes == 1


def test_the_server_hears_the_tabs_text_when_the_file_opens(seen):
    assert seen.opened_text.split() == seen.original_text.split()


def test_the_server_hears_the_files_language(seen):
    assert seen.opened_language == "python"


def test_typing_reaches_the_server_as_the_tabs_whole_text(seen):
    assert seen.changed_text.split() == seen.editor_text.split()


def test_a_save_reaches_the_server_for_the_same_uri(seen):
    assert seen.saved_uri == seen.uri


def test_the_server_hears_the_file_in_order(seen):
    assert seen.methods_of_the_file == [
        "textDocument/didOpen",
        "textDocument/didChange",
        "textDocument/didSave",
    ]


def test_closing_the_tab_closes_the_document(seen):
    assert seen.closed_uri == seen.uri


def test_a_tab_with_no_file_shows_no_segment(seen):
    assert seen.segment_after_close == 0


def test_two_visible_tabs_each_hold_a_session(seen):
    assert (seen.sessions_of_two_tabs, seen.second_tab_ready, seen.first_tab_still) == (
        2,
        READY,
        READY,
    )


def test_the_second_tab_still_saves(seen):
    assert seen.second_tab_saved


def test_a_server_that_is_not_installed_says_so_with_a_link_to_health(seen):
    assert (seen.not_installed, seen.health_link) == (NOT_INSTALLED, "#/health")


def test_a_language_with_no_server_yet_says_so(seen):
    assert seen.no_server == NO_SERVER


def test_the_settings_view_lists_each_language(seen):
    assert seen.languages[:2] == [
        "Python basedpyright 1.40.2",
        "TypeScript not installed: run cstudy doctor --fix",
    ]


def test_the_settings_view_lists_the_languages_without_a_server_yet(seen):
    assert "Kotlin not available yet" in seen.languages


def test_an_uninstalled_language_in_settings_links_to_health(seen):
    assert seen.languages_link == "#/health"


def test_the_health_view_shows_the_code_intelligence_rows(seen):
    assert [name for name in seen.health_checks if name.startswith("code intelligence")] == [
        "code intelligence python",
        "code intelligence typescript",
        "code intelligence java",
        "code intelligence go",
        "code intelligence rust",
    ]


def test_the_health_view_names_the_installed_server(seen):
    assert "basedpyright 1.40.2" in seen.health_python


def test_a_server_that_exits_stops_the_session_with_restart(seen):
    assert (seen.stopped, seen.stopped_title.startswith("exit 3")) == (STOPPED, True)


def test_restart_opens_the_session_again(seen):
    assert seen.restarted == READY


def test_turning_the_preference_off_closes_the_session(seen):
    assert seen.exits_when_turned_off == 1


def test_with_the_preference_off_a_file_opens_no_session_and_no_segment(seen):
    assert (seen.segment_when_off, seen.sessions_when_off) == (0, 0)


def test_the_page_logs_no_error_and_no_policy_violation(seen):
    assert seen.errors == []
