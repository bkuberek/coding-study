"""A service project from `cstudy start` to the last `cstudy submit`, in TypeScript and in Python,
on a real Docker engine, and its code intelligence from inside the sidecar. Run with
`uv run pytest -q -m docker`. The waits are generous for a busy machine: what these tests assert
is what happened, not how fast."""

from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
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
from tests.real_service_projects import (
    MEMBERS,
    PYTHON,
    TYPESCRIPT,
    FixtureProject,
    docker,
    fixture_project,
)
from tests.waits import GENEROUS_WAIT_S
from tests.web_server import session_client, web_app

pytestmark = [pytest.mark.slow, pytest.mark.docker]

EXIT_OK = 0
EXIT_FAILURES = 1


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")


@pytest.fixture(params=[TYPESCRIPT, PYTHON], ids=["typescript", "python"])
def project(request: pytest.FixtureRequest, tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(request.param, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


def said(result) -> str:
    return f"exit {result.returncode}\n{result.stdout}\n{result.stderr}"


def nothing_running(project: FixtureProject) -> None:
    assert project.labelled("containers") == []
    assert project.labelled("networks") == []


def test_a_project_from_start_to_the_last_level(project: FixtureProject):
    assert_passes_its_static_checks(project)
    assert_start_installs_and_starts_nothing(project)
    assert_the_starter_fails_its_visible_cases(project)
    project.use_naive()
    assert_the_naive_solution_passes_what_is_visible(project)
    assert_the_first_level_opens_the_next(project)
    assert_a_hidden_case_catches_the_naive_solution(project)
    project.use_reference()
    assert_the_reference_finishes_every_level(project)


def assert_passes_its_static_checks(project: FixtureProject) -> None:
    result = project.cstudy("verify", project.slug, "--static")

    assert result.returncode == EXIT_OK, said(result)


def assert_start_installs_and_starts_nothing(project: FixtureProject) -> None:
    result = project.cstudy("start", project.slug, "--yes", "--no-open")

    assert result.returncode == EXIT_OK, said(result)
    assert "cstudy dev" in result.stdout
    assert any(project.folder.glob("node_modules")) or any(project.folder.glob(".venv"))
    nothing_running(project)


def assert_the_starter_fails_its_visible_cases(project: FixtureProject) -> None:
    result = project.cstudy("test")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "commands.test passed" in result.stdout
    assert "not counted" in result.stdout
    nothing_running(project)


def assert_the_naive_solution_passes_what_is_visible(project: FixtureProject) -> None:
    result = project.cstudy("test")

    assert result.returncode == EXIT_OK, said(result)
    assert "2/2 visible passed" in result.stdout


def assert_the_first_level_opens_the_next(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_OK, said(result)
    assert "level 2 unlocked" in result.stdout
    nothing_running(project)


def assert_a_hidden_case_catches_the_naive_solution(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "h5" in result.stdout
    assert "expected 2 requests" in result.stdout
    nothing_running(project)


def assert_the_reference_finishes_every_level(project: FixtureProject) -> None:
    result = project.cstudy("submit")

    assert result.returncode == EXIT_OK, said(result)
    assert "startup" in result.stdout
    nothing_running(project)


def test_verify_require_ready_passes_on_the_reference(project: FixtureProject):
    result = project.cstudy("verify", project.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(project)


@pytest.fixture
def members(tmp_path: Path) -> Generator[FixtureProject]:
    """Postgres and Redis as backing services, migrations, `grade_setup` and `reset`."""
    found = fixture_project(MEMBERS, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


def no_data_of_a_run_left(project: FixtureProject) -> None:
    """A test or graded stack's volumes, its backing services' among them, go with it; the install
    cache stays by design."""
    left = [
        volume
        for kind in ("test", "graded")
        for volume in docker(
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=cstudy.slug={project.slug}",
            "--filter",
            f"label=cstudy.kind={kind}",
        ).stdout.split()
    ]
    assert left == []


def test_a_project_with_postgres_and_redis_from_start_to_the_last_level(members: FixtureProject):
    assert_passes_its_static_checks(members)
    assert_start_installs_and_starts_nothing(members)
    assert_the_starter_fails_its_visible_cases(members)
    members.use_naive()
    assert_the_naive_solution_passes_what_is_visible(members)
    assert_a_member_loaded_before_the_migration_catches_the_naive_one(members)
    members.use_reference()
    assert_the_first_level_opens_the_next(members)
    assert_the_reference_finishes_every_level(members)
    no_data_of_a_run_left(members)


def assert_a_member_loaded_before_the_migration_catches_the_naive_one(
    project: FixtureProject,
) -> None:
    """`grade_setup` loads member 900 into the baseline, and the naive migration drops the table."""
    result = project.cstudy("submit")

    assert result.returncode == EXIT_FAILURES, said(result)
    assert "h3" in result.stdout
    nothing_running(project)
    no_data_of_a_run_left(project)


def test_verify_require_ready_passes_on_the_reference_with_backing_services(
    members: FixtureProject,
):
    result = members.cstudy("verify", members.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(members)
    no_data_of_a_run_left(members)


# Code intelligence from inside the sidecar (docs/specs/service-projects.md#language-servers):
# `cstudy start` installs the fixture, the real servers of `.cs/lsp/` run in a sidecar over
# `docker exec`, and a session gets a type error and a hover from the project's own
# dependencies; once it ends, nothing of cstudy's is left. Needs Node and pnpm for `.cs/lsp/`.


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


@pytest.fixture(scope="module", params=[TYPESCRIPT, PYTHON], ids=["typescript", "python"])
def sidecar_project(
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
def sidecar_session(sidecar_project: FixtureProject) -> Played:
    """A session that opens the file, waits for its diagnostics and asks for a hover, then ends;
    the server's stop has taken the sidecar down by the time the app has stopped."""
    opened = FILES[sidecar_project.directory]
    environment = load_environment(
        sidecar_project.root, sidecar_project.environment(), sidecar_project.root.parent
    )
    attempt = environment.progress.active_attempt(sidecar_project.slug)
    assert attempt is not None
    document = (sidecar_project.folder / opened.path).as_uri()
    app = web_app(sidecar_project.root, environment, sessions=LanguageSessions())
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


def test_the_server_in_the_sidecar_reports_the_type_error(sidecar_project, sidecar_session):
    error = FILES[sidecar_project.directory].error

    assert any(error in diagnostic["message"] for diagnostic in sidecar_session.diagnostics)


def test_the_server_in_the_sidecar_answers_a_hover_from_the_projects_dependencies(
    sidecar_project, sidecar_session
):
    assert (
        FILES[sidecar_project.directory].hovered
        in sidecar_session.hover["result"]["contents"]["value"]
    )


def test_no_container_is_left_once_the_session_ended(sidecar_project, sidecar_session):
    assert sidecar_project.labelled("containers") == []


def test_no_folder_of_the_sidecar_is_left_once_the_session_ended(sidecar_project, sidecar_session):
    assert not any((sidecar_project.root / ".cs" / "runs").glob("cstudy-l-*"))
