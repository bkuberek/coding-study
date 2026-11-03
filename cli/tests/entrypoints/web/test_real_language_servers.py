"""The real language servers behind a session (docs/specs/web-ui.md#testing): basedpyright,
installed in `.cs/lsp/` from the shipped lock, answers a page that opens a practice file: an
undefined name is an error, `sorted` has documentation, and the definition of `sorted` is
`builtins.pyi`, which the broker reads for the page through `cstudy/libraryFile`.

Needs Node, pnpm and, the first time, the network for the packages of the pinned lock; the tests
are skipped where the servers cannot be installed."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import WebSocketTestSession

from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        shutil.which("node") is None or shutil.which("pnpm") is None,
        reason="node and pnpm are not installed",
    ),
]

SERVER_SECONDS = 120
"""Generous: the machine running the slow tests is often loaded."""
SOURCE = "total = undefined_name + 1\nprint(sorted([3, 1, 2]))\n"
SORTED = {"line": 1, "character": 8}
"""Inside `sorted` on the second line."""
HTML = "cstudy-html"


@pytest.fixture(scope="module")
def installed(practice_workspace: Path) -> Path:
    """`.cs/lsp/` of the practice workspace with the shipped manifest installed."""
    directory = LspDirectory(practice_workspace, SubprocessToolProbe(), SubprocessCommandRunner())
    result = directory.install()
    if result is None or result.exit_code != 0:
        pytest.skip(
            f"the language servers are not installed in .cs/lsp/: {result and result.output}"
        )
    return practice_workspace / ".cs" / "lsp"


@dataclass
class Played:
    diagnostics: list[dict[str, Any]]
    hover: dict[str, Any]
    definition: Any
    library: dict[str, Any]
    document: str


def ask(websocket: WebSocketTestSession, message: dict[str, Any]) -> dict[str, Any]:
    """Sends a request and reads until its answer, leaving out what the server sends meanwhile."""
    websocket.send_json(message)
    return until(websocket, lambda found: found.get("id") == message["id"])


def until(
    websocket: WebSocketTestSession, matches: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    while True:
        message = received(websocket, SERVER_SECONDS)
        if matches(message):
            return message


@pytest.fixture(scope="module")
def played(practice_workspace: Path, installed: Path, tmp_path_factory) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-servers"), PRACTICE, FIXTURE_TRACKS)
    python = root / "python"
    python.mkdir()
    shutil.copyfile(practice_workspace / "python" / "pyproject.toml", python / "pyproject.toml")
    (python / ".venv").symlink_to(practice_workspace / "python" / ".venv", target_is_directory=True)
    (root / ".cs").mkdir()
    (root / ".cs" / "lsp").symlink_to(installed, target_is_directory=True)
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt
    practice = python / "practice" / "two_sum.py"
    practice.write_text(SOURCE)
    document = practice.as_uri()
    position = {"textDocument": {"uri": document}, "position": SORTED}
    app = web_app(root, environment, sessions=LanguageSessions())
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        ask(websocket, request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {"uri": document, "languageId": "python", "version": 1, "text": SOURCE}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        published = until(websocket, lambda m: _reports(m, document, "undefined_name"))
        hover = ask(websocket, request(2, "textDocument/hover", position))
        definition = ask(websocket, request(3, "textDocument/definition", position))
        library = ask(
            websocket, request(4, "cstudy/libraryFile", {"uri": _target(definition["result"])})
        )
    return Played([published], hover, definition["result"], library, document)


def _reports(message: dict[str, Any], document: str, name: str) -> bool:
    if message.get("method") != "textDocument/publishDiagnostics":
        return False
    params = message["params"]
    return params["uri"] == document and any(name in d["message"] for d in params["diagnostics"])


def _target(result: Any) -> str:
    first = result[0] if isinstance(result, list) else result
    return first.get("uri") or first["targetUri"]


def test_an_undefined_name_is_an_error(played):
    (published,) = played.diagnostics
    undefined = [d for d in published["params"]["diagnostics"] if "undefined_name" in d["message"]]
    assert [diagnostic["severity"] for diagnostic in undefined] == [1]


def test_sorted_has_documentation_the_page_may_insert(played):
    contents = played.hover["result"]["contents"]
    assert (contents["kind"], "new list" in contents["value"], "<script" in contents["value"]) == (
        HTML,
        True,
        False,
    )


def test_the_definition_of_sorted_is_builtins_pyi(played):
    assert _target(played.definition).endswith("/builtins.pyi")


def test_builtins_pyi_is_read_through_the_broker(played):
    result = played.library["result"]
    assert (result["path"].endswith("builtins.pyi"), "def sorted(" in result["text"]) == (
        True,
        True,
    )
