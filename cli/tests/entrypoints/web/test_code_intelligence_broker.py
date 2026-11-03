"""The broker inside a session (docs/specs/web-ui.md#the-broker), through the socket and the
scripted server: `initialize` rebuilt, the server's requests answered without the page,
documentation sent as HTML, library files read, and the workspace's changes passed on. The rules
message by message are in `test_language_broker.py`."""

import os
from collections.abc import Callable, Iterator

import pytest
from starlette.testclient import TestClient

from coding_study.application.attempt_changes import FileChanged
from coding_study.domain.code_intelligence import BASEDPYRIGHT
from coding_study.entrypoints.web.code_intelligence import MESSAGE_LIMIT
from coding_study.entrypoints.web.notifications import Notifications
from tests.language_server_scripts import answer, notification, request
from tests.language_sessions import Rig, closed_with, noticed, received, rig, session
from tests.scripted_runs import eventually
from tests.web_server import TEST_VERSION, session_client

HTML = "cstudy-html"
MIB = 1024 * 1024
OUTSIDE = "file:///etc/passwd"
SENT_ITEM = {"label": "sorted", "data": {"uri": OUTSIDE, "moduleUri": "file:///lib/builtins.pyi"}}
"""A completion item as the server writes it, whose `data` the page never sees."""


@pytest.fixture
def lab(tmp_path) -> Rig:
    return rig(tmp_path)


@pytest.fixture
def client(lab) -> Iterator[TestClient]:
    with session_client(lab.app) as page:
        yield page


def diagnostics(uri: str, message: str = "x") -> dict[str, object]:
    return notification(
        "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": [{"message": message}]}
    )


def message_of(diagnostic: dict[str, object]) -> str:
    return diagnostic["params"]["diagnostics"][0]["message"]  # type: ignore[index]


def ask(lab: Rig, request_id: int, method: str, **extra: object) -> dict[str, object]:
    params = {"textDocument": {"uri": lab.document}, "position": {"line": 0}, **extra}
    return request(request_id, method, params)


def stopped_methods(lab: Rig) -> list[str]:
    """The methods the server received, once the socket closed and the server was stopped."""
    eventually(lab.server.methods, lambda methods: methods[-2:] == ["shutdown", "exit"])
    return lab.server.methods()[:-2]


# initialize


