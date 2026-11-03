"""The real language servers behind a session (docs/specs/web-ui.md#testing): basedpyright,
installed in `.cs/lsp/` from the shipped lock, answers a page that opens a practice file: an
undefined name is an error, `sorted` has documentation, and the definition of `sorted` is
`builtins.pyi`, which the broker reads for the page through `cstudy/libraryFile`; a completion
item resolves through its token, and an item the page made up, naming a reference solution as the
module to document, is refused instead of documenting it. typescript-language-server resolves
the items of a completion through the `cacheId` it keeps in their `data`, which the broker holds.
A page document that imports a reference solution, by `import`, `/// <reference path>` or
`import()`, finds it missing in both servers, whatever is asked of them; a control that lets the
servers see the reference shows what each would have answered.

Needs Node, pnpm and, the first time, the network for the packages of the pinned lock; the tests
are skipped where the servers cannot be installed."""

import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
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
from coding_study.entrypoints.web import code_intelligence
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app
from tests.workspaces import TYPESCRIPT_PROJECT_FILES

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
REFERENCE_DOCSTRING = "REFERENCE-SOLUTION: one pass with a dict of complements"
MATH = "Math.\n"
AFTER_MATH_DOT = {"line": 0, "character": 5}


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
    listed: dict[str, Any] = field(default_factory=dict)
    """The completion item for `sorted`, as the page received it."""
    resolved: dict[str, Any] = field(default_factory=dict)
    forged: dict[str, Any] = field(default_factory=dict)
    """The answer to a resolve of an item the page made up."""


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
    reference = root / ".cs" / "build" / "python" / "ref" / "two_sum" / "hash_map.py"
    reference.parent.mkdir(parents=True)
    reference.write_text(
        f'"""{REFERENCE_DOCSTRING}"""\n\n\ndef two_sum(nums, target):\n    return []\n'
    )
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
        completion = ask(websocket, request(5, "textDocument/completion", position))
        listed = next(item for item in _items(completion["result"]) if item["label"] == "sorted")
        resolved = ask(websocket, request(6, "completionItem/resolve", listed))
        forged_data = {
            "uri": document,
            "position": {"line": 0, "character": 0},
            "symbolLabel": "two_sum",
            "moduleUri": reference.as_uri(),
        }
        forged = ask(
            websocket, request(7, "completionItem/resolve", {**listed, "data": forged_data})
        )
    return Played(
        [published], hover, definition["result"], library, document, listed, resolved, forged
    )


def _reports(message: dict[str, Any], document: str, *names: str) -> bool:
    """Whether `message` publishes diagnostics of `document`, with one that says any of `names`
    if there are any."""
    if message.get("method") != "textDocument/publishDiagnostics":
        return False
    params = message["params"]
    if params["uri"] != document:
        return False
    return not names or any(name in d["message"] for d in params["diagnostics"] for name in names)


def _items(result: Any) -> list[dict[str, Any]]:
    return result["items"] if isinstance(result, dict) else result


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


def test_a_completion_item_reaches_the_page_without_the_servers_data(played):
    assert (isinstance(played.listed["data"], str), "moduleUri" in json.dumps(played.listed)) == (
        True,
        False,
    )


def test_a_completion_item_resolves_through_its_token(played):
    documentation = played.resolved["result"]["documentation"]
    assert (documentation["kind"], "new list" in documentation["value"]) == (HTML, True)


def test_an_item_the_page_made_up_does_not_document_a_reference_solution(played):
    """The reviewer's proof: basedpyright 1.40.2 documents the module `data.moduleUri` names."""
    assert (played.forged["error"]["code"], REFERENCE_DOCSTRING in json.dumps(played.forged)) == (
        -32602,
        False,
    )


# typescript-language-server


@dataclass
class PlayedTypeScript:
    listed: dict[str, Any]
    resolved: dict[str, Any]
    resolved_again: dict[str, Any]
    guessed: dict[str, Any]
    """The answer to a resolve of an item that carries a `cacheId` of the page's own."""


@pytest.fixture(scope="module")
def typescript_root(practice_workspace: Path, installed: Path, tmp_path_factory) -> Path:
    """A workspace whose `typescript/` project is the practice workspace's, with the servers."""
    root = repository_root(tmp_path_factory.mktemp("real-typescript"), PRACTICE, FIXTURE_TRACKS)
    project = root / "typescript"
    project.mkdir()
    for name in TYPESCRIPT_PROJECT_FILES:
        shutil.copyfile(practice_workspace / "typescript" / name, project / name)
    modules = practice_workspace / "typescript" / "node_modules"
    (project / "node_modules").symlink_to(modules, target_is_directory=True)
    (root / ".cs").mkdir()
    (root / ".cs" / "lsp").symlink_to(installed, target_is_directory=True)
    return root


