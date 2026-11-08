"""The real gopls behind a session (docs/specs/web-ui.md#testing, ADR 0018 phase 3): the version
the selected Go pins, built with `go install` into `.cs/lsp/bin/` as `cstudy doctor --fix` builds
it, answers a page that opens a Go practice file: an undefined name is an error and an unused
variable is tagged Unnecessary; `strings.Split` has documentation whose link into GOROOT is a
button, and the linked file can be read; the definition of `Split` is GOROOT's source, read
through the broker; completion after `strings.` lists `Split` with its documentation. A
reference in `.cs/build/go/` stays out of gopls's reach: its function is undefined in the
practice file. Nothing is written into the root.

Needs Go and, the first time, the network for `go install`, whose binary stays in pytest's cache;
the tests are skipped otherwise."""

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
from coding_study.application.ports import VersionPrinted
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import GOPLS, LSP_BIN, LSP_DIRECTORY
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app

pytestmark = pytest.mark.slow

SERVER_SECONDS = 120
"""Generous: gopls loads the standard library's packages first, and the machine is often loaded."""
GO_WORK = "go 1.24\n\nuse ./go\n"
GO_MOD = "module workspace\n\ngo 1.24\n"
REFERENCE = "package two_sum\n\nfunc Reference() int { return 1 }\n"
SOURCE = """package two_sum

import "strings"

func TwoSum(nums []int, target int) []int {
\tvar unused int
\tparts := strings.Split("a b", " ")
\treturn helper(sqrt(len(parts)), Reference())
}

func helper(value int, other int) []int { return []int{value, other} }
"""
LINES = SOURCE.splitlines()
SPLIT = {"line": 6, "character": LINES[6].index("Split") + 1}
AFTER_STRINGS_DOT = {"line": 6, "character": LINES[6].index("strings.") + len("strings.")}
PRACTICE_FILE = "go/practice/two_sum/two_sum.go"
LIBRARY_LINK = 'class="cs-library-link" data-uri="'


@pytest.fixture(scope="module")
def built(pytestconfig: pytest.Config) -> Path:
    """`.cs/lsp/bin/` in pytest's cache, holding the gopls the selected Go pins, built the first
    time as `cstudy doctor --fix` builds it."""
    assert pytestconfig.cache is not None
    cache = pytestconfig.cache.mkdir("gopls-workspace")
    directory = LspDirectory(cache, SubprocessToolProbe(), SubprocessCommandRunner())
    release = directory.go_release()
    install = GOPLS.go_install
    if release is None or install is None:
        pytest.skip("gopls needs Go on PATH")
    version = install.version_for(release)
    if directory.probe(GOPLS) != VersionPrinted(f"golang.org/x/tools/gopls v{version}\n"):
        result = directory.go_install(install, version)
        if result is None or result.exit_code != 0:
            pytest.skip(f"gopls could not be built: {result.output if result else 'no go'}")
    return cache / LSP_DIRECTORY / LSP_BIN


@dataclass
class Played:
    root: Path
    document: str
    version: Any
    errors: list[str]
    unnecessary: list[str]
    hover: dict[str, Any]
    linked_library: dict[str, Any]
    definition: Any
    library: dict[str, Any]
    completion: list[dict[str, Any]]


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


def _linked_uri(html: str) -> str:
    """The file the first library-link button of hover HTML names, without its fragment."""
    start = html.index(LIBRARY_LINK) + len(LIBRARY_LINK)
    return html[start : html.index('"', start)].partition("#")[0]