def test_initialize_reaches_the_server_rebuilt_from_the_catalog_and_the_session(lab, client):
    lab.server.play({"reply": "initialize", "result": {"capabilities": {"hoverProvider": True}}})
    page = request(
        1,
        "initialize",
        {"rootUri": "file:///evil", "processId": 1, "capabilities": {"textDocument": {}}},
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(page)
        assert received(websocket) == answer(1, {"capabilities": {"hoverProvider": True}})
    sent = lab.server.received()[0]
    assert sent["params"] == {
        "processId": os.getpid(),
        "rootUri": lab.python_root,
        "workspaceFolders": [{"uri": lab.python_root, "name": "python"}],
        "clientInfo": {"name": "cstudy", "version": TEST_VERSION},
        "initializationOptions": {},
        "capabilities": BASEDPYRIGHT.capabilities,
    }


def test_a_second_initialize_is_refused_without_reaching_the_server(lab, client):
    lab.server.play({"reply": "initialize", "result": {}})
    with session(client, lab.query) as websocket:
        websocket.send_json(request(1, "initialize", {}))
        received(websocket)
        websocket.send_json(request(2, "initialize", {}))
        assert received(websocket)["error"]["code"] == -32600
    assert stopped_methods(lab) == ["initialize"]


# what the page may send


def test_a_method_outside_the_list_gets_32601_and_the_server_never_sees_it(lab, client):
    lab.server.play({"reply": "textDocument/hover", "result": None})
    with session(client, lab.query) as websocket:
        websocket.send_json(request(1, "shutdown"))
        websocket.send_json(request(2, "workspace/executeCommand", {"command": "x"}))
        websocket.send_json(notification("exit"))
        errors = [received(websocket)["error"]["code"] for _ in range(2)]
        websocket.send_json(ask(lab, 3, "textDocument/hover"))
        assert (errors, received(websocket)) == ([-32601, -32601], answer(3, None))
    assert stopped_methods(lab) == ["textDocument/hover"]


def test_a_document_outside_the_root_is_refused_with_32602_on_the_way(lab, client):
    lab.server.play({"reply": "textDocument/hover", "result": None})
    with session(client, lab.query) as websocket:
        outside = request(1, "textDocument/hover", {"textDocument": {"uri": OUTSIDE}})
        websocket.send_json(outside)
        error = received(websocket)["error"]
        websocket.send_json(ask(lab, 2, "textDocument/hover"))
        received(websocket)
    assert (error["code"], error["message"]) == (-32602, f"{OUTSIDE} is outside the session's root")
    assert stopped_methods(lab) == ["textDocument/hover"]


def test_what_the_page_sends_reaches_the_server_in_order(lab, client):
    lab.server.play({"reply": "textDocument/hover", "result": None})
    opened = {"textDocument": {"uri": lab.document, "text": "x = 1\n", "version": 1}}
    changed = {"textDocument": {"uri": lab.document}, "contentChanges": [{"text": "x = 2\n"}]}
    with session(client, lab.query) as websocket:
        websocket.send_json(notification("initialized", {}))
        websocket.send_json(notification("textDocument/didOpen", opened))
        websocket.send_json(notification("textDocument/didChange", changed))
        websocket.send_json(ask(lab, 1, "textDocument/hover"))
        received(websocket)
    assert stopped_methods(lab) == [
        "initialized",
        "textDocument/didOpen",
        "textDocument/didChange",
        "textDocument/hover",
    ]


# what the server may send


def test_the_servers_requests_are_answered_and_never_reach_the_page(lab, client):
    configuration = request(
        "h1", "workspace/configuration", {"items": [{"section": "basedpyright.analysis"}]}
    )
    lab.server.play(
        {"send": configuration},
        {"await_response": "h1"},
        {"send": request("h2", "window/workDoneProgress/create", {"token": 1})},
        {"await_response": "h2"},
        {"send": diagnostics(lab.document, "first message the page sees")},
    )
    with session(client, lab.query) as websocket:
        assert message_of(received(websocket)) == "first message the page sees"
    answers = [message for message in lab.server.received() if "result" in message]
    assert answers == [
        answer("h1", [BASEDPYRIGHT.settings["basedpyright.analysis"]]),
        answer("h2", None),
    ]


def test_only_diagnostics_for_files_of_the_root_reach_the_page(lab, client):
    lab.server.play(
        {"send": notification("window/logMessage", {"message": "hello", "type": 3})},
        {"send": diagnostics(OUTSIDE, "outside")},
        {"send": notification("$/progress", {"token": 1, "value": {}})},
        {"send": diagnostics(lab.document, "inside")},
    )
    with session(client, lab.query) as websocket:
        assert message_of(received(websocket)) == "inside"


def test_hover_documentation_reaches_the_page_as_html_it_may_insert(lab, client):
    contents = {
        "kind": "markdown",
        "value": "```python\ndef sorted(x): ...\n```\n<script>x</script>",
    }
    lab.server.play({"reply": "textDocument/hover", "result": {"contents": contents}})
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/hover"))
        reply = received(websocket)
    value = reply["result"]["contents"]["value"]
    assert (reply["result"]["contents"]["kind"], "tok-k" in value, "<script" in value) == (
        HTML,
        True,
        False,
    )


def test_a_hover_with_nothing_to_show_is_answered_null(lab, client):
    lab.server.play(
        {"reply": "textDocument/hover", "result": {"contents": {"kind": "markdown", "value": ""}}}
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/hover"))
        assert received(websocket) == answer(1, None)


def test_resolved_documentation_is_html_and_the_detail_stays_text(lab, client):
    item = {
        "label": "sorted",
        "detail": "(x) -> <b>list</b>",
        "documentation": {"kind": "markdown", "value": "**Sort**"},
    }
    lab.server.play(
        {"reply": "textDocument/completion", "result": {"items": [SENT_ITEM]}},
        {"reply": "completionItem/resolve", "result": item},
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/completion"))
        (listed,) = received(websocket)["result"]["items"]
        websocket.send_json(request(2, "completionItem/resolve", listed))
        result = received(websocket)["result"]
    assert {name: value for name, value in result.items() if name != "data"} == {
        "label": "sorted",
        "detail": "(x) -> <b>list</b>",
        "documentation": {"kind": HTML, "value": "<p><strong>Sort</strong></p>\n"},
    }


def test_a_resolve_reaches_the_server_with_the_data_the_server_sent(lab, client):
    lab.server.play(
        {"reply": "textDocument/completion", "result": {"items": [SENT_ITEM]}},
        {"reply": "completionItem/resolve", "result": SENT_ITEM},
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/completion"))
        (listed,) = received(websocket)["result"]["items"]
        websocket.send_json(request(2, "completionItem/resolve", {**listed, "label": "other"}))
        received(websocket)
    resolve = next(m for m in lab.server.received() if m.get("method") == "completionItem/resolve")
    assert (listed["data"] != SENT_ITEM["data"], resolve["params"]) == (True, SENT_ITEM)


def test_a_resolve_of_an_item_the_server_never_sent_gets_32602_and_the_server_never_sees_it(
    lab, client
):
    lab.server.play({"reply": "textDocument/hover", "result": None})
    forged = {"label": "x", "data": {"uri": lab.document, "moduleUri": "file:///etc/passwd"}}
    with session(client, lab.query) as websocket:
        websocket.send_json(request(1, "completionItem/resolve", forged))
        error = received(websocket)["error"]
        websocket.send_json(ask(lab, 2, "textDocument/hover"))
        received(websocket)
    assert (error["code"], stopped_methods(lab)) == (-32602, ["textDocument/hover"])


def test_a_request_with_the_id_of_a_pending_request_gets_32600_and_the_pending_one_is_answered(
    lab, client
):
    lab.server.play(
        {"await": "textDocument/hover"},
        {"wait_for": str(lab.server.gate("answer"))},
        {"send": answer(1, None)},
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/hover"))
        eventually(lab.server.methods, lambda methods: methods == ["textDocument/hover"])
        websocket.send_json(ask(lab, 1, "textDocument/definition"))
        refusal = received(websocket)
        lab.server.gate("answer").touch()
        answered = received(websocket)
    assert (refusal["id"], refusal["error"]["code"], answered) == (None, -32600, answer(1, None))
    assert stopped_methods(lab) == ["textDocument/hover"]


def test_an_answer_over_4_mib_arrives_as_an_error(lab, client):
    lab.server.play({"reply": "textDocument/hover", "result": "x" * (MESSAGE_LIMIT + 10)})
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/hover"))
        reply = received(websocket)
    assert reply["error"] == {"code": -32803, "message": "answer over 4 MiB"}


# definitions and library files


def definition_to(lab: Rig, path: str, text: str = "def sorted(x): ...\n") -> str:
    """A file of the workspace the server will name as a definition; its URI."""
    file = lab.root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    lab.server.play(
        {"reply": "textDocument/definition", "result": [{"uri": file.as_uri(), "range": {}}]}
    )
    return file.as_uri()


def test_a_definition_into_the_library_is_read_over_the_socket_by_the_broker(lab, client):
    uri = definition_to(lab, ".cs/lsp/node_modules/basedpyright/typeshed/builtins.pyi")
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/definition"))
        located = received(websocket)
        websocket.send_json(request(2, "cstudy/libraryFile", {"uri": uri}))
        read = received(websocket)
    assert (located["result"][0]["uri"], read) == (
        uri,
        answer(
            2,
            {
                "uri": uri,
                "path": ".cs/lsp/node_modules/basedpyright/typeshed/builtins.pyi",
                "text": "def sorted(x): ...\n",
            },
        ),
    )
    assert stopped_methods(lab) == ["textDocument/definition"]


def test_a_file_the_server_never_named_is_not_read(lab, client):
    other = lab.root / "secret.txt"
    other.write_text("secret\n")
    with session(client, lab.query) as websocket:
        websocket.send_json(request(1, "cstudy/libraryFile", {"uri": other.as_uri()}))
        error = received(websocket)["error"]
    assert (error["code"], error["data"]["reason"]) == (-32803, "not_a_definition")


def test_a_definition_into_the_build_area_is_not_shown(lab, client):
    uri = definition_to(lab, ".cs/build/python/reference/x.py", "secret = 1\n")
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/definition"))
        received(websocket)
        websocket.send_json(request(2, "cstudy/libraryFile", {"uri": uri}))
        error = received(websocket)["error"]
    assert error == {
        "code": -32803,
        "message": "not shown: cstudy's build area",
        "data": {"reason": "build_area", "path": ".cs/build/python/reference/x.py"},
    }


def test_a_definition_into_the_content_root_is_not_shown(lab, client):
    reference = lab.environment.content_root / "problems" / "reference.py"
    reference.parent.mkdir(parents=True)
    reference.write_text("secret = 1\n")
    lab.server.play({"reply": "textDocument/definition", "result": [{"uri": reference.as_uri()}]})
    with session(client, lab.query) as websocket:
        websocket.send_json(ask(lab, 1, "textDocument/definition"))
        received(websocket)
        websocket.send_json(request(2, "cstudy/libraryFile", {"uri": reference.as_uri()}))
        assert received(websocket)["error"]["data"]["reason"] == "build_area"


# changes on disk


REGISTRATION = request(
    "r1",
    "client/registerCapability",
    {
        "registrations": [
            {"id": "w1", "method": "workspace/didChangeWatchedFiles", "registerOptions": {}}
        ]
    },
)
SAVED = FileChanged(1, "two_sum.py", "ab", "python/practice")


def registered(lab: Rig) -> None:
    lab.server.play(
        {"send": REGISTRATION},
        {"await_response": "r1"},
        {"send": diagnostics(lab.document, "registered")},
    )


def test_a_change_on_disk_reaches_the_server_once_it_registered_to_hear_of_them(lab, client):
    registered(lab)
    with session(client, lab.query) as websocket:
        assert message_of(received(websocket)) == "registered"
        noticed(client, lab.notifications, SAVED)
        eventually(lab.server.methods, lambda methods: "workspace/didChangeWatchedFiles" in methods)
    event = next(
        m for m in lab.server.received() if m.get("method") == "workspace/didChangeWatchedFiles"
    )
    assert event["params"] == {"changes": [{"uri": lab.document, "type": 2}]}


def test_created_and_deleted_files_have_their_own_types(lab, client):
    registered(lab)
    created = FileChanged(1, "ledger.py", "cd", "python/practice", created=True)
    deleted = FileChanged(1, "old.py", None, "python/practice")
    with session(client, lab.query) as websocket:
        received(websocket)
        noticed(client, lab.notifications, created)
        noticed(client, lab.notifications, deleted)
        eventually(
            lab.server.methods,
            lambda methods: methods.count("workspace/didChangeWatchedFiles") == 2,
        )
    kinds = [
        m["params"]["changes"][0]["type"]
        for m in lab.server.received()
        if m.get("method") == "workspace/didChangeWatchedFiles"
    ]
    assert kinds == [1, 3]


def test_a_server_that_did_not_register_hears_of_no_change(lab, client):
    lab.server.play({"send": diagnostics(lab.document, "ready")})
    with session(client, lab.query) as websocket:
        received(websocket)
        noticed(client, lab.notifications, SAVED)
    assert stopped_methods(lab) == []


def test_a_change_outside_the_root_is_not_passed_on(lab, client):
    registered(lab)
    elsewhere = FileChanged(2, "x.ts", "ab", "typescript/practice")
    with session(client, lab.query) as websocket:
        received(websocket)
        noticed(client, lab.notifications, elsewhere)
    assert stopped_methods(lab) == []


class WatchedHub(Notifications):
    """A hub that counts its file-change listeners."""

    def __init__(self) -> None:
        super().__init__()
        self.listening = 0

    def on_file_changed(self, listener: Callable[[FileChanged], None]) -> Callable[[], None]:
        self.listening += 1
        stop = super().on_file_changed(listener)

        def stop_listening() -> None:
            self.listening -= 1
            stop()

        return stop_listening


def test_a_session_listens_to_changes_while_it_lasts_and_no_longer(lab):
    hub = WatchedHub()
    lab.notifications = hub
    lab.server.play({"send": diagnostics(lab.document, "ready")})
    with session_client(lab.app) as page:
        with session(page, lab.query) as websocket:
            received(websocket)
            during = hub.listening
        eventually(lambda: hub.listening, lambda listening: listening == 0)
    assert during == 1


def test_every_session_of_the_root_hears_of_a_change(lab, client):
    registered(lab)
    with session(client, lab.query) as first, session(client, lab.query) as second:
        received(first)
        received(second)
        noticed(client, lab.notifications, SAVED)
        eventually(
            lab.server.methods,
            lambda methods: methods.count("workspace/didChangeWatchedFiles") == 2,
        )


def test_a_server_that_exits_still_closes_the_socket_with_4002(lab, client):
    lab.server.play({"exit": 3})
    with session(client, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "exit 3")
