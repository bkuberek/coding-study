"""Code intelligence on a service project in Chromium (docs/specs/web-ui.md#status-bar,
docs/specs/service-projects.md#language-servers), against a real `cstudy serve` whose `docker` is
a fake (`fake_docker`) and whose TypeScript server is the scripted fake: a TypeScript file of the
catalog's first service project gets a session whose server runs through `docker exec` in a
sidecar that came up detached, and whose diagnostic the editor draws; the sidecar goes once the
page has gone. With Docker stopped, the segment says so calmly, with Restart and no error colour,
and nothing starts. No console error and no Content Security Policy violation.

The attempt is started in this process, since `cstudy start` would install the project in Docker
and nothing here needs it. Playwright and Chromium are set up as `tests/browsers.py` says; without
them the test is skipped.
"""

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
from tests.language_server_scripts import (
    ScriptedServer,
    fake_docker,
    fake_node,
    notification,
)
from tests.scripted_runs import eventually
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
LANGUAGES = "/api/v1/code-intelligence/languages"
HEAD = "typescript · typescript-language-server · "
READY = f"{HEAD}ready · 1 error"
WAITING = f"{HEAD}Docker is not running · Restart"
WAIT_MS = 60_000
STEADY_MS = 5_000
"""How long a calm segment is watched for a change, longer than a reconnect's first wait."""
SERVES = {"reply": "initialize", "result": {"capabilities": {"textDocumentSync": 2}}}
WRONG_TYPE = {
    "range": {"start": {"line": 7, "character": 6}, "end": {"line": 7, "character": 10}},
    "severity": 1,
    "source": "typescript",
    "message": "Type 'number' is not assignable to type 'string'.",
}
DIAGNOSES = (
    SERVES,
    {"await": "textDocument/didOpen"},
    {
        "send": notification(
            "textDocument/publishDiagnostics", {"uri": "$uri", "diagnostics": [WRONG_TYPE]}
        )
    },
)


@pytest.fixture(scope="module", params=["chromium"])
def engine(request: pytest.FixtureRequest) -> str:
    """Chromium alone: what differs here is the server's side, not the engine's."""
    return request.param


@dataclass
class Lab:
    workspace: Path
    script: ScriptedServer
    docker_log: Path
    variables: dict[str, str]

    def docker_calls(self) -> list[str]:
        if not self.docker_log.exists():
            return []
        return self.docker_log.read_text().splitlines()


@dataclass
class Seen:
    segment: str = ""
    state: str = ""
    buttons: int = -1
    underlined: int = -1
    segment_later: str = ""
    errors: list[str] = field(default_factory=list[str])


