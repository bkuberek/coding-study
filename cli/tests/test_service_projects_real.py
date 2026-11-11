"""A service project from `cstudy start` to the last `cstudy submit`, in TypeScript, Python, Java
and Go, on a real Docker engine, and its code intelligence from inside the sidecar. Run with
`uv run pytest -q -m docker`; the Java cases are also marked `docker_jvm`, and the Go ones
`docker_go`, which CI deselects. The waits are generous for a busy machine: what these tests assert
is what happened, not how fast."""

import itertools
import json
import os
import shutil
import time
from collections.abc import Callable, Generator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from starlette.testclient import WebSocketTestSession

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.adapters.workspace_marker import record_license
from coding_study.application.ports import Fetched, NoBuild, Unpacked
from coding_study.domain.code_intelligence import (
    JDTLS,
    JDTLS_DIRECTORY,
    KOTLIN_LSP_DIRECTORY,
    KOTLIN_LSP_LICENSE,
    KOTLIN_LSP_LINUX,
    LSP_DIRECTORY,
)
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.sandbox import workspace_digest
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.helpers import SCHEMAS_DIRECTORY
from tests.language_server_scripts import notification, request
from tests.language_sessions import received, session
from tests.real_service_projects import (
    GO,
    JAVA,
    KOTLIN,
    MEMBERS,
    PYTHON,
    TYPESCRIPT,
    FixtureProject,
    catalog_project,
    docker,
    fixture_project,
)
from tests.waits import GENEROUS_WAIT_S
from tests.web_server import session_client, web_app

pytestmark = [pytest.mark.slow, pytest.mark.docker]

EXIT_OK = 0
EXIT_FAILURES = 1
ACCEPT_LICENSE_VARIABLE = "CSTUDY_ACCEPT_LICENSE"
PULL_PAUSE_S = 1.0


@pytest.fixture(scope="module", autouse=True)
def require_engine() -> None:
    try:
        if docker("info", "--format", "{{.ServerVersion}}").returncode != 0:
            pytest.skip("no running Docker engine")
    except FileNotFoundError:
        pytest.skip("no docker on PATH")


@pytest.fixture(
    params=[
        TYPESCRIPT,
        PYTHON,
        pytest.param(JAVA, marks=pytest.mark.docker_jvm),
        pytest.param(GO, marks=pytest.mark.docker_go),
    ],
    ids=["typescript", "python", "java", "go"],
)
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
    assert installed(project)
    nothing_running(project)


def installed(project: FixtureProject) -> bool:
    """`node_modules` or `.venv` in the folder, or Gradle's user home or Go's modules in the
    install cache."""
    in_folder = any(project.folder.glob("node_modules")) or any(project.folder.glob(".venv"))
    return in_folder or bool(project.labelled("volumes"))


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


