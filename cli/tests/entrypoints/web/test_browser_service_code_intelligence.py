"""Code intelligence on a service project in a real browser
(docs/specs/web-ui.md#status-bar), in each engine of `tests/browsers.py`, against a real
`cstudy serve` whose TypeScript server counts as installed: a TypeScript file of the catalog's
first service project says that code intelligence for service projects comes later, with no
Restart; the page reads no list of languages and opens no session, so no server starts; and the
segment stays as it is. No console error and no Content Security Policy violation.

The attempt is started in this process, since `cstudy start` would install the project in Docker
and nothing here needs it. Playwright and its engines are set up as `tests/browsers.py` says;
without them the test is skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import LSP_DIRECTORY, TYPESCRIPT_LANGUAGE_SERVER
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.language_server_scripts import ScriptedServer, fake_node
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SLUG = "coworking-availability-typescript"
SOURCE_FILE = "src/server.ts"
FILE_BUTTON = f"button.tree-file[data-path='{SOURCE_FILE}']"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
EDITOR = ".panel:not([hidden]) .cm-content"
SEGMENT = ".statusbar .code-intelligence"
LATER = "code intelligence for service projects comes later"
LANGUAGES = "/api/v1/code-intelligence/languages"
SESSIONS = "/api/v1/code-intelligence"
WAIT_MS = 60_000
STEADY_MS = 5_000
"""How long the segment is watched for a change, longer than a reconnect's first wait."""
SERVES = {"reply": "initialize", "result": {"capabilities": {"textDocumentSync": 2}}}


@dataclass
class Seen:
    segment: str = ""
    buttons: int = -1
    segment_later: str = ""
    sockets: list[str] = field(default_factory=list[str])
    requests: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@dataclass
class Lab:
    workspace: Path
    script: ScriptedServer
    variables: dict[str, str]


@pytest.fixture(scope="module")
def lab(engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Lab:
    base = tmp_path_factory.mktemp(f"service-intelligence-{engine}")
    workspace = workspace_like(practice_workspace, base / "workspace")
    environment = load_environment(workspace, served_environment(workspace), workspace.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    _install_fake_typescript_server(workspace)
    FsPreferencesStore(workspace).write(preferences_document(Preferences(code_intelligence=True)))
    script = ScriptedServer(base / "server.json")
    script.play(SERVES)
    return Lab(workspace, script, {"PATH": fake_node(base / "bin", script)})


def _install_fake_typescript_server(workspace: Path) -> None:
    """The file `cstudy` looks for in `.cs/lsp/`; the workspace's `typescript/node_modules`
    holds the `tsserver` it also needs."""
    script = workspace / LSP_DIRECTORY / str(TYPESCRIPT_LANGUAGE_SERVER.script)
    script.parent.mkdir(parents=True)
    script.write_text("")


@pytest.fixture(scope="module")
def server(lab: Lab) -> Iterator[RunningServer]:
    with running_server(lab.workspace, variables=lab.variables) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    attempt_id = opened_page(server).attempts[SLUG]
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.on("websocket", lambda socket: found.sockets.append(socket.url))
        page.on("request", lambda request: found.requests.append(request.url))
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("id => { location.hash = `#/attempts/${id}` }", attempt_id)
        page.click(FILE_BUTTON)
        page.wait_for_function(
            "([selector, path]) => document.querySelector(selector)?.title === path",
            arg=[ACTIVE_TAB, SOURCE_FILE],
        )
        page.wait_for_selector(EDITOR)
        found.segment = _segment_once_it_says(page, LATER)
        found.buttons = page.locator(f"{SEGMENT} button").count()
        page.wait_for_timeout(STEADY_MS)
        found.segment_later = page.eval_on_selector(SEGMENT, "element => element.textContent")
        browser.close()
    return found


def _segment_once_it_says(page: Any, text: str) -> str:
    page.wait_for_function(
        "([selector, text]) => document.querySelector(selector)?.textContent === text",
        arg=[SEGMENT, text],
    )
    return page.eval_on_selector(SEGMENT, "element => element.textContent")


def test_the_typescript_server_counts_as_installed(server):
    states = opened_page(server).client.get(LANGUAGES).json()["languages"]
    typescript = next(state for state in states if state["language"] == "typescript")
    assert typescript["state"] == "installed"


def test_a_file_of_a_service_project_says_code_intelligence_comes_later(seen):
    assert seen.segment == LATER


def test_the_segment_offers_no_restart(seen):
    assert seen.buttons == 0


def test_the_segment_stays_as_it_is(seen):
    assert seen.segment_later == LATER


def test_the_page_opens_no_session(seen):
    assert [url for url in seen.sockets if SESSIONS in url] == []


def test_the_page_reads_no_list_of_languages(seen):
    assert [url for url in seen.requests if LANGUAGES in url] == []


def test_no_language_server_starts(seen, lab):
    assert lab.script.pids() == []


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []
