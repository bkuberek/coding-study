"""The real JDT LS behind a session (docs/specs/web-ui.md#testing, ADR 0018 phase 2): the pinned
milestone, downloaded and checked by its SHA-256 as `cstudy doctor --fix` does, runs on the
selected JDK and answers a page that opens a Java practice file: an undefined method is an error,
`List.add` has documentation, a method of the file is its own definition, and a class of the JDK is
a `jdt://` URI that the broker refuses to read as a file, naming the class. Completion after
`Math.ma` lists `max`. Nothing is written into the root: JDT LS keeps its Eclipse files, its index
and its caches in the session's data directory under `.cs/lsp/`.

The root here holds no Gradle build, so JDT LS imports no project and needs no Gradle warm-up.
Needs a selected JDK 25 or 26 and, the first time, the network for the milestone, which stays in
pytest's cache; the tests are skipped otherwise."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import WebSocketTestSession

from coding_study.adapters.jdk_locator import EnvJdkSelector
from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.application.ports import Unpacked
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import JDTLS, LSP_DIRECTORY
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app

pytestmark = pytest.mark.slow

SERVER_SECONDS = 180
"""Generous: JDT LS indexes the JDK on its first start, and the machine is often loaded."""
SOURCE = """package practice.two_sum;

import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        List<Integer> seen = new ArrayList<>();
        seen.add(1);
        int top = Math.max(1, 2);
        return helper(sqrt(top));
    }

    int[] helper(int value) { return new int[] {value}; }
}
"""
LINES = SOURCE.splitlines()
ADD = {"line": 7, "character": LINES[7].index("add") + 1}
ARRAY_LIST = {"line": 6, "character": LINES[6].index("ArrayList") + 1}
HELPER = {"line": 9, "character": LINES[9].index("helper") + 1}
AFTER_MATH_MA = {"line": 8, "character": LINES[8].index("Math.") + len("Math.ma")}
"""After `Math.ma`: the list after `Math.` alone is cut at 50 items, in alphabetical order."""
HELPER_DEFINITION_LINE = 12
PRACTICE_FILE = "jvm/java/src/main/java/practice/two_sum/Solution.java"


@pytest.fixture(scope="module")
def jdk_home() -> Path:
    selector = EnvJdkSelector(os.environ)
    selected, home = selector.selected(), selector.selected_home()
    jdks = JDTLS.jdks
    if selected is None or home is None or jdks is None or not jdks.contains(selected.feature):
        pytest.skip("JDT LS needs a selected JDK 25 or 26")
    return home


@pytest.fixture(scope="module")
def unpacked(pytestconfig: pytest.Config, jdk_home: Path) -> Path:
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
    return cache / LSP_DIRECTORY / "jdtls"


@dataclass
class Played:
    root: Path
    document: str
    error_messages: list[str]
    hover: dict[str, Any]
    own_definition: Any
    jdk_definition: Any
    jdk_library: dict[str, Any]
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


def _has_errors(message: dict[str, Any], document: str) -> bool:
    if message.get("method") != "textDocument/publishDiagnostics":
        return False
    params = message["params"]
    return params["uri"] == document and any(d["severity"] == 1 for d in params["diagnostics"])


@pytest.fixture(scope="module")
def played(unpacked: Path, jdk_home: Path, tmp_path_factory: pytest.TempPathFactory) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-jdtls"), PRACTICE, FIXTURE_TRACKS)
    (root / LSP_DIRECTORY).mkdir(parents=True)
    (root / LSP_DIRECTORY / "jdtls").symlink_to(unpacked, target_is_directory=True)
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
        jdk=EnvJdkSelector(os.environ),
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.JAVA)).attempt
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
        opened = {"uri": document, "languageId": "java", "version": 1, "text": SOURCE}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        published = until(websocket, lambda message: _has_errors(message, document))
        hover = ask(websocket, request(2, "textDocument/hover", at(ADD)))
        own = ask(websocket, request(3, "textDocument/definition", at(HELPER)))
        jdk = ask(websocket, request(4, "textDocument/definition", at(ARRAY_LIST)))
        library = ask(websocket, request(5, "cstudy/libraryFile", {"uri": _target(jdk["result"])}))
        completion = ask(websocket, request(6, "textDocument/completion", at(AFTER_MATH_MA)))
    errors = [d["message"] for d in published["params"]["diagnostics"] if d["severity"] == 1]
    items = completion["result"]
    labels = [item["label"] for item in (items["items"] if isinstance(items, dict) else items)]
    return Played(root, document, errors, hover, own["result"], jdk["result"], library, labels)


def _target(result: Any) -> str:
    first = result[0] if isinstance(result, list) else result
    return first.get("uri") or first["targetUri"]


def _line(result: Any) -> int:
    first = result[0] if isinstance(result, list) else result
    return (first.get("range") or first["targetSelectionRange"])["start"]["line"]


def test_an_undefined_method_is_an_error(played):
    assert any("sqrt(int) is undefined" in message for message in played.error_messages)


def test_list_add_has_documentation_the_page_may_insert(played):
    contents = played.hover["result"]["contents"]
    assert (contents["kind"], "Appends the specified element" in contents["value"]) == (
        "cstudy-html",
        True,
    )


def test_a_method_of_the_file_is_defined_in_the_file(played):
    assert (_target(played.own_definition), _line(played.own_definition)) == (
        played.document,
        HELPER_DEFINITION_LINE,
    )


def test_a_class_of_the_jdk_is_a_jdt_uri(played):
    assert _target(played.jdk_definition).startswith("jdt://contents/java.base/java.util/")


def test_a_class_of_the_jdk_is_refused_as_a_file_naming_the_class(played):
    assert played.jdk_library["error"]["data"] == {
        "reason": "not_a_file_uri",
        "path": "java.base/java.util/ArrayList.java",
    }


def test_completion_after_math_ma_lists_max(played):
    assert "max" in played.completion_labels


def test_nothing_is_written_into_the_root(played):
    """No `.project`, `.classpath`, `.settings/` or `bin/` beside the practice files."""
    written = sorted(
        path.relative_to(played.root / "jvm").as_posix()
        for path in (played.root / "jvm").rglob("*")
        if path.is_file()
    )
    assert written == ["java/src/main/java/practice/two_sum/Solution.java"]


def test_jdtls_keeps_its_workspace_in_the_sessions_data_directory(played):
    data = played.root / LSP_DIRECTORY / "jdtls-data" / "jvm" / "1"
    assert sorted(path.name for path in data.iterdir()) == ["cache", "configuration", "workspace"]


def test_the_milestone_was_checked_and_unpacked_where_the_doctor_puts_it(unpacked):
    assert (unpacked / "plugins" / "org.eclipse.jdt.ls.core_1.63.0.202610191322.jar").is_file()
