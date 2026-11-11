"""A code-intelligence session on a service project (docs/specs/web-ui.md#sessions,
docs/specs/service-projects.md#language-servers): its server runs in a sidecar of its own, which
goes with the session; Docker that does not answer, or a sidecar image that is not here, closes
the socket calmly with 4004 and starts nothing. A fake engine's sidecar runs the scripted server
here."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.code_intelligence import (
    NO_KOTLIN_IMAGE,
    NO_PROJECT_IMAGE,
    NO_SIDECAR_IMAGE,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.errors import SandboxError
from coding_study.domain.preferences import preferences_document
from coding_study.domain.sandbox import GRADLE_GLIBC_IMAGE, NODE_IMAGE
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from coding_study.entrypoints.web.language_server import LanguageServerCommand
from tests.fakes import INSTALLED_SERVERS, FakeLanguageServers, make_environment
from tests.language_server_scripts import QUICK, ScriptedServer, request
from tests.language_sessions import (
    CODE_INTELLIGENCE_ON,
    Rig,
    closed_with,
    received,
    rig,
    session,
    stopped,
)
from tests.sandbox_fakes import FakeSandbox
from tests.scripted_runs import eventually, is_alive
from tests.service_problems import (
    GRADLE_IMAGE,
    SLUG,
    java_meta_document,
    make_content,
    write_problem,
)
from tests.web_server import session_client

NEEDS_DOCKER = 4004
INITIALIZED = {"reply": "initialize", "result": {"capabilities": {}}}


def service_rig(
    tmp_path: Path,
    sandbox: FakeSandbox,
    command: LanguageServerCommand | None = None,
    document: dict[str, object] | None = None,
):
    root = make_content(tmp_path)
    write_problem(root, document)
    environment = make_environment(
        root, sandbox=sandbox, language_servers=FakeLanguageServers(INSTALLED_SERVERS)
    )
    attempt = start_attempt(environment, StartRequest(SLUG)).attempt
    FsPreferencesStore(root).write(preferences_document(CODE_INTELLIGENCE_ON))
    scripted = ScriptedServer(tmp_path / "server.json")
    sessions = LanguageSessions(command or scripted.command, QUICK, sidecars=sandbox)
    return Rig(root, environment, sessions, scripted, attempt)


@pytest.fixture
def sandbox() -> FakeSandbox:
    return FakeSandbox()


@pytest.fixture
def lab(tmp_path, sandbox) -> Rig:
    return service_rig(tmp_path, sandbox)


@pytest.fixture
def client(lab) -> Iterator[TestClient]:
    with session_client(lab.app) as page:
        yield page


def sidecar_steps(sandbox: FakeSandbox) -> list[str]:
    return [name for name, _detail in sandbox.calls if name.startswith("sidecar")]


def servers_gone(lab: Rig) -> bool:
    alive = eventually(
        lambda: [is_alive(pid) for pid in lab.server.pids()], lambda found: not any(found)
    )
    return not any(alive)


def test_the_server_runs_in_the_sidecar(lab, client, sandbox):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
        assert sidecar_steps(sandbox) == ["sidecar", "sidecar_command"]


def test_the_sidecar_runs_the_catalogs_command(lab, client, sandbox):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    assert sandbox.called("sidecar_command") == [lab.server.arguments]


def test_the_server_runs_in_the_project_folder(lab, client):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    assert Path(lab.server.calls()[0]["cwd"]).resolve() == (lab.root / "projects" / SLUG).resolve()


def test_initialize_names_no_process_for_a_server_in_a_sidecar(lab, client):
    """The sidecar's servers cannot see this machine's processes, and would exit at once."""
    lab.server.play(INITIALIZED)
    with session(client, lab.query) as websocket:
        websocket.send_json(request(1, "initialize", {}))
        received(websocket)
    initialize = next(found for found in lab.server.received() if found["method"] == "initialize")
    assert initialize["params"]["processId"] is None


def test_the_docker_client_gets_no_variables_that_hide_directories(lab, client):
    """None of the hidden directories is mounted in the sidecar, and no variable crosses
    `docker exec`."""
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    call = lab.server.calls()[0]
    assert (call["hidden"], call["node_options"]) == (None, None)


def test_closing_the_socket_takes_the_sidecar_down_once_the_server_has_stopped(
    lab, client, sandbox
):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    eventually(lambda: sidecar_steps(sandbox), lambda steps: steps[-1:] == ["sidecar_down"])
    assert servers_gone(lab)


def test_stopping_cstudy_serve_takes_the_sidecar_down(lab, sandbox):
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
        stopped(page, lab.sessions)
        assert sidecar_steps(sandbox)[-1] == "sidecar_down"


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (EngineStatus.STOPPED, "Docker is not running"),
        (EngineStatus.NOT_INSTALLED, "Docker is not installed"),
        (EngineStatus.NO_PERMISSION, "Docker refuses this user"),
        (EngineStatus.NO_COMPOSE, "Docker has no compose v2"),
    ],
)
def test_docker_that_does_not_answer_closes_calmly_with_4004(tmp_path, state, reason):
    lab = service_rig(tmp_path, FakeSandbox(engine=EngineState(state)))
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (NEEDS_DOCKER, reason)


def test_docker_that_does_not_answer_starts_nothing(tmp_path):
    sandbox = FakeSandbox(engine=EngineState(EngineStatus.STOPPED))
    lab = service_rig(tmp_path, sandbox)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        closed_with(websocket)
    assert (sidecar_steps(sandbox), lab.server.calls(), sandbox.called("start_engine")) == (
        [],
        [],
        [],
    )


def test_a_sidecar_image_that_is_not_here_closes_calmly_with_4004_naming_the_pull(tmp_path):
    sandbox = FakeSandbox(every_image_present=False)
    lab = service_rig(tmp_path, sandbox)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (NEEDS_DOCKER, NO_SIDECAR_IMAGE)
    assert (sidecar_steps(sandbox), sandbox.called("pull")) == ([], [])


def test_a_sidecar_that_does_not_start_closes_with_4002_saying_why(tmp_path):
    sandbox = FakeSandbox(sidecar_error=SandboxError("the sidecar did not start: no space left"))
    lab = service_rig(tmp_path, sandbox)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (
            4002,
            "cannot start: the sidecar did not start: no space left",
        )


def test_a_server_that_cannot_start_in_the_sidecar_takes_the_sidecar_down(tmp_path, sandbox):
    lab = service_rig(tmp_path, sandbox, LanguageServerCommand(("cstudy-no-such-server",)))
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "cannot start: cstudy-no-such-server not found")
    assert sidecar_steps(sandbox)[-1] == "sidecar_down"


def test_a_practice_session_starts_no_sidecar(tmp_path, sandbox):
    lab = rig(tmp_path)
    lab.sessions = LanguageSessions(lab.server.command, QUICK, sidecars=sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    assert sandbox.calls == []


def java_rig(tmp_path: Path, sandbox: FakeSandbox) -> Rig:
    """A Java service project, whose JDT LS runs in a sidecar on the project's image."""
    return service_rig(tmp_path, sandbox, document=java_meta_document())


