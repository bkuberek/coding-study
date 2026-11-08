"""The real rust-analyzer behind a session (docs/specs/web-ui.md#testing, ADR 0018 phase 3): the
one on PATH, from rustup or not, answers a page that opens a Rust practice file in a crate shaped
like the workspace's `rust/`, whose `.cargo/config.toml` replaces crates.io with the runtime's
vendored crates, as the workspace template's does. Its own
diagnostics are pulled as the page pulls them: while it loads its workspace it answers an empty
report, asks for a refresh and cancels pulls (`ServerCancelled`, `retriggerRequest` true), which
are asked again; then a syntax error is a pulled error before any save. Once the error is fixed,
`didSave` makes `cargo check` publish rustc's unused variable, tagged Unnecessary, from a target
directory of its own. `Vec` and `len` have the standard library's documentation, the
definition of `len` is the standard library's source, read through the broker, and completion
after `nums.` lists `len`: the vendored crates.io does not reach the standard library, which
rust-analyzer reads from the links cstudy makes in `.cs/lsp/rust-library/`.

Needs a `rust-analyzer` whose `--version` runs (`rustup component add rust-analyzer`) and cargo;
the tests are skipped otherwise, and when only rustup's proxy of a missing component is there."""

import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
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
PULLS = 120
"""How many pulls the test makes before it gives up on a pulled error: two minutes of a load."""
RETRY_S = 0.5
"""What the page waits before it asks again for a pull the server cancelled, the first time."""
EMPTY_REPORT_WAIT_S = 1.0
SERVER_CANCELLED = -32802
CARGO_TOML = """[package]
name = "practice"
version = "0.0.0"
edition = "2021"
publish = false

[lib]
path = "lib.rs"
"""
LIB_RS = '#[path = "practice/two_sum.rs"]\npub mod two_sum;\n'
CARGO_CONFIG = (
    Path(__file__).parents[3]
    / "src/coding_study/adapters/workspace_template/rust/.cargo/config.toml"
)
"""The workspace template's: crates.io replaced by the runtime's vendored crates."""
VENDORED = ".cs/runtime/runners/rust/vendor"
SOURCE = """pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let seen = nums.len();
    let top = ;
    vec![target]
}
"""
"""A syntax error, which rust-analyzer reports itself; the rest, such as an unknown function, is
`cargo check`'s, published, not pulled."""
FIXED = SOURCE.replace("    let top = ;\n", "")
LINES = FIXED.splitlines()
LEN = {"line": 1, "character": LINES[1].index("len") + 1}
VEC = {"line": 0, "character": LINES[0].index("Vec") + 1}
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
class Exchange:
    """The page's side of a session: what it asks, and every diagnostic the server publishes
    meanwhile, which waiting for an answer must not lose."""

    websocket: WebSocketTestSession
    published: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])

    def receive(self) -> dict[str, Any]:
        message = received(self.websocket, SERVER_SECONDS)
        if message.get("method") == "textDocument/publishDiagnostics":
            self.published.append(message["params"])
        return message

    def ask(self, message: dict[str, Any]) -> dict[str, Any]:
        self.websocket.send_json(message)
        return self.until(lambda found: found.get("id") == message["id"])

    def until(self, matches: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        while not matches(message := self.receive()):
            pass
        return message

    def tell(self, method: str, params: object) -> None:
        self.websocket.send_json(notification(method, params))


@dataclass
class Pulled:
    errors: list[str]
    failures: list[dict[str, Any]]
    """Every error a pull was answered with: a cancellation to ask again, or anything else."""


@dataclass
class Played:
    root: Path
    pulled: Pulled
    published_unnecessary: list[str]
    vec_hover: dict[str, Any]
    hover: dict[str, Any]
    definition: Any
    library: dict[str, Any]
    completion: list[dict[str, Any]]


def pulled(exchange: Exchange, document: str) -> Pulled:
    """Pulls the file's diagnostics as the page does: a cancelled pull again after a short wait,
    an empty report again a little later, as after the server's refresh, until one is an error."""
    failures: list[dict[str, Any]] = []
    for request_id in range(100, 100 + PULLS):
        answer = exchange.ask(request(request_id, "textDocument/diagnostic", _of(document)))
        if "error" in answer:
            failures.append(answer["error"])
            time.sleep(RETRY_S)
            continue
        items = answer["result"].get("items", [])
        errors = [found["message"] for found in items if found.get("severity") == 1]
        if errors:
            return Pulled(errors, failures)
        time.sleep(EMPTY_REPORT_WAIT_S)
    return Pulled([], failures)


def published_unnecessary(exchange: Exchange, document: str) -> list[str]:
    """The diagnostics tagged Unnecessary of the first publication for the file that has one,
    from those already received or the next ones."""
    while True:
        for params in exchange.published:
            tagged = [d["message"] for d in params["diagnostics"] if 1 in d.get("tags", [])]
            if params["uri"] == document and tagged:
                return tagged
        exchange.published.clear()
        exchange.receive()


def _of(document: str) -> dict[str, Any]:
    return {"textDocument": {"uri": document}}


@pytest.fixture(scope="module")
def played(on_path: VersionPrinted, tmp_path_factory: pytest.TempPathFactory) -> Played:
    root = repository_root(tmp_path_factory.mktemp("real-ra"), PRACTICE, FIXTURE_TRACKS)
    (root / "rust").mkdir()
    (root / "rust" / "Cargo.toml").write_text(CARGO_TOML)
    (root / "rust" / "lib.rs").write_text(LIB_RS)
    (root / "rust" / ".cargo").mkdir()
    (root / "rust" / ".cargo" / "config.toml").write_text(CARGO_CONFIG.read_text())
    (root / VENDORED).mkdir(parents=True)
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
        exchange = Exchange(websocket)
        exchange.ask(request(1, "initialize", {"capabilities": {}}))
        exchange.tell("initialized", {})
        opened = {"uri": document, "languageId": "rust", "version": 1, "text": SOURCE}
        exchange.tell("textDocument/didOpen", {"textDocument": opened})
        pulls = pulled(exchange, document)
        practice.write_text(FIXED)
        change = {
            "textDocument": {"uri": document, "version": 2},
            "contentChanges": [{"text": FIXED}],
        }
        exchange.tell("textDocument/didChange", change)
        exchange.published.clear()
        exchange.tell("textDocument/didSave", _of(document))
        unnecessary = published_unnecessary(exchange, document)
        vec_hover = exchange.ask(request(6, "textDocument/hover", at(VEC)))
        hover = exchange.ask(request(2, "textDocument/hover", at(LEN)))
        definition = exchange.ask(request(3, "textDocument/definition", at(LEN)))
        target = {"uri": _target(definition["result"]) or "file:///missing"}
        library = exchange.ask(request(4, "cstudy/libraryFile", target))
        completion = exchange.ask(request(5, "textDocument/completion", at(AFTER_NUMS_DOT)))
    items = completion["result"]
    return Played(
        root,
        pulls,
        unnecessary,
        vec_hover,
        hover,
        definition["result"],
        library,
        items["items"] if isinstance(items, dict) else items,
    )


def _target(result: Any) -> str:
    """The URI of the first location; empty for none, as an answer whose `Vec` did not resolve."""
    first = (result[0] if result else {}) if isinstance(result, list) else (result or {})
    return first.get("uri") or first.get("targetUri", "")


def test_rust_analyzer_on_path_prints_a_version(on_path):
    assert RUST_ANALYZER.printed_version(on_path.output) is not None


def test_a_syntax_error_is_pulled_before_any_save_once_cancelled_pulls_are_asked_again(played):
    """Every pull the server did not answer, it cancelled for the page to ask again."""
    retriggers = [
        failure["code"] == SERVER_CANCELLED
        and failure.get("data", {}).get("retriggerRequest") is True
        for failure in played.pulled.failures
    ]
    assert (any("expected expression" in m for m in played.pulled.errors), all(retriggers)) == (
        True,
        True,
    )


def test_cargo_checks_unused_variable_is_published_tagged_unnecessary(played):
    assert any("unused variable" in message for message in played.published_unnecessary)


def test_cargo_check_builds_into_a_target_directory_of_its_own(played):
    assert (played.root / "rust" / "target" / "rust-analyzer").is_dir()


def test_vec_has_the_standard_librarys_documentation(played):
    contents = (played.vec_hover["result"] or {}).get("contents", {})
    assert "A contiguous growable array type" in contents.get("value", "")


def test_len_has_the_standard_librarys_documentation_the_page_may_insert(played):
    contents = (played.hover["result"] or {}).get("contents", {})
    assert (
        contents.get("kind"),
        "Returns the number of elements in the vector" in contents.get("value", ""),
    ) == (
        "cstudy-html",
        True,
    )


def test_the_definition_of_vecs_len_is_the_standard_librarys_source(played):
    assert _target(played.definition).endswith("/alloc/src/vec/mod.rs")


def test_the_standard_librarys_source_is_read_through_the_broker(played):
    assert "pub const fn len(&self)" in played.library.get("result", {}).get("text", "")


def test_completion_after_nums_dot_lists_len(played):
    assert any(item["label"].startswith("len") for item in played.completion)
