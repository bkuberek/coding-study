"""The real Kotlin LSP behind a session (docs/specs/web-ui.md#testing, ADR 0018, Kotlin
revisited): the pinned build of this machine, downloaded and checked by its SHA-256 as `cstudy
doctor --fix` downloads it once its license is accepted, answers a page that opens a Kotlin
practice file. The page pulls its diagnostics, as the Kotlin LSP answers no others: an unresolved
name and a type mismatch are errors. `add` has documentation, a function of the file is its own
definition, a function of the standard library is a source in a jar that the broker refuses to
read as a file, naming it, and completion after `seen.ad` lists `add`. Nothing but Gradle's own
files is written into the build: the Kotlin LSP keeps its index, configuration and logs in the
session's data directory.

The root holds the practice workspace's `jvm/` build, warmed up by Gradle: the Kotlin LSP
imports it, with the network for the sources of its libraries the first time, as the warm-up of
`cstudy doctor --fix` does. Running it means accepting JetBrains' license for the Kotlin LSP: the
tests are skipped unless `CSTUDY_ACCEPT_LICENSE=kotlin-lsp` says you accept it, without a selected
JDK cstudy supports, once the pinned build has expired, and when the build cannot be downloaded
the first time; it stays in pytest's cache."""

import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import WebSocketTestSession

from coding_study.adapters.jdk_locator import EnvJdkSelector
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.runner_runtime import RUNTIME_DIRECTORY
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.adapters.workspace_marker import record_license
from coding_study.application.ports import Unpacked
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import (
    KOTLIN_LSP,
    KOTLIN_LSP_DIRECTORY,
    KOTLIN_LSP_LICENSE,
    LSP_DIRECTORY,
)
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS, mark_workspace
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app
from tests.workspaces import JVM_COPY_IGNORED

pytestmark = pytest.mark.slow

ACCEPT_VARIABLE = "CSTUDY_ACCEPT_LICENSE"
SERVER_SECONDS = 300
"""Generous: the Kotlin LSP indexes the JDK and its own libraries on its first start, and the
machine is often loaded."""
PULL_PAUSE_S = 1.0
SOURCE = """package practice.two_sum

class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        val seen = mutableListOf<Int>()
        seen.add(target)
        val name: String = seen.size
        return helper(sqrt(target))
    }

    fun helper(value: Int): IntArray = intArrayOf(value)
}
"""
LINES = SOURCE.splitlines()
ADD = {"line": 5, "character": LINES[5].index("add") + 1}
MUTABLE_LIST = {"line": 4, "character": LINES[4].index("mutableListOf") + 1}
HELPER = {"line": 7, "character": LINES[7].index("helper") + 1}
AFTER_SEEN_AD = {"line": 5, "character": LINES[5].index("seen.") + len("seen.ad")}
HELPER_DEFINITION_LINE = 10
PRACTICE_FILE = "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt"


@pytest.fixture(scope="module")
def license_accepted() -> None:
    accepted = os.environ.get(ACCEPT_VARIABLE, "").split(",")
    if KOTLIN_LSP_LICENSE.key not in accepted:
        pytest.skip(
            f"the Kotlin LSP's license is not accepted: set {ACCEPT_VARIABLE}=kotlin-lsp to "
            f"accept the {KOTLIN_LSP_LICENSE.name} ({KOTLIN_LSP_LICENSE.url}) for this test"
        )


@pytest.fixture(scope="module")
def jdk_home() -> Path:
    selector = EnvJdkSelector(os.environ)
    selected, home = selector.selected(), selector.selected_home()
    jdks = KOTLIN_LSP.jdks
    if selected is None or home is None or jdks is None or not jdks.contains(selected.feature):
        pytest.skip("the Kotlin LSP imports with a selected JDK 21 to 26")
    return home


@pytest.fixture(scope="module")
def unpacked(pytestconfig: pytest.Config, license_accepted: None, jdk_home: Path) -> Path:
    """The Kotlin LSP unpacked in pytest's cache, downloaded the first time as `cstudy doctor
    --fix` downloads it."""
    if KOTLIN_LSP.expires is not None and date.today() >= KOTLIN_LSP.expires:
        pytest.skip(f"the pinned Kotlin LSP expired on {KOTLIN_LSP.expires}: pin a newer build")
    assert pytestconfig.cache is not None
    cache = pytestconfig.cache.mkdir("kotlin-lsp-workspace")
    directory = LspDirectory(cache, SubprocessToolProbe(), SubprocessCommandRunner())
    if not isinstance(directory.probe(KOTLIN_LSP), Unpacked):
        archive = KOTLIN_LSP.archive_on(directory.machine)
        if archive is None:
            pytest.skip(f"the Kotlin LSP has no build for {directory.machine}")
        result = directory.download(archive)
        if result.exit_code != 0:
            pytest.skip(f"the Kotlin LSP could not be downloaded: {result.output}")
    return cache / LSP_DIRECTORY / KOTLIN_LSP_DIRECTORY


@dataclass
class Played:
    root: Path
    started: float
    """When the test wrote the practice file, from which nothing but it is new in the build."""
    document: str
    error_messages: list[str]
    hover: dict[str, Any]
    own_definition: Any
    library_definition: Any
    library: dict[str, Any]
    completion_labels: list[str]


def ask(websocket: WebSocketTestSession, message: dict[str, Any]) -> dict[str, Any]:
    websocket.send_json(message)
    return until(websocket, lambda found: found.get("id") == message["id"])


