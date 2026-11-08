"""The real rust-analyzer behind a session (docs/specs/web-ui.md#testing, ADR 0018 phase 3): the
one on PATH, from rustup or not, answers a page that opens a Rust practice file. Its own
diagnostics are pulled: an unknown function is an error before any save. After `didSave`, `cargo
check` publishes rustc's unused variable, tagged Unnecessary, into a target directory of its own.
`len` has documentation, and its definition is the standard library's source, read through the
broker; completion after `nums.` lists `len`.

Needs a `rust-analyzer` whose `--version` runs (`rustup component add rust-analyzer`) and cargo;
the tests are skipped otherwise, and when only rustup's proxy of a missing component is there."""

import os
import shutil
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
from coding_study.domain.code_intelligence import RUST_ANALYZER
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.code_intelligence import LanguageSessions
from tests.fakes import FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.language_server_scripts import notification, request
from tests.language_sessions import PRACTICE, STUBS, received, session
from tests.web_server import session_client, web_app

pytestmark = pytest.mark.slow

SERVER_SECONDS = 240
"""Generous: rust-analyzer loads the sysroot, and `cargo check` builds once."""
CARGO_TOML = """[package]
name = "practice"
version = "0.0.0"
edition = "2021"
publish = false

[lib]
path = "lib.rs"
"""
LIB_RS = '#[path = "practice/two_sum.rs"]\npub mod two_sum;\n'
SOURCE = """pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let seen = nums.len();
    let top = sqrt(target);
    vec![top]
}
"""
LINES = SOURCE.splitlines()
LEN = {"line": 1, "character": LINES[1].index("len") + 1}
AFTER_NUMS_DOT = {"line": 1, "character": LINES[1].index("nums.") + len("nums.")}
PRACTICE_FILE = "rust/practice/two_sum.rs"


@pytest.fixture(scope="module")
def on_path() -> VersionPrinted:
    """What `rust-analyzer --version` printed, as the doctor row reads it."""
    if shutil.which("cargo") is None:
        pytest.skip("rust-analyzer needs cargo on PATH")
    probe = LspDirectory(Path.cwd(), SubprocessToolProbe(), SubprocessCommandRunner()).probe(
        RUST_ANALYZER
    )
    if not isinstance(probe, VersionPrinted):
        pytest.skip(f"no rust-analyzer that runs: {probe}; rustup component add rust-analyzer")
    return probe


@dataclass
class Played:
    root: Path
    pulled_errors: list[str]
    published_unnecessary: list[str]
    hover: dict[str, Any]
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


def _pulled_errors(websocket: WebSocketTestSession, document: str) -> list[str]:
    """Pulls the file's diagnostics, again after each refresh, until one is an error."""
    for request_id in range(100, 160):
        report = ask(websocket, request(request_id, "textDocument/diagnostic", _of(document)))
        errors = [d["message"] for d in report["result"].get("items", []) if d["severity"] == 1]
        if errors:
            return errors
        until(websocket, lambda message: message.get("method") == "cstudy/diagnosticRefresh")
    return []


def _published_unnecessary(message: dict[str, Any], document: str) -> list[str]:
    if message.get("method") != "textDocument/publishDiagnostics":
        return []
    params = message["params"]
    if params["uri"] != document:
        return []
    return [d["message"] for d in params["diagnostics"] if 1 in d.get("tags", [])]


def _of(document: str) -> dict[str, Any]:
    return {"textDocument": {"uri": document}}


@pytest.fixture(scope="module")
def played(on_path: VersionPrinted, tmp_path_factory: pytest.TempPathFactory) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-ra"), PRACTICE, FIXTURE_TRACKS)
    (root / "rust").mkdir()
    (root / "rust" / "Cargo.toml").write_text(CARGO_TOML)
    (root / "rust" / "lib.rs").write_text(LIB_RS)
    environment = make_environment(
        root,
        toolchains=FakeToolchains(stub_generators=STUBS),
        language_servers=LspDirectory(root, SubprocessToolProbe(), SubprocessCommandRunner()),
        content_root=root.parent / "reference-content",
        jdk=EnvJdkSelector(os.environ),
    )
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    attempt = start_attempt(environment, StartRequest("two-sum", Language.RUST)).attempt
    practice = root / PRACTICE_FILE
    practice.write_text(SOURCE)
    document = practice.as_uri()

    def at(position: dict[str, int]) -> dict[str, Any]:
        return {**_of(document), "position": position}

    app = web_app(root, environment, sessions=LanguageSessions())
    with session_client(app) as client, session(client, f"?attempt_id={attempt.id}") as websocket:
        ask(websocket, request(1, "initialize", {"capabilities": {}}))
        websocket.send_json(notification("initialized", {}))
        opened = {"uri": document, "languageId": "rust", "version": 1, "text": SOURCE}
        websocket.send_json(notification("textDocument/didOpen", {"textDocument": opened}))
        pulled = _pulled_errors(websocket, document)
        websocket.send_json(notification("textDocument/didSave", _of(document)))
        published = []
        while not published:
            published = _published_unnecessary(received(websocket, SERVER_SECONDS), document)
        hover = ask(websocket, request(2, "textDocument/hover", at(LEN)))
        definition = ask(websocket, request(3, "textDocument/definition", at(LEN)))
        library = ask(
            websocket, request(4, "cstudy/libraryFile", {"uri": _target(definition["result"])})
        )
        completion = ask(websocket, request(5, "textDocument/completion", at(AFTER_NUMS_DOT)))
    items = completion["result"]
    return Played(
        root,
        pulled,
        published,
        hover,
        definition["result"],
        library,
        items["items"] if isinstance(items, dict) else items,
    )


def _target(result: Any) -> str:
    first = result[0] if isinstance(result, list) else result
    return first.get("uri") or first["targetUri"]


def test_rust_analyzer_on_path_prints_a_version(on_path):
    assert RUST_ANALYZER.printed_version(on_path.output) is not None


def test_an_unknown_function_is_a_pulled_error_before_any_save(played):
    assert any("sqrt" in message for message in played.pulled_errors)


def test_cargo_checks_unused_variable_is_published_tagged_unnecessary(played):
    assert any("unused variable" in message for message in played.published_unnecessary)


def test_cargo_check_builds_into_a_target_directory_of_its_own(played):
    assert (played.root / "rust" / "target" / "rust-analyzer").is_dir()


def test_len_has_documentation_the_page_may_insert(played):
    assert played.hover["result"]["contents"]["kind"] == "cstudy-html"


def test_the_definition_of_len_is_the_standard_librarys_source(played):
    assert _target(played.definition).endswith("/core/src/slice/mod.rs")


def test_the_standard_librarys_source_is_read_through_the_broker(played):
    assert "pub const fn len(&self)" in played.library["result"]["text"]


def test_completion_after_nums_dot_lists_len(played):
    assert any(item["label"].startswith("len") for item in played.completion)