def sidecar_data(lab: Rig) -> list[Path]:
    return list((lab.root / ".cs" / "runs").glob("cstudy-l-*/data"))


def test_jdt_ls_in_the_sidecar_keeps_its_caches_in_the_sidecars_data_folder(tmp_path, sandbox):
    lab = java_rig(tmp_path, sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    (data,) = sidecar_data(lab)
    assert sandbox.exec_environments == [{"XDG_CACHE_HOME": f"{data}/cache"}]


def test_jdt_ls_finds_its_empty_list_of_gradle_versions_in_the_sidecars_data_folder(
    tmp_path, sandbox
):
    lab = java_rig(tmp_path, sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    (data,) = sidecar_data(lab)
    assert (data / "cache" / "tooling" / "gradle" / "versions.json").read_text() == "[]"


def test_a_node_server_in_the_sidecar_gets_no_variables_of_its_own(lab, client, sandbox):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    assert sandbox.exec_environments == [{}]


def test_a_projects_image_that_is_not_here_closes_calmly_with_4004_naming_what_pulls_it(
    tmp_path,
):
    sandbox = FakeSandbox(every_image_present=False, present={NODE_IMAGE})
    lab = java_rig(tmp_path, sandbox)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (NEEDS_DOCKER, NO_PROJECT_IMAGE)
    assert (sidecar_steps(sandbox), sandbox.called("pull")) == ([], [])


def test_the_java_sidecar_asks_for_the_projects_image(tmp_path):
    sandbox = FakeSandbox(every_image_present=False, present={GRADLE_IMAGE})
    lab = java_rig(tmp_path, sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    assert sidecar_steps(sandbox)[:2] == ["sidecar", "sidecar_command"]


def kotlin_rig(tmp_path: Path, sandbox: FakeSandbox) -> Rig:
    """A Kotlin service project, whose Kotlin LSP runs its Linux build on the glibc image."""
    document = {**java_meta_document(), "languages": ["kotlin"]}
    return service_rig(tmp_path, sandbox, document=document)


def test_the_kotlin_lsp_imports_with_the_images_jdk_and_its_gradle_home_in_the_data_folder(
    tmp_path, sandbox
):
    lab = kotlin_rig(tmp_path, sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    options = sandbox.exec_environments[0]["IJ_JAVA_OPTIONS"]
    runs = re.escape(str((lab.root / ".cs" / "runs").resolve()))
    home = rf"gradleUserHome={runs}/cstudy-l-[^/]+/data/gradle"
    assert (
        "-Dcom.jetbrains.ls.imports.gradle.java.home=/opt/java/openjdk" in options,
        re.search(home, options) is not None,
    ) == (True, True)


def test_a_missing_kotlin_image_closes_calmly_naming_its_pull_by_digest(tmp_path):
    sandbox = FakeSandbox(every_image_present=False, present={GRADLE_IMAGE})
    lab = kotlin_rig(tmp_path, sandbox)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (NEEDS_DOCKER, NO_KOTLIN_IMAGE)
    assert (sidecar_steps(sandbox), sandbox.called("pull")) == ([], [])


def test_the_kotlin_sidecar_asks_for_the_glibc_image_only(tmp_path):
    sandbox = FakeSandbox(every_image_present=False, present={GRADLE_GLIBC_IMAGE})
    lab = kotlin_rig(tmp_path, sandbox)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    assert sidecar_steps(sandbox)[:2] == ["sidecar", "sidecar_command"]