def until(
    websocket: WebSocketTestSession, matches: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        message = received(websocket, SERVER_SECONDS)
        if matches(message):
            return message


def pulled_errors(websocket: WebSocketTestSession, document: str) -> list[str]:
    """Pulls the file's diagnostics until some are errors, as the page pulls again when the
    server asks for a refresh: the Kotlin LSP answers none while it imports and indexes."""
    deadline = time.monotonic() + SERVER_SECONDS
    params = {"textDocument": {"uri": document}}
    for number in range(100, 100_000):
        report = ask(websocket, request(number, "textDocument/diagnostic", params))["result"]
        errors = [d["message"] for d in report.get("items", []) if d["severity"] == 1]
        if errors or time.monotonic() > deadline:
            return errors
        time.sleep(PULL_PAUSE_S)
    return []


@pytest.fixture(scope="module")
def played(
    unpacked: Path,
    jdk_home: Path,
    practice_workspace: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-kotlin-lsp"), PRACTICE, FIXTURE_TRACKS)
    with_the_jvm_build(practice_workspace, root)
    (root / LSP_DIRECTORY).mkdir(parents=True)
    (root / LSP_DIRECTORY / KOTLIN_LSP_DIRECTORY).symlink_to(unpacked, target_is_directory=True)
    license_ = KOTLIN_LSP_LICENSE
    record_license(mark_workspace(root), license_.key, license_.name, license_.url)
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
        jdk=EnvJdkSelector(os.environ),
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.KOTLIN)).attempt
    started = time.time()
    practice = root / PRACTICE_FILE
    practice.parent.mkdir(parents=True, exist_ok=True)
    practice.write_text(SOURCE)
    document = practice.as_uri()

    def at(position: dict[str, int]) -> dict[str, Any]:
        return {"textDocument": {"uri": document}, "position": position}

    app = web_app(root, environment, sessions=LanguageSessions())
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        ask(websocket, request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {"uri": document, "languageId": "kotlin", "version": 1, "text": SOURCE}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        errors = pulled_errors(websocket, document)
        hover = ask(websocket, request(2, "textDocument/hover", at(ADD)))
        own = ask(websocket, request(3, "textDocument/definition", at(HELPER)))
        library = ask(websocket, request(4, "textDocument/definition", at(MUTABLE_LIST)))
        refused = ask(
            websocket, request(5, "cstudy/libraryFile", {"uri": _target(library["result"])})
        )
        completion = ask(websocket, request(6, "textDocument/completion", at(AFTER_SEEN_AD)))
    items = completion["result"]
    labels = [item["label"] for item in (items["items"] if isinstance(items, dict) else items)]
    return Played(
        root, started, document, errors, hover, own["result"], library["result"], refused, labels
    )


def with_the_jvm_build(practice_workspace: Path, root: Path) -> None:
    """The practice workspace's `jvm/` build and runner runtime, warmed up by Gradle, in `root`:
    the Kotlin LSP reads the standard library from the build's libraries. The runtime is a copy,
    not a link: the import refuses an included build whose real path lies elsewhere."""
    shutil.copytree(
        practice_workspace / "jvm", root / "jvm", ignore=JVM_COPY_IGNORED, symlinks=True
    )
    shutil.copytree(
        practice_workspace / RUNTIME_DIRECTORY,
        root / RUNTIME_DIRECTORY,
        ignore=shutil.ignore_patterns(".gradle"),
        symlinks=True,
    )


def _target(result: Any) -> str:
    first = result[0] if isinstance(result, list) else result
    return first.get("uri") or first["targetUri"]


def _line(result: Any) -> int:
    first = result[0] if isinstance(result, list) else result
    return (first.get("range") or first["targetSelectionRange"])["start"]["line"]


def test_an_unresolved_name_is_an_error(played):
    assert any("Unresolved reference 'sqrt'" in message for message in played.error_messages)


def test_a_type_mismatch_is_an_error(played):
    assert any("type mismatch" in message.lower() for message in played.error_messages)


def test_add_has_documentation_the_page_may_insert(played):
    contents = played.hover["result"]["contents"]
    assert (contents["kind"], "Adds the specified element" in contents["value"]) == (
        "cstudy-html",
        True,
    )


def test_a_function_of_the_file_is_defined_in_the_file(played):
    assert (_target(played.own_definition), _line(played.own_definition)) == (
        played.document,
        HELPER_DEFINITION_LINE,
    )


def test_a_function_of_the_standard_library_is_a_source_in_a_jar(played):
    assert _target(played.library_definition).startswith("jar:")


def test_a_source_in_a_jar_is_refused_as_a_file_naming_the_jar_and_the_source(played):
    data = played.library["error"]["data"]
    jar, _, inside = data["path"].partition("!/")
    assert (data["reason"], jar, inside.endswith(".kt")) == (
        "not_a_file_uri",
        "kotlin-stdlib-2.4.21-sources.jar",
        True,
    )


def test_completion_after_seen_ad_lists_add(played):
    assert "add" in played.completion_labels


def test_nothing_but_gradles_own_files_is_written_into_the_build(played):
    """No `.idea/`, `.kotlin/` or build output: the source tree holds the practice file alone,
    and only Gradle writes its `.gradle/`, as it does for `cstudy test`."""
    jvm = played.root / "jvm"
    written = sorted(
        path.relative_to(jvm).as_posix()
        for path in jvm.rglob("*")
        if path.is_file() and path.stat().st_mtime > played.started and ".gradle" not in path.parts
    )
    assert written == ["kotlin/src/main/kotlin/practice/two_sum/Solution.kt"]


def test_the_kotlin_lsp_keeps_its_index_and_logs_in_the_sessions_data_directory(played):
    data = played.root / LSP_DIRECTORY / "kotlin-lsp-data" / "jvm" / "1"
    assert {"system", "log"} <= {path.name for path in data.iterdir()}


def test_the_build_was_checked_and_unpacked_where_the_doctor_puts_it(unpacked):
    assert (unpacked / "kotlin-server-263.7084.0" / "build.txt").is_file()