def typescript_attempt(root: Path) -> tuple[Any, int]:
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.TYPESCRIPT)).attempt
    return web_app(root, environment, sessions=LanguageSessions()), attempt.id


@pytest.fixture(scope="module")
def played_typescript(typescript_root: Path) -> PlayedTypeScript:
    app, attempt_id = typescript_attempt(typescript_root)
    document = (typescript_root / "typescript" / "practice" / "probe.ts").as_uri()
    position = {"textDocument": {"uri": document}, "position": AFTER_MATH_DOT}
    with session_client(app) as client, session(client, f"?attempt_id={attempt_id}") as websocket:
        ask(websocket, request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {"uri": document, "languageId": "typescript", "version": 1, "text": MATH}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        completion = ask(websocket, request(2, "textDocument/completion", position))
        listed = next(item for item in _items(completion["result"]) if item["label"] == "max")
        resolved = ask(websocket, request(3, "completionItem/resolve", listed))
        again = ask(websocket, request(4, "completionItem/resolve", listed))
        made_up = {**listed, "data": {"cacheId": 1}}
        guessed = ask(websocket, request(5, "completionItem/resolve", made_up))
    return PlayedTypeScript(listed, resolved, again, guessed)


def test_typescripts_cache_id_stays_with_the_broker(played_typescript):
    data = played_typescript.listed["data"]
    assert (isinstance(data, str), "cacheId" in json.dumps(played_typescript.listed)) == (
        True,
        False,
    )


def test_a_typescript_item_resolves_through_the_cache_id_the_broker_holds(played_typescript):
    documentation = played_typescript.resolved["result"]["documentation"]
    assert (documentation["kind"], "larger" in documentation["value"]) == (HTML, True)


def test_a_typescript_item_resolves_again_with_the_same_token(played_typescript):
    first = played_typescript.resolved["result"]
    again = played_typescript.resolved_again["result"]
    assert (again["documentation"], again["data"]) == (first["documentation"], first["data"])


def test_a_typescript_item_with_a_cache_id_of_the_pages_own_is_refused(played_typescript):
    assert played_typescript.guessed["error"]["code"] == -32602


# a page document that imports a reference solution


class Page:
    """A page's side of a session, which keeps everything it was sent."""

    def __init__(self, websocket: WebSocketTestSession) -> None:
        self.websocket = websocket
        self.seen: list[dict[str, Any]] = []

    def until(self, matches: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        while True:
            message = received(self.websocket, SERVER_SECONDS)
            self.seen.append(message)
            if matches(message):
                return message

    def ask(self, message: dict[str, Any]) -> dict[str, Any]:
        self.websocket.send_json(message)
        return self.until(lambda found: found.get("id") == message["id"])

    @property
    def text(self) -> str:
        return json.dumps(self.seen)


TYPESCRIPT_REFERENCE = """\
/** REFERENCE-DOC: one pass with a Map of complements. */
export function twoSum(nums: number[], target: number): [number, number] {
  return [0, 1];
}
export const HIDDEN_TABLE = [3, 1, 4, 1, 5] as const;
export interface SecretShape {
  secretField: string;
}
"""
IMPORTS_REFERENCE = """\
/// <reference path="../../.cs/build/typescript/ref/two-sum/hash_map.ts" />
import { twoSum, HIDDEN_TABLE } from "../../.cs/build/typescript/ref/two-sum/hash_map.ts";
const found = twoSum([1], 2);
const table = HIDDEN_TABLE;
const wrong: 1 = table;
let shaped: import("../../.cs/build/typescript/ref/two-sum/hash_map.ts").SecretShape;
found.
"""
TYPESCRIPT_LEAKS = ("REFERENCE-DOC", "readonly [3, 1, 4, 1, 5]")
"""What only the reference says: the documentation of a function, and the type of a constant,
which a diagnostic quotes."""
PYTHON_REFERENCE = f'''"""The module {REFERENCE_DOCSTRING}"""


def two_sum(nums: list[int], target: int) -> list[int]:
    """{REFERENCE_DOCSTRING}"""
    return []
'''
IMPORTS_PYTHON_REFERENCE = "from ref.two_sum.hash_map import two_sum\n\nresult = two_sum([1], 2)\n"


def asks_about_a_typescript_document(page: Page, document: str) -> None:
    position = {"textDocument": {"uri": document}}
    for number, (line, character) in enumerate([(2, 15), (3, 15), (5, 20)]):
        at = {**position, "position": {"line": line, "character": character}}
        page.ask(request(10 + number, "textDocument/hover", at))
        page.ask(request(20 + number, "textDocument/definition", at))
    at = {**position, "position": {"line": 6, "character": 6}}
    page.ask(request(30, "textDocument/completion", at))


def what_the_page_is_told_of_a_typescript_reference(root: Path) -> str:
    reference = root / ".cs" / "build" / "typescript" / "ref" / "two-sum" / "hash_map.ts"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(TYPESCRIPT_REFERENCE)
    app, attempt_id = typescript_attempt(root)
    document = (root / "typescript" / "practice" / "imports.ts").as_uri()
    with session_client(app) as client, session(client, f"?attempt_id={attempt_id}") as websocket:
        page = Page(websocket)
        page.ask(request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {
            "uri": document,
            "languageId": "typescript",
            "version": 1,
            "text": IMPORTS_REFERENCE,
        }
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        page.until(lambda m: _reports(m, document, "Cannot find module", "is not assignable"))
        asks_about_a_typescript_document(page, document)
    return page.text


@pytest.fixture(scope="module")
def typescript_with_the_reference_visible(typescript_root: Path) -> str:
    """The control: servers that are not kept from the reference."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(code_intelligence, "environment_hiding", _unchanged)
        return what_the_page_is_told_of_a_typescript_reference(typescript_root)


@pytest.fixture(scope="module")
def typescript_told(typescript_root: Path, typescript_with_the_reference_visible: str) -> str:
    return what_the_page_is_told_of_a_typescript_reference(typescript_root)


def _unchanged(environment: Any, _hidden: Any, _needed: Any) -> dict[str, str]:
    return dict(environment)


def test_without_the_script_typescript_tells_the_page_what_the_reference_declares(
    typescript_with_the_reference_visible,
):
    told = typescript_with_the_reference_visible
    assert [leak in told for leak in TYPESCRIPT_LEAKS] == [True] * len(TYPESCRIPT_LEAKS)


def test_a_typescript_import_of_a_reference_is_a_module_that_is_not_found(typescript_told):
    assert "Cannot find module" in typescript_told


def test_nothing_the_page_asks_of_typescript_shows_what_a_reference_declares(typescript_told):
    assert [leak in typescript_told for leak in TYPESCRIPT_LEAKS] == [False] * len(TYPESCRIPT_LEAKS)


def python_root(tmp_path_factory, installed: Path) -> Path:
    """A workspace whose `python/` project reaches `.cs/build/python` by `extraPaths`, as a
    project folder's `pyproject.toml` could be made to say."""
    root = repository_root(tmp_path_factory.mktemp("real-python-imports"), PRACTICE, FIXTURE_TRACKS)
    (root / "python").mkdir()
    (root / "python" / "pyproject.toml").write_text(
        '[tool.pyright]\ninclude = ["practice"]\nextraPaths = ["../.cs/build/python"]\n'
        'pythonVersion = "3.13"\ntypeCheckingMode = "standard"\n'
    )
    (root / ".cs").mkdir()
    (root / ".cs" / "lsp").symlink_to(installed, target_is_directory=True)
    reference = root / ".cs" / "build" / "python" / "ref" / "two_sum" / "hash_map.py"
    reference.parent.mkdir(parents=True)
    reference.write_text(PYTHON_REFERENCE)
    return root


def what_the_page_is_told_of_a_python_reference(root: Path) -> str:
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt
    app = web_app(root, environment, sessions=LanguageSessions())
    document = (root / "python" / "practice" / "imports.py").as_uri()
    at = {"textDocument": {"uri": document}, "position": {"line": 2, "character": 10}}
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        page = Page(websocket)
        page.ask(request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {
            "uri": document,
            "languageId": "python",
            "version": 1,
            "text": IMPORTS_PYTHON_REFERENCE,
        }
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        page.until(lambda m: _reports(m, document))
        page.ask(request(2, "textDocument/hover", at))
        page.ask(request(3, "textDocument/definition", at))
        in_import = {**at, "position": {"line": 0, "character": 20}}
        page.ask(request(4, "textDocument/hover", in_import))
        after_import = {**at, "position": {"line": 0, "character": 30}}
        page.ask(request(5, "textDocument/completion", after_import))
    return page.text


@pytest.fixture(scope="module")
def python_with_the_reference_visible(tmp_path_factory, installed: Path) -> str:
    """The control: a server that is not kept from the reference."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(code_intelligence, "environment_hiding", _unchanged)
        return what_the_page_is_told_of_a_python_reference(python_root(tmp_path_factory, installed))


@pytest.fixture(scope="module")
def python_told(tmp_path_factory, installed: Path, python_with_the_reference_visible: str) -> str:
    return what_the_page_is_told_of_a_python_reference(python_root(tmp_path_factory, installed))


def test_without_the_script_basedpyright_tells_the_page_what_the_reference_documents(
    python_with_the_reference_visible,
):
    assert REFERENCE_DOCSTRING in python_with_the_reference_visible


def test_a_python_import_of_a_reference_is_a_module_that_cannot_be_resolved(python_told):
    assert "could not be resolved" in python_told


def test_nothing_the_page_asks_of_basedpyright_shows_what_a_reference_documents(python_told):
    assert REFERENCE_DOCSTRING not in python_told