def make_lab(base: Path, practice_workspace: Path, *, running: bool) -> Lab:
    workspace = workspace_like(practice_workspace, base / "workspace")
    environment = load_environment(workspace, served_environment(workspace), workspace.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    _install_fake_typescript_server(workspace)
    FsPreferencesStore(workspace).write(preferences_document(Preferences(code_intelligence=True)))
    script = ScriptedServer(base / "server.json")
    script.play(*DIAGNOSES)
    path = fake_node(base / "bin", script)
    log = base / "docker.log"
    fake_docker(base / "bin", log, running=running)
    return Lab(workspace, script, log, {"PATH": path})


def _install_fake_typescript_server(workspace: Path) -> None:
    """The file `cstudy` looks for in `.cs/lsp/`. The workspace's `typescript/` has no
    `node_modules`, as for a learner of service projects only: a sidecar's server runs the
    project's own compiler, so the page's list for the attempt counts the server as installed."""
    script = workspace / LSP_DIRECTORY / str(TYPESCRIPT_LANGUAGE_SERVER.script)
    script.parent.mkdir(parents=True)
    script.write_text("")
    (workspace / "typescript" / "node_modules").unlink()


def _open_the_file(page: Any, server: RunningServer) -> None:
    attempt_id = opened_page(server).attempts[SLUG]
    page.goto(server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    page.evaluate("id => { location.hash = `#/attempts/${id}` }", attempt_id)
    page.click(FILE_BUTTON)
    page.wait_for_function(
        "([selector, path]) => document.querySelector(selector)?.title === path",
        arg=[ACTIVE_TAB, SOURCE_FILE],
    )
    page.wait_for_selector(EDITOR)


def _segment_once_it_says(page: Any, text: str) -> str:
    page.wait_for_function(
        "([selector, text]) => document.querySelector(selector)?.textContent === text",
        arg=[SEGMENT, text],
    )
    return page.eval_on_selector(SEGMENT, "element => element.textContent")


@pytest.fixture(scope="module")
def running_lab(engine: str, practice_workspace: Path, tmp_path_factory) -> Lab:
    return make_lab(tmp_path_factory.mktemp("service-sidecar"), practice_workspace, running=True)


@pytest.fixture(scope="module")
def seen(engine: str, running_lab: Lab) -> Seen:
    """Once the page has gone, `cstudy serve` keeps running until the sidecar went with it."""
    found = Seen()
    with (
        running_server(running_lab.workspace, variables=running_lab.variables) as server,
        sync_api.sync_playwright() as playwright,
    ):
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        _open_the_file(page, server)
        found.segment = _segment_once_it_says(page, READY)
        found.underlined = page.locator(".panel:not([hidden]) .cm-lintRange-error").count()
        browser.close()
        eventually(running_lab.docker_calls, lambda calls: any(" down" in call for call in calls))
    return found


def test_a_file_of_a_typescript_service_project_gets_a_ready_session(seen):
    assert seen.segment == READY


def test_the_editor_draws_the_servers_diagnostic(seen):
    assert seen.underlined == 1


def test_the_sidecar_came_up_detached_from_its_own_compose_file(seen, running_lab):
    ups = [call for call in running_lab.docker_calls() if " up --detach " in call]
    assert [(" -p cstudy-l-" in call, "stack.yaml" in call) for call in ups] == [(True, True)]


def test_the_server_ran_in_the_sidecar_through_docker_exec(seen, running_lab):
    folder = running_lab.workspace / "projects" / SLUG
    execs = [call for call in running_lab.docker_calls() if call.startswith("exec ")]
    assert [call.split(" cstudy-l-")[0] for call in execs] == [
        f"exec --interactive --workdir {folder}"
    ]


def test_the_server_is_the_one_in_the_workspaces_lsp_directory(seen, running_lab):
    script = running_lab.workspace / LSP_DIRECTORY / str(TYPESCRIPT_LANGUAGE_SERVER.script)
    exec_call = next(call for call in running_lab.docker_calls() if call.startswith("exec "))
    assert exec_call.endswith(f"node {script} --stdio")


def test_the_sidecar_goes_once_the_page_has_gone(seen, running_lab):
    downs = [call for call in running_lab.docker_calls() if call.endswith(" down")]
    assert [" -p cstudy-l-" in call for call in downs] == [True]


def test_the_workspace_alone_has_no_typescript_server_to_run_on_this_machine(running_lab):
    with running_server(running_lab.workspace, variables=running_lab.variables) as server:
        states = opened_page(server).client.get(LANGUAGES).json()["languages"]
    typescript = next(state for state in states if state["language"] == "typescript")
    assert typescript["state"] == "not_installed"


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []


@pytest.fixture(scope="module")
def stopped_lab(engine: str, practice_workspace: Path, tmp_path_factory) -> Lab:
    base = tmp_path_factory.mktemp("service-sidecar-stopped")
    return make_lab(base, practice_workspace, running=False)


@pytest.fixture(scope="module")
def seen_stopped(engine: str, stopped_lab: Lab) -> Seen:
    found = Seen()
    with (
        running_server(stopped_lab.workspace, variables=stopped_lab.variables) as server,
        sync_api.sync_playwright() as playwright,
    ):
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        _open_the_file(page, server)
        found.segment = _segment_once_it_says(page, WAITING)
        found.state = page.get_attribute(SEGMENT, "data-state") or ""
        found.buttons = page.locator(f"{SEGMENT} button").count()
        page.wait_for_timeout(STEADY_MS)
        found.segment_later = page.eval_on_selector(SEGMENT, "element => element.textContent")
        browser.close()
    return found


def test_with_docker_stopped_the_segment_says_so(seen_stopped):
    assert seen_stopped.segment == WAITING


def test_with_docker_stopped_the_segment_is_calm_with_a_restart(seen_stopped):
    assert (seen_stopped.state, seen_stopped.buttons) == ("needs-docker", 1)


def test_with_docker_stopped_the_page_does_not_keep_trying(seen_stopped):
    assert seen_stopped.segment_later == WAITING


def test_with_docker_stopped_no_sidecar_and_no_server_start(seen_stopped, stopped_lab):
    calls = stopped_lab.docker_calls()
    started = [call for call in calls if call.startswith(("compose", "exec"))]
    assert (started, stopped_lab.script.pids()) == ([], [])


def test_with_docker_stopped_no_console_error_or_csp_violation(seen_stopped):
    assert seen_stopped.errors == []