@pytest.fixture(scope="module")
def played(built: Path, tmp_path_factory: pytest.TempPathFactory) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-gopls"), PRACTICE, FIXTURE_TRACKS)
    (root / LSP_DIRECTORY).mkdir(parents=True)
    (root / LSP_DIRECTORY / LSP_BIN).symlink_to(built, target_is_directory=True)
    (root / "go.work").write_text(GO_WORK)
    (root / "go").mkdir()
    (root / "go" / "go.mod").write_text(GO_MOD)
    reference = root / ".cs" / "build" / "go" / "practice" / "two_sum" / "reference.go"
    reference.parent.mkdir(parents=True)
    reference.write_text(REFERENCE)
    language_servers = LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner())
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=language_servers,
        content_root=root.parent / "reference-content",
        jdk=EnvJdkSelector(os.environ),
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.GO)).attempt
    practice = root / PRACTICE_FILE
    practice.write_text(SOURCE)
    document = practice.as_uri()

    def at(position: dict[str, int]) -> dict[str, Any]:
        return {"textDocument": {"uri": document}, "position": position}

    app = web_app(root, environment, sessions=LanguageSessions())
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        ask(websocket, request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {"uri": document, "languageId": "go", "version": 1, "text": SOURCE}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        published = until(websocket, lambda message: _has_errors(message, document))
        hover = ask(websocket, request(2, "textDocument/hover", at(SPLIT)))
        linked = _linked_uri(hover["result"]["contents"]["value"])
        linked_library = ask(websocket, request(3, "cstudy/libraryFile", {"uri": linked}))
        definition = ask(websocket, request(4, "textDocument/definition", at(SPLIT)))
        library = ask(
            websocket, request(5, "cstudy/libraryFile", {"uri": _target(definition["result"])})
        )
        completion = ask(websocket, request(6, "textDocument/completion", at(AFTER_STRINGS_DOT)))
    diagnostics = published["params"]["diagnostics"]
    items = completion["result"]
    return Played(
        root,
        document,
        language_servers.probe(GOPLS),
        [d["message"] for d in diagnostics if d["severity"] == 1],
        [d["message"] for d in diagnostics if 1 in d.get("tags", [])],
        hover,
        linked_library,
        definition["result"],
        library,
        items["items"] if isinstance(items, dict) else items,
    )


def _target(result: Any) -> str:
    first = result[0] if isinstance(result, list) else result
    return first.get("uri") or first["targetUri"]


def test_gopls_prints_the_version_the_selected_go_pins(played):
    install = GOPLS.go_install
    assert install is not None
    assert isinstance(played.version, VersionPrinted)
    assert GOPLS.printed_version(played.version.output) in install.versions.values()


def test_an_undefined_name_is_an_error(played):
    assert "undefined: sqrt" in played.errors


def test_an_unused_variable_is_tagged_unnecessary(played):
    assert played.unnecessary == ["declared and not used: unused"]


def test_a_reference_in_the_build_area_is_out_of_goplss_reach(played):
    """No module of the root's `go.work` names `.cs/build/`, so gopls never loads it."""
    assert "undefined: Reference" in played.errors


def test_split_has_documentation_the_page_may_insert(played):
    contents = played.hover["result"]["contents"]
    assert (contents["kind"], "Split slices s into all substrings" in contents["value"]) == (
        "cstudy-html",
        True,
    )


def test_the_hover_shows_no_web_link_to_the_package_documentation(played):
    assert "pkg.go.dev" not in played.hover["result"]["contents"]["value"]


def test_a_documentation_link_into_goroot_can_be_read_as_a_library_file(played):
    result = played.linked_library["result"]
    assert (result["path"].endswith("/src/strings/strings.go"), "func Cut(" in result["text"]) == (
        True,
        True,
    )


def test_the_definition_of_split_is_goroots_source(played):
    assert _target(played.definition).endswith("/src/strings/strings.go")


def test_goroots_source_is_read_through_the_broker(played):
    assert "func Split(" in played.library["result"]["text"]


def test_completion_after_strings_dot_lists_split_with_its_documentation(played):
    split = next(item for item in played.completion if item["label"] == "Split")
    assert split["documentation"]["kind"] == "cstudy-html"


def test_nothing_is_written_into_the_root(played):
    """No `go.sum`, `go.work.sum` or cache beside the module."""
    written = sorted(
        path.relative_to(played.root / "go").as_posix()
        for path in (played.root / "go").rglob("*")
        if path.is_file()
    )
    assert written == ["go.mod", "practice/two_sum/two_sum.go"]
