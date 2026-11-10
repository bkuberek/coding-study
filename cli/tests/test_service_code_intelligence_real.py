"""Code intelligence on a service project from inside its sidecar, on a real Docker engine and the
real servers of `.cs/lsp/` (docs/specs/service-projects.md#language-servers): `cstudy start`
installs the fixture project in Docker, a session opens a file with a type error, and the
diagnostic and a hover come from the server in the sidecar, over `docker exec`, on the project's
own installed dependencies; once the session ends, nothing of cstudy's is left. Run with
`uv run pytest -q -m docker`. Needs Node and pnpm for `.cs/lsp/`; skipped where the servers
cannot be installed. The waits are generous for a busy machine."""

from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any

import pytest
from starlette.testclient import WebSocketTestSession

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.language_server_scripts import notification, request
from tests.language_sessions import received, session
from tests.real_service_projects import PYTHON, TYPESCRIPT, FixtureProject, docker, fixture_project
from tests.waits import GENEROUS_WAIT_S
from tests.web_server import session_client, web_app

pytestmark = [pytest.mark.slow, pytest.mark.docker]


@dataclass(frozen=True, slots=True)
class Opened:
    """A file of the fixture, the text the page opens it with, what it is wrong about, and where
    a hover lands."""

    path: str
    language_id: str
    text: str
    error: str
    """Words of the error the server reports for `text`."""
    hover_at: dict[str, int]
    hovered: str
    """Words of the hover there."""


TYPESCRIPT_FILE = Opened(
    path="src/server.ts",
    language_id="typescript",
    text=(
        'import { createServer } from "node:http";\n\n'
        "const port: string = Number(process.env.PORT);\n"
        "createServer().listen(port);\n"
    ),
    error="is not assignable to type 'string'",
    hover_at={"line": 0, "character": 10},
    hovered="createServer",
)
"""`createServer`'s types come from the project's own `@types/node` in its `node_modules`."""
PYTHON_FILE = Opened(
    path="src/server.py",
    language_id="python",
    text="import json\n\nprint(json.dumps({}) + 1)\n",
    error="Operator",
    hover_at={"line": 2, "character": 12},
    hovered="dumps",
)
FILES = {TYPESCRIPT: TYPESCRIPT_FILE, PYTHON: PYTHON_FILE}


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")


@pytest.fixture(scope="module", params=[TYPESCRIPT, PYTHON], ids=["typescript", "python"])
def project(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[FixtureProject]:
    found = fixture_project(request.param, tmp_path_factory.mktemp("sidecar"))
    try:
        started = found.cstudy("start", found.slug, "--yes", "--no-open")
        assert started.returncode == 0, f"{started.stdout}\n{started.stderr}"
        installed = LspDirectory(found.root, SubprocessToolProbe(), SubprocessCommandRunner())
        result = installed.install()
        if result is None or result.exit_code != 0:
            pytest.skip(f"the language servers are not installed: {result and result.output}")
        FsPreferencesStore(found.root).write(
            preferences_document(Preferences(code_intelligence=True))
        )
        yield found
    finally:
        found.remove_all_it_left()


@dataclass
class Played:
    diagnostics: list[dict[str, Any]]
    hover: dict[str, Any]


def until(
    websocket: WebSocketTestSession, matches: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        message = received(websocket, GENEROUS_WAIT_S)
        if matches(message):
            return message


@pytest.fixture(scope="module")
def played(project: FixtureProject) -> Played:
    """A session that opens the file, waits for its diagnostics and asks for a hover, then ends;
    the server's stop has taken the sidecar down by the time the app has stopped."""
    opened = FILES[project.directory]
    environment = load_environment(project.root, project.environment(), project.root.parent)
    attempt = environment.progress.active_attempt(project.slug)
    assert attempt is not None
    document = (project.folder / opened.path).as_uri()
    app = web_app(project.root, environment, sessions=LanguageSessions())
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        websocket.send_json(request(1, "initialize", {"capabilities": {}}))
        until(websocket, lambda message: message.get("id") == 1)
        websocket.send_json(notification("initialized", {}))
        text = {
            "uri": document,
            "languageId": opened.language_id,
            "version": 1,
            "text": opened.text,
        }
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": text}))
        published = until(websocket, lambda message: _reports_on(message, document))
        position = {"textDocument": {"uri": document}, "position": opened.hover_at}
        websocket.send_json(request(2, "textDocument/hover", position))
        hover = until(websocket, lambda message: message.get("id") == 2)
    return Played(published["params"]["diagnostics"], hover)


def _reports_on(message: dict[str, Any], document: str) -> bool:
    params = message.get("params") or {}
    return (
        message.get("method") == "textDocument/publishDiagnostics"
        and params.get("uri") == document
        and bool(params.get("diagnostics"))
    )


def test_the_server_in_the_sidecar_reports_the_type_error(project, played):
    error = FILES[project.directory].error

    assert any(error in diagnostic["message"] for diagnostic in played.diagnostics)


def test_the_server_in_the_sidecar_answers_a_hover_from_the_projects_dependencies(project, played):
    assert FILES[project.directory].hovered in played.hover["result"]["contents"]["value"]


def test_no_container_is_left_once_the_session_ended(project, played):
    assert project.labelled("containers") == []


def test_no_folder_of_the_sidecar_is_left_once_the_session_ended(project, played):
    assert not any((project.root / ".cs" / "runs").glob("cstudy-l-*"))