@pytest.fixture
def typescript(tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(TYPESCRIPT, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


REACH_THE_MOCK_SERVER = (
    "fetch('http://room-vendor:8080/v1/rooms')"
    ".then((answer) => console.log(`room-vendor answered ${answer.status}`))"
    ".catch((error) => { console.log(String(error)); process.exit(1); })"
)
"""Only a container on the dev stack's network can name the mock server."""


def test_dev_exec_runs_a_command_in_the_dev_stack_and_takes_it_down(typescript: FixtureProject):
    started = typescript.cstudy("start", typescript.slug, "--yes", "--no-open")
    assert started.returncode == EXIT_OK, said(started)

    result = typescript.cstudy("dev", "--exec", "--", "node", "-e", REACH_THE_MOCK_SERVER)

    assert result.returncode == EXIT_OK, said(result)
    assert "room-vendor answered 200" in result.stdout
    nothing_running(typescript)


def test_test_events_stream_the_stack_the_command_and_the_visible_cases(
    typescript: FixtureProject,
):
    """`cstudy test --events`, as the Web UI starts it, on the starter: the stack's stages up to
    down, `commands.test` as one test, each visible case, and nothing left running."""
    assert typescript.cstudy("start", typescript.slug, "--yes", "--no-open").returncode == EXIT_OK

    result = typescript.cstudy("test", "--events")

    events: list[dict[str, Any]] = [json.loads(line) for line in result.stdout.splitlines()]
    validator = Draft202012Validator(
        json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
    )
    for event in events:
        validator.validate(event)
    stages = [event["stack"] for event in events if "stack" in event]
    assert stages[-3:] == ["starting", "ready", "stopped"], said(result)
    tests = [event["id"] for event in events if event["type"] == "test_result"]
    assert tests == ["commands.test"]
    assert [event["type"] for event in events].count("case_result") == 2
    assert (events[-1]["type"], events[-1]["exit_code"]) == ("run_end", EXIT_FAILURES)
    assert result.returncode == EXIT_FAILURES
    nothing_running(typescript)


def test_verify_require_ready_passes_on_the_reference(project: FixtureProject):
    result = project.cstudy("verify", project.slug, "--require-ready")

    assert result.returncode == EXIT_OK, said(result)
    nothing_running(project)


@pytest.fixture
def java(tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(JAVA, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


@pytest.mark.docker_jvm
def test_a_jvm_project_builds_from_its_install_cache_with_no_volume_of_the_images_own(
    java: FixtureProject,
):
    """The install cache is Gradle's user home in every container of the app, and the image's
    `VOLUME` is a tmpfs, so Docker makes no anonymous volume there for the dev stack to leave.
    What stays is what stays by design: the dev stack's data and the install cache."""
    assert java.cstudy("start", java.slug, "--yes", "--no-open").returncode == EXIT_OK

    result = java.cstudy(
        "dev", "--exec", "--", "grep", "-E", " /(cache|home/gradle/.gradle) ", "/proc/mounts"
    )

    assert result.returncode == EXIT_OK, said(result)
    assert "tmpfs /home/gradle/.gradle tmpfs" in result.stdout
    assert " /cache " in result.stdout
    stacks = (
        f"cstudy-d-{java.slug}-{workspace_of(java)}",
        f"cstudy-i-{java.slug}-{workspace_of(java)}",
    )
    assert sorted(java.labelled("volumes")) == [f"{stacks[0]}_data", f"{stacks[1]}_cache"]
    nothing_running(java)


def workspace_of(project: FixtureProject) -> str:
    return workspace_digest(str(project.root.resolve()))


@pytest.fixture
def go(tmp_path: Path) -> Generator[FixtureProject]:
    found = fixture_project(GO, tmp_path)
    try:
        yield found
    finally:
        found.remove_all_it_left()


WHERE_GO_CMP_LIVES = ("go", "list", "-m", "-f", "{{.Dir}}", "github.com/google/go-cmp")


@pytest.mark.docker_go
def test_a_go_project_builds_offline_from_the_modules_in_its_install_cache(go: FixtureProject):
    """`install` downloads the starter's one module into the install cache, and every other
    command reads it there with `GOPROXY=off`: a module cache with nothing in it fails at once,
    with Go's own reason, rather than reaching for a proxy. What stays is what stays by design."""
    assert go.cstudy("start", go.slug, "--yes", "--no-open").returncode == EXIT_OK

    cached = go.cstudy("dev", "--exec", "--", *WHERE_GO_CMP_LIVES)
    empty = go.cstudy("dev", "--exec", "--", "env", "GOMODCACHE=/tmp/none", "go", "vet", "./...")

    assert cached.returncode == EXIT_OK, said(cached)
    assert "/cache/go/mod/github.com/google/go-cmp@v0.7.0" in cached.stdout
    assert empty.returncode != EXIT_OK, said(empty)
    assert "module lookup disabled by GOPROXY=off" in said(empty)
    stacks = (
        f"cstudy-d-{go.slug}-{workspace_of(go)}",
        f"cstudy-i-{go.slug}-{workspace_of(go)}",
    )
    assert sorted(go.labelled("volumes")) == [f"{stacks[0]}_data", f"{stacks[1]}_cache"]
    nothing_running(go)


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
# dependencies; once it ends, nothing of cstudy's is left. Needs Node and pnpm for `.cs/lsp/`,
# and for Java the network the first time, for JDT LS, which then stays in pytest's cache.


@dataclass(frozen=True, slots=True)
class Opened:
    """A file of the fixture, the text the page opens it with, what it is wrong about, where a
    hover lands, and where a definition is asked for, which leads into the project's own
    dependencies."""

    path: str
    language_id: str
    text: str
    error: str
    """Words of the error the server reports for `text`."""
    hover_at: dict[str, int]
    hovered: str
    """Words of the hover there."""
    defined_at: dict[str, int]
    defined_in: str
    """Where in the project folder the definition's file is."""
    defined_elsewhere: str | None = None
    """The start of the definition's URI when it is outside the project folder: a `jdt://` URI of
    a class in a jar, or a file of the install cache, which only the sidecar has."""
    library_refusal: dict[str, str] | None = None
    """What the library tab says of such a definition, which it cannot read on this machine."""
    pulled: bool = False
    """For a server that answers diagnostics only when asked, as the Kotlin LSP does."""


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
    defined_at={"line": 0, "character": 10},
    defined_in="node_modules/",
)
"""`createServer`'s types come from the project's own `@types/node` in its `node_modules`."""
PYTHON_FILE = Opened(
    path="src/server.py",
    language_id="python",
    text="import json\n\nimport pytest\n\nprint(json.dumps({}) + 1, pytest)\n",
    error="Operator",
    hover_at={"line": 4, "character": 12},
    hovered="dumps",
    defined_at={"line": 2, "character": 8},
    defined_in=".venv/lib/",
)
"""`pytest` is installed in the project's `.venv` only, by `uv sync` in Docker."""
JAVA_SOURCES = Path(__file__).parent / "fixtures/service_projects" / JAVA / "starter/src/main/java"
JAVA_FILE = Opened(
    path="src/main/java/rooms/Server.java",
    language_id="java",
    text=(JAVA_SOURCES / "rooms" / "Server.java")
    .read_text()
    .replace("int port = Integer.parseInt", "String port = Integer.parseInt"),
    error="Type mismatch: cannot convert from int to String",
    hover_at={"line": 12, "character": 26},
    hovered="JsonMapper",
    defined_at={"line": 12, "character": 26},
    defined_in="",
    defined_elsewhere="jdt://contents/jackson-databind-3.3.0.jar/",
    library_refusal={
        "reason": "not_a_file_uri",
        "path": "jackson-databind-3.3.0.jar/tools.jackson.databind.json/JsonMapper.java",
    },
)
"""`JsonMapper` comes from jackson-databind, which the install put in the install cache: JDT LS
imports the Gradle build offline over it, read-only."""
GO_TEST = Path(__file__).parent / "fixtures/service_projects" / GO / "starter/main_test.go"
GO_FILE = Opened(
    path="main_test.go",
    language_id="go",
    text=GO_TEST.read_text().replace(
        "var body map[string]string", "var body map[string]string = 3"
    ),
    error="cannot use 3",
    hover_at={"line": 25, "character": 16},
    hovered="Diff",
    defined_at={"line": 25, "character": 16},
    defined_in="",
    defined_elsewhere="file:///cache/go/mod/github.com/google/go-cmp@v0.7.0/cmp/",
    library_refusal={"reason": "missing"},
)
"""`cmp.Diff` comes from go-cmp, which the install put in the install cache, where the sidecar's
gopls reads it and this machine has no file."""
KOTLIN_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "problems"
    / KOTLIN
    / "starter/src/main/kotlin/coworking/DeskInventory.kt"
)
KOTLIN_TEXT = KOTLIN_SOURCE.read_text().replace(
    "fun availableOn(day: String): Int? = byDay[day]",
    "fun availableOn(day: String): String = byDay[day]",
)
KOTLIN_JSON_LINE = next(
    index for index, line in enumerate(KOTLIN_TEXT.splitlines()) if "Json.decode" in line
)
KOTLIN_JSON = {
    "line": KOTLIN_JSON_LINE,
    "character": KOTLIN_TEXT.splitlines()[KOTLIN_JSON_LINE].index("Json") + 1,
}
KOTLIN_FILE = Opened(
    path="src/main/kotlin/coworking/DeskInventory.kt",
    language_id="kotlin",
    text=KOTLIN_TEXT,
    error="Return type mismatch",
    hover_at=KOTLIN_JSON,
    hovered="Json",
    defined_at=KOTLIN_JSON,
    defined_in="",
    defined_elsewhere="jar:///cache/gradle/caches/modules-2/files-2.1/org.jetbrains.kotlinx/",
    library_refusal={"reason": "not_a_file_uri"},
    pulled=True,
)
"""`Json` comes from kotlinx-serialization, which the install put in the install cache: the
Kotlin LSP's import reads it there, read-only, with the image's Gradle, offline."""
FILES = {
    TYPESCRIPT: TYPESCRIPT_FILE,
    PYTHON: PYTHON_FILE,
    JAVA: JAVA_FILE,
    GO: GO_FILE,
    KOTLIN: KOTLIN_FILE,
}


def patient_language_servers(root: Path) -> LspDirectory:
    """The workspace's servers, whose version checks run on this machine and wait as long as a
    busy machine needs: a check that runs out is no server, and the session would refuse."""
    return LspDirectory(root, SubprocessToolProbe(GENEROUS_WAIT_S), SubprocessCommandRunner())


def jdtls_in_cache(pytestconfig: pytest.Config) -> Path:
    """JDT LS unpacked in pytest's cache, downloaded the first time as `cstudy doctor --fix`
    downloads it."""
    assert pytestconfig.cache is not None
    cache = pytestconfig.cache.mkdir("jdtls-workspace")
    directory = LspDirectory(cache, SubprocessToolProbe(), SubprocessCommandRunner())
    if not isinstance(directory.probe(JDTLS), Unpacked):
        assert JDTLS.archive is not None
        result = directory.download(JDTLS.archive)
        if result.exit_code != 0:
            pytest.skip(f"JDT LS could not be downloaded: {result.output}")
    return cache / LSP_DIRECTORY / JDTLS_DIRECTORY


def kotlin_linux_build_in_cache(pytestconfig: pytest.Config) -> Path:
    """JetBrains' newest Linux build of the Kotlin LSP for this processor, in pytest's cache,
    fetched and checked by its published SHA-256 as `cstudy doctor --fix` fetches it, again once
    a newer one is out; skipped unless you accept its license."""
    accepted = os.environ.get(ACCEPT_LICENSE_VARIABLE, "").split(",")
    if KOTLIN_LSP_LICENSE.key not in accepted:
        pytest.skip(f"the Kotlin LSP's license is not accepted: set {ACCEPT_LICENSE_VARIABLE}")
    assert pytestconfig.cache is not None
    cache = pytestconfig.cache.mkdir("kotlin-lsp-sidecar")
    directory = LspDirectory(cache, SubprocessToolProbe(), SubprocessCommandRunner())
    newest = directory.newest_build(KOTLIN_LSP_LINUX)
    if isinstance(newest, NoBuild):
        pytest.skip(f"no Kotlin LSP build to fetch: {newest.reason}")
    probe = directory.probe(KOTLIN_LSP_LINUX)
    if not isinstance(probe, Fetched) or probe.version != newest.build.version:
        result = directory.install_build(KOTLIN_LSP_LINUX, newest)
        if result.exit_code != 0:
            pytest.skip(f"the Kotlin LSP's Linux build could not be fetched: {result.output}")
    return cache / LSP_DIRECTORY / KOTLIN_LSP_DIRECTORY


def install_kotlin_linux_build(project: FixtureProject, pytestconfig: pytest.Config) -> None:
    """The Linux build and its record in the workspace's `.cs/lsp/kotlin-lsp/`, linked hard from
    pytest's cache, and the license accepted in the workspace's marker, as `--fix` leaves them."""
    fetched = kotlin_linux_build_in_cache(pytestconfig)
    builds = project.root / LSP_DIRECTORY / KOTLIN_LSP_DIRECTORY
    builds.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fetched / "linux", builds / "linux", copy_function=_linked, symlinks=True)
    shutil.copy2(fetched / "linux.json", builds / "linux.json")
    license_ = KOTLIN_LSP_LICENSE
    record_license(project.root, license_.key, license_.name, license_.url)


def _linked(source: str, target: str) -> None:
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def install_servers(project: FixtureProject, pytestconfig: pytest.Config) -> None:
    """The workspace's `.cs/lsp/`, as `cstudy doctor --fix` fills it: JDT LS is copied, not
    linked, since the sidecar mounts `.cs/lsp/` and a link would point outside it. Go's gopls
    needs none: `cstudy start` built it into the install cache, code intelligence being on."""
    if project.directory == GO:
        return
    if project.directory == KOTLIN:
        install_kotlin_linux_build(project, pytestconfig)
        return
    if project.directory == JAVA:
        unpacked = jdtls_in_cache(pytestconfig)
        shutil.copytree(unpacked, project.root / LSP_DIRECTORY / JDTLS_DIRECTORY)
        return
    result = patient_language_servers(project.root).install()
    if result is None or result.exit_code != 0:
        pytest.skip(f"the language servers are not installed: {result and result.output}")


@pytest.fixture(
    scope="module",
    params=[
        TYPESCRIPT,
        PYTHON,
        pytest.param(JAVA, marks=pytest.mark.docker_jvm),
        pytest.param(GO, marks=pytest.mark.docker_go),
        pytest.param(KOTLIN, marks=pytest.mark.docker_jvm),
    ],
    ids=["typescript", "python", "java", "go", "kotlin"],
)
def sidecar_project(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    pytestconfig: pytest.Config,
) -> Generator[FixtureProject]:
    scratch = tmp_path_factory.mktemp("sidecar")
    if request.param == KOTLIN:
        found = catalog_project(request.param, scratch)
    else:
        found = fixture_project(request.param, scratch)
    try:
        FsPreferencesStore(found.root).write(
            preferences_document(Preferences(code_intelligence=True))
        )
        started = found.cstudy("start", found.slug, "--yes", "--no-open")
        assert started.returncode == 0, f"{started.stdout}\n{started.stderr}"
        install_servers(found, pytestconfig)
        yield found
    finally:
        found.remove_all_it_left()


@dataclass
class Played:
    diagnostics: list[dict[str, Any]]
    hover: dict[str, Any]
    definition: str
    """The URI of the first place the definition named."""
    library: dict[str, Any]
    """What `cstudy/libraryFile` answered for that place."""


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
    environment = replace(
        load_environment(
            sidecar_project.root, sidecar_project.environment(), sidecar_project.root.parent
        ),
        language_servers=patient_language_servers(sidecar_project.root),
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
        diagnostics = (
            _pulled(websocket, document, opened.error)
            if opened.pulled
            else until(websocket, lambda message: _reports_on(message, document, opened.error))[
                "params"
            ]["diagnostics"]
        )
        position = {"textDocument": {"uri": document}, "position": opened.hover_at}
        websocket.send_json(request(2, "textDocument/hover", position))
        hover = until(websocket, lambda message: message.get("id") == 2)
        position = {"textDocument": {"uri": document}, "position": opened.defined_at}
        websocket.send_json(request(3, "textDocument/definition", position))
        definition = _first_target(until(websocket, lambda message: message.get("id") == 3))
        websocket.send_json(request(4, "cstudy/libraryFile", {"uri": definition}))
        library = until(websocket, lambda message: message.get("id") == 4)
    return Played(diagnostics, hover, definition, library)


def _pulled(websocket: WebSocketTestSession, document: str, error: str) -> list[dict[str, Any]]:
    """The document's diagnostics, asked for until they hold the error, as the page asks again
    while the server imports and indexes."""
    for request_id in itertools.count(100):
        asked = {"textDocument": {"uri": document}}
        websocket.send_json(request(request_id, "textDocument/diagnostic", asked))
        answer = until(websocket, lambda message, wanted=request_id: message.get("id") == wanted)
        items = (answer.get("result") or {}).get("items") or []
        if any(error in found["message"] for found in items):
            return items
        time.sleep(PULL_PAUSE_S)
    raise AssertionError("unreachable")


def _first_target(answer: dict[str, Any]) -> str:
    found = answer["result"]
    location = found[0] if isinstance(found, list) else found
    return location.get("targetUri") or location["uri"]


def _reports_on(message: dict[str, Any], document: str, error: str) -> bool:
    """A publication of the document's diagnostics that holds the error: JDT LS first publishes
    what it finds before the Gradle import, without it."""
    params = message.get("params") or {}
    return (
        message.get("method") == "textDocument/publishDiagnostics"
        and params.get("uri") == document
        and any(error in found["message"] for found in params.get("diagnostics") or [])
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


def test_a_definition_leads_into_the_projects_installed_dependencies(
    sidecar_project, sidecar_session
):
    opened = FILES[sidecar_project.directory]
    within = opened.defined_elsewhere or (sidecar_project.folder / opened.defined_in).as_uri()

    assert sidecar_session.definition.startswith(within)


def test_the_library_tab_reads_that_file_at_the_same_path_on_this_machine(
    sidecar_project, sidecar_session
):
    """A class in a jar is no file, and a file of the install cache is not on this machine: the
    tab refuses them, saying why."""
    refusal = FILES[sidecar_project.directory].library_refusal
    if refusal is not None:
        data = sidecar_session.library["error"]["data"]
        assert {name: data[name] for name in refusal} == refusal
    else:
        assert sidecar_session.library["result"]["text"]


def test_no_container_is_left_once_the_session_ended(sidecar_project, sidecar_session):
    assert sidecar_project.labelled("containers") == []


def test_no_folder_of_the_sidecar_is_left_once_the_session_ended(sidecar_project, sidecar_session):
    assert not any((sidecar_project.root / ".cs" / "runs").glob("cstudy-l-*"))
