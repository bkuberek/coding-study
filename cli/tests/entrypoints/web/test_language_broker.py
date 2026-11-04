"""The broker between a session's socket and its server (docs/specs/web-ui.md#the-broker): what
reaches the server and what reaches the page, message by message. The broker holds no socket and
no process, so these tests give it messages and read what it would send."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from coding_study.application.attempt_changes import FileChanged
from coding_study.application.code_intelligence import SessionTarget
from coding_study.domain.code_intelligence import BASEDPYRIGHT, TYPESCRIPT_LANGUAGE_SERVER
from coding_study.entrypoints.web.completion_items import ANSWERS_KEPT
from coding_study.entrypoints.web.language_broker import Delivery, LanguageBroker
from tests.language_server_scripts import answer, notification, request

MIB = 1024 * 1024
PID = 4242
VERSION = "9.9.9"
WORKSPACE = Path("/ws")
CONTENT = Path("/content")
ROOT = "file:///ws/python"
INSIDE = f"{ROOT}/practice/two_sum.py"
HTML = "cstudy-html"
NOTHING = Delivery()


def broker_for(
    server=BASEDPYRIGHT, root: str = "python", workspace: Path = WORKSPACE
) -> LanguageBroker:
    return LanguageBroker(SessionTarget(server, workspace, root, CONTENT), VERSION, PID)


@pytest.fixture
def broker() -> LanguageBroker:
    return broker_for()


def from_page(broker: LanguageBroker, message: Any) -> Delivery:
    return asyncio.run(broker.from_page(message))


def from_server(broker: LanguageBroker, message: Any) -> Delivery:
    return broker.from_server(message if isinstance(message, str) else json.dumps(message))


def initialized(broker: LanguageBroker) -> LanguageBroker:
    from_page(broker, request(0, "initialize", {}))
    return broker


def error_of(delivery: Delivery) -> dict[str, Any]:
    (reply,) = delivery.to_page
    return reply["error"]


def document(uri: str) -> dict[str, Any]:
    return {"textDocument": {"uri": uri}}


# initialize


def test_initialize_is_rebuilt_from_the_catalog_and_the_session(broker):
    page = request(
        0,
        "initialize",
        {
            "processId": None,
            "rootUri": "file:///somewhere/else",
            "rootPath": "/somewhere/else",
            "locale": "xx",
            "trace": "verbose",
            "workDoneToken": "t",
            "clientInfo": {"name": "page"},
            "capabilities": {
                "textDocument": {"completion": {"completionItem": {"snippetSupport": True}}}
            },
            "initializationOptions": {"page": "options"},
            "workspaceFolders": [{"uri": "file:///somewhere/else", "name": "else"}],
        },
    )
    delivery = from_page(broker, page)
    assert delivery == Delivery(
        to_server=(
            request(
                0,
                "initialize",
                {
                    "processId": PID,
                    "rootUri": ROOT,
                    "workspaceFolders": [{"uri": ROOT, "name": "python"}],
                    "clientInfo": {"name": "cstudy", "version": VERSION},
                    "initializationOptions": {},
                    "capabilities": BASEDPYRIGHT.capabilities,
                },
            ),
        )
    )


def test_initialize_needs_nothing_of_the_pages_parameters(broker):
    delivery = from_page(broker, {"jsonrpc": "2.0", "id": 5, "method": "initialize"})
    (sent,) = delivery.to_server
    assert (sent["id"], sent["params"]["rootUri"]) == (5, ROOT)


def test_typescript_gets_its_initialization_options_for_the_workspace():
    broker = broker_for(TYPESCRIPT_LANGUAGE_SERVER, "typescript")
    (sent,) = from_page(broker, request(0, "initialize", {})).to_server
    assert (sent["params"]["initializationOptions"], sent["params"]["rootUri"]) == (
        {
            "tsserver": {"path": "/ws/typescript/node_modules/typescript/lib"},
            "disableAutomaticTypingAcquisition": True,
            "preferences": {"includeCompletionsForModuleExports": False},
        },
        "file:///ws/typescript",
    )


def test_a_project_folder_is_the_root_and_names_the_folder():
    broker = broker_for(root="projects/bank-project-python")
    (sent,) = from_page(broker, request(0, "initialize", {})).to_server
    assert (sent["params"]["rootUri"], sent["params"]["workspaceFolders"]) == (
        "file:///ws/projects/bank-project-python",
        [{"uri": "file:///ws/projects/bank-project-python", "name": "bank-project-python"}],
    )


def test_a_root_with_a_space_is_a_percent_encoded_uri():
    broker = broker_for(workspace=Path("/my ws"))
    (sent,) = from_page(broker, request(0, "initialize", {})).to_server
    assert sent["params"]["rootUri"] == "file:///my%20ws/python"


def test_the_servers_answer_to_initialize_goes_back_unchanged(broker):
    from_page(broker, request(3, "initialize", {}))
    result = {"capabilities": {"hoverProvider": True}, "serverInfo": {"name": "x"}}
    assert from_server(broker, answer(3, result)) == Delivery(to_page=(answer(3, result),))


def test_a_second_initialize_is_refused_with_32600(broker):
    initialized(broker)
    delivery = from_page(broker, request(1, "initialize", {}))
    assert (delivery.to_server, error_of(delivery)["code"], delivery.to_page[0]["id"]) == (
        (),
        -32600,
        1,
    )


# what reaches the server


@pytest.mark.parametrize(
    "message",
    [
        notification("initialized", {}),
        notification("textDocument/didOpen", {"textDocument": {"uri": INSIDE, "text": "x = 1"}}),
        notification(
            "textDocument/didChange",
            {"textDocument": {"uri": INSIDE}, "contentChanges": [{"text": "x = 2"}]},
        ),
        notification("textDocument/didClose", document(INSIDE)),
        notification("textDocument/didSave", document(INSIDE)),
        request(1, "textDocument/hover", {**document(INSIDE), "position": {"line": 0}}),
        request(2, "textDocument/definition", {**document(INSIDE), "position": {"line": 0}}),
        request(3, "textDocument/completion", {**document(INSIDE), "position": {"line": 0}}),
        request(5, "textDocument/signatureHelp", {**document(INSIDE), "position": {"line": 0}}),
        notification("$/cancelRequest", {"id": 3}),
    ],
    ids=lambda message: message["method"],
)
def test_the_methods_of_the_list_reach_the_server_unchanged(broker, message):
    assert from_page(broker, message) == Delivery(to_server=(message,))


@pytest.mark.parametrize(
    "method",
    [
        "shutdown",
        "textDocument/rename",
        "textDocument/references",
        "textDocument/codeAction",
        "textDocument/formatting",
        "workspace/executeCommand",
        "workspace/symbol",
        "custom/anything",
        "cstudy/other",
    ],
)
def test_any_other_request_gets_32601_and_never_reaches_the_server(broker, method):
    delivery = from_page(broker, request(9, method, {}))
    assert (delivery.to_server, delivery.to_page[0]["id"], error_of(delivery)["code"]) == (
        (),
        9,
        -32601,
    )


@pytest.mark.parametrize(
    "method",
    ["exit", "textDocument/willSave", "workspace/didChangeConfiguration", "$/setTrace", "x/y"],
)
def test_any_other_notification_is_dropped(broker, method):
    assert from_page(broker, notification(method, {})) == NOTHING


@pytest.mark.parametrize(
    "response",
    [answer(1, None), {"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "x"}}],
)
def test_a_response_from_the_page_is_dropped(broker, response):
    assert from_page(broker, response) == NOTHING


@pytest.mark.parametrize("message", [{}, {"jsonrpc": "2.0"}, {"result": 1}, {"params": {}}])
def test_an_object_that_is_no_message_is_dropped(broker, message):
    assert from_page(broker, message) == NOTHING


def test_a_request_whose_method_is_not_a_string_gets_32600(broker):
    delivery = from_page(broker, {"jsonrpc": "2.0", "id": 4, "method": 7})
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32600)


@pytest.mark.parametrize(
    "request_id", ["cstudy-1", "cstudy-shutdown", True, None, 1.5, [1], {"a": 1}]
)
def test_a_request_with_an_id_the_page_may_not_use_gets_32600(broker, request_id):
    delivery = from_page(broker, request(request_id, "textDocument/hover", document(INSIDE)))
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32600)


@pytest.mark.parametrize("request_id", [0, 7, "abc", "x-cstudy-1"])
def test_ids_that_are_integers_or_other_strings_are_the_pages_own(broker, request_id):
    message = request(request_id, "textDocument/hover", document(INSIDE))
    assert from_page(broker, message) == Delivery(to_server=(message,))


# request ids that are still pending


@pytest.mark.parametrize(
    "method",
    [
        "textDocument/hover",
        "textDocument/definition",
        "textDocument/completion",
        "textDocument/signatureHelp",
        "completionItem/resolve",
        "cstudy/libraryFile",
        "initialize",
        "textDocument/rename",
    ],
)
def test_a_request_whose_id_is_still_pending_gets_32600_with_a_null_id(broker, method):
    page_asks(broker, 9, "textDocument/hover")
    delivery = from_page(broker, request(9, method, {**document(INSIDE), "uri": INSIDE}))
    (reply,) = delivery.to_page
    assert (delivery.to_server, reply["id"], reply["error"]) == (
        (),
        None,
        {"code": -32600, "message": "the id 9 is still pending"},
    )


def test_a_string_id_that_is_still_pending_is_refused_too(broker):
    initialized(broker)
    from_page(broker, request("a", "textDocument/hover", document(INSIDE)))
    delivery = from_page(broker, request("a", "textDocument/definition", document(INSIDE)))
    assert (delivery.to_server, error_of(delivery)["message"]) == (
        (),
        'the id "a" is still pending',
    )


def test_the_id_of_the_initialize_that_waits_for_its_answer_is_pending_too(broker):
    from_page(broker, request(0, "initialize", {}))
    delivery = from_page(broker, request(0, "textDocument/hover", document(INSIDE)))
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32600)


def test_a_refused_initialize_does_not_count_as_the_sessions_initialize(broker):
    from_page(broker, request(9, "textDocument/hover", document(INSIDE)))
    from_page(broker, request(9, "initialize", {}))
    delivery = from_page(broker, request(10, "initialize", {}))
    assert [message["method"] for message in delivery.to_server] == ["initialize"]


def test_an_id_is_free_again_once_the_server_answered_it(broker):
    page_asks(broker, 9, "textDocument/hover")
    from_server(broker, answer(9, None))
    message = request(9, "textDocument/definition", document(INSIDE))
    assert from_page(broker, message) == Delivery(to_server=(message,))


def test_the_pending_request_keeps_its_answer_when_its_id_is_reused(broker):
    page_asks(broker, 9, "textDocument/hover")
    from_page(broker, request(9, "textDocument/definition", document(INSIDE)))
    contents = {"kind": "markdown", "value": "**sorted**(x)"}
    assert answered(broker, 9, {"contents": contents})["contents"]["kind"] == HTML


def test_an_answer_to_a_request_with_a_reused_id_is_not_filed_as_a_definition(broker):
    """The attack: a request with an id of a pending request of another kind, so that the
    server's answer to the first is taken for a definition."""
    page_asks(broker, 9, "textDocument/hover")
    from_page(broker, request(9, "textDocument/definition", document(INSIDE)))
    from_server(broker, answer(9, [{"uri": "file:///etc/passwd"}]))
    reply = library_request(broker, "file:///etc/passwd")
    assert reply["error"]["data"]["reason"] == "not_a_definition"


def test_a_forged_resolve_cannot_make_its_echo_a_definition_target(broker):
    """The reviewer's script: a resolve whose item names a file, then a definition request with
    the same id, then the server echoing the item."""
    initialized(broker)
    forged = request(9, "completionItem/resolve", {"label": "x", "uri": "file:///etc/passwd"})
    resolve = from_page(broker, forged)
    from_page(broker, request(9, "textDocument/definition", document(INSIDE)))
    for sent in resolve.to_server:
        from_server(broker, answer(9, sent["params"]))
    reply = library_request(broker, "file:///etc/passwd")
    assert reply["error"]["data"]["reason"] == "not_a_definition"


# documents


@pytest.mark.parametrize(
    "uri",
    [
        f"{ROOT}/a.py",
        f"{ROOT}/practice/two_sum.py",
        f"{ROOT}/venv/x.py",
        f"{ROOT}/src/build_tools/x.py",
        "file:///ws/python/my%20dir/x.py",
        "file:///ws/py%74hon/a.py",
        "file://localhost/ws/python/a.py",
    ],
)
def test_a_document_inside_the_root_is_forwarded(broker, uri):
    message = notification("textDocument/didSave", document(uri))
    assert from_page(broker, message) == Delivery(to_server=(message,))


@pytest.mark.parametrize(
    "uri",
    [
        "file:///ws/other/x.py",
        "file:///ws/python-evil/x.py",
        "file:///ws/pythonx.py",
        "file:///ws/python",
        "file:///ws/python/",
        "file:///etc/passwd",
        "file:///",
        "file:///ws/python/../other/x.py",
        "file:///ws/python/./a.py",
        "file:///ws/python/%2e%2e/other/x.py",
        "file:///ws/python/%2E%2E/x.py",
        "file:///ws/python/..%2fother/x.py",
        "file:///ws/python/a/..",
        "file://remote-host/ws/python/a.py",
        "file:///ws/python/a.py#L3",
        "file:///ws/python/a.py?x=1",
        "file:relative/a.py",
        "http://example.com/ws/python/a.py",
        "untitled:Untitled-1",
        "jdt://contents/a.class",
        "/ws/python/a.py",
        "",
    ],
)
def test_a_document_outside_the_root_is_refused_with_32602_naming_it(broker, uri):
    delivery = from_page(broker, request(1, "textDocument/hover", document(uri)))
    assert (delivery.to_server, error_of(delivery)["code"], error_of(delivery)["message"]) == (
        (),
        -32602,
        f"{uri} is outside the session's root",
    )


@pytest.mark.parametrize(
    "path",
    [
        ".venv/lib/python3.13/site-packages/x.py",
        "node_modules/left-pad/index.js",
        "practice/__pycache__/x.pyc",
        ".pytest_cache/v/cache/nodeids",
        ".ruff_cache/x",
        "build/classes/X.class",
        ".gradle/x",
        "target/debug/x",
        "uv.lock",
        "a/b/node_modules/c.js",
    ],
)
def test_a_document_in_untracked_paths_is_refused(broker, path):
    delivery = from_page(broker, request(1, "textDocument/hover", document(f"{ROOT}/{path}")))
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_a_notification_about_a_document_outside_the_root_is_dropped(broker):
    message = notification(
        "textDocument/didOpen", {"textDocument": {"uri": "file:///etc/x", "text": ""}}
    )
    assert from_page(broker, message) == NOTHING


@pytest.mark.parametrize(
    "params",
    [
        None,
        {},
        {"textDocument": None},
        {"textDocument": {}},
        {"textDocument": {"uri": 7}},
        [1],
        "x",
    ],
)
def test_a_request_that_names_no_document_gets_32602(broker, params):
    delivery = from_page(broker, request(1, "textDocument/hover", params))
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_a_notification_that_names_no_document_is_dropped(broker):
    assert from_page(broker, notification("textDocument/didClose", {})) == NOTHING


def test_text_of_exactly_1_mib_is_forwarded(broker):
    message = notification(
        "textDocument/didOpen", {"textDocument": {"uri": INSIDE, "text": "x" * MIB}}
    )
    assert from_page(broker, message) == Delivery(to_server=(message,))


def test_text_over_1_mib_in_didopen_is_dropped(broker):
    message = notification(
        "textDocument/didOpen", {"textDocument": {"uri": INSIDE, "text": "x" * (MIB + 1)}}
    )
    assert from_page(broker, message) == NOTHING


def test_the_limit_of_1_mib_counts_bytes(broker):
    message = notification(
        "textDocument/didOpen", {"textDocument": {"uri": INSIDE, "text": "é" * (MIB // 2 + 1)}}
    )
    assert from_page(broker, message) == NOTHING


def test_changes_over_1_mib_together_in_didchange_are_dropped(broker):
    half = {"text": "x" * (MIB // 2 + 1)}
    message = notification(
        "textDocument/didChange", {"textDocument": {"uri": INSIDE}, "contentChanges": [half, half]}
    )
    assert from_page(broker, message) == NOTHING


def test_a_didchange_with_ranges_and_small_text_is_forwarded(broker):
    changes = [{"range": {}, "text": "x"}, {"text": "y"}]
    message = notification(
        "textDocument/didChange", {"textDocument": {"uri": INSIDE}, "contentChanges": changes}
    )
    assert from_page(broker, message) == Delivery(to_server=(message,))


# the server's requests


def configuration(items: Any) -> dict[str, Any]:
    return request("s1", "workspace/configuration", {"items": items})


def reply_to(delivery: Delivery) -> dict[str, Any]:
    (reply,) = delivery.to_server
    return reply


def test_configuration_answers_each_section_from_the_catalog_and_null_for_the_rest(broker):
    items = [{"section": "basedpyright"}, {"section": "python"}, {"scopeUri": ROOT}]
    delivery = from_server(broker, configuration(items))
    assert (delivery.to_page, reply_to(delivery)) == (
        (),
        answer("s1", [BASEDPYRIGHT.settings["basedpyright"], None, None]),
    )


def test_typescript_has_no_settings_to_answer():
    broker = broker_for(TYPESCRIPT_LANGUAGE_SERVER, "typescript")
    delivery = from_server(broker, configuration([{"section": "typescript"}]))
    assert reply_to(delivery) == answer("s1", [None])


@pytest.mark.parametrize("params", [None, {}, {"items": "x"}, {"items": []}])
def test_configuration_without_items_answers_an_empty_list(broker, params):
    delivery = from_server(broker, request("s1", "workspace/configuration", params))
    assert reply_to(delivery) == answer("s1", [])


def test_workspace_folders_answers_the_root(broker):
    delivery = from_server(broker, request("s1", "workspace/workspaceFolders"))
    assert reply_to(delivery) == answer("s1", [{"uri": ROOT, "name": "python"}])


@pytest.mark.parametrize(
    "method",
    [
        "window/workDoneProgress/create",
        "window/showMessageRequest",
        "workspace/diagnostic/refresh",
        "workspace/semanticTokens/refresh",
        "workspace/inlayHint/refresh",
        "workspace/codeLens/refresh",
        "client/registerCapability",
        "client/unregisterCapability",
    ],
)
def test_housekeeping_requests_are_answered_with_null(broker, method):
    delivery = from_server(broker, request("s1", method, {}))
    assert (delivery.to_page, reply_to(delivery)) == ((), answer("s1", None))


def test_apply_edit_is_refused_saying_why(broker):
    delivery = from_server(broker, request("s1", "workspace/applyEdit", {"edit": {}}))
    assert reply_to(delivery) == answer(
        "s1", {"applied": False, "failureReason": "cstudy applies no edits from a language server"}
    )


@pytest.mark.parametrize("method", ["window/showDocument", "custom/ask", "workspace/refresh", "x"])
def test_any_other_request_of_the_server_gets_32601_and_never_reaches_the_page(broker, method):
    delivery = from_server(broker, request(7, method, {}))
    (reply,) = delivery.to_server
    assert (delivery.to_page, reply["id"], reply["error"]["code"]) == ((), 7, -32601)


def test_the_servers_requests_never_reach_the_page(broker):
    for method in ("workspace/configuration", "window/showMessageRequest", "custom/x"):
        assert from_server(broker, request(1, method, {})).to_page == ()


# the server's notifications


def diagnostics(uri: str) -> dict[str, Any]:
    return notification(
        "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": [{"message": "x"}]}
    )


def test_diagnostics_for_a_file_inside_the_root_reach_the_page(broker):
    message = diagnostics(INSIDE)
    assert from_server(broker, message) == Delivery(to_page=(message,))


@pytest.mark.parametrize(
    "uri", ["file:///etc/passwd", "file:///ws/other/x.py", "untitled:1", "", 7]
)
def test_diagnostics_for_any_other_uri_are_dropped(broker, uri):
    assert from_server(broker, diagnostics(uri)) == NOTHING


@pytest.mark.parametrize(
    "uri",
    [
        "file:///ws/python/../other/x.py",
        "file:///ws/python/../.cs/build/python/ref/x.py",
        "file:///ws/python/./a.py",
        "file:///ws/python/%2e%2e/other/x.py",
        "file:///ws/python/%2E%2E/other/x.py",
        "file:///ws/python/a/..",
        "file:///ws/python/practice/../../other/x.py",
    ],
)
def test_diagnostics_for_a_path_with_dot_segments_are_dropped(broker, uri):
    assert from_server(broker, diagnostics(uri)) == NOTHING


def test_the_related_information_of_diagnostics_is_left_out(broker):
    related = [
        {"location": {"uri": "file:///ws/.cs/build/python/x.py", "range": {}}, "message": "m"}
    ]
    message = notification(
        "textDocument/publishDiagnostics",
        {
            "uri": INSIDE,
            "version": 3,
            "diagnostics": [
                {"message": "a", "relatedInformation": related, "severity": 1},
                {"message": "b"},
                "not a diagnostic",
            ],
        },
    )
    (reply,) = from_server(broker, message).to_page
    assert reply["params"] == {
        "uri": INSIDE,
        "version": 3,
        "diagnostics": [{"message": "a", "severity": 1}, {"message": "b"}, "not a diagnostic"],
    }


@pytest.mark.parametrize("diagnostics_value", [None, "x", {"a": 1}])
def test_diagnostics_that_are_no_list_pass_through_as_they_are(broker, diagnostics_value):
    message = notification(
        "textDocument/publishDiagnostics", {"uri": INSIDE, "diagnostics": diagnostics_value}
    )
    assert from_server(broker, message) == Delivery(to_page=(message,))


@pytest.mark.parametrize(
    "method",
    [
        "window/logMessage",
        "window/showMessage",
        "$/progress",
        "$/logTrace",
        "telemetry/event",
        "x/y",
    ],
)
def test_every_other_notification_of_the_server_is_dropped(broker, method):
    assert from_server(broker, notification(method, {"message": "hello"})) == NOTHING


# the server's answers


def page_asks(
    broker: LanguageBroker, request_id: int, method: str, params: Any = None, uri: str = INSIDE
) -> None:
    initialized(broker)
    from_page(broker, request(request_id, method, params if params is not None else document(uri)))


def answered(broker: LanguageBroker, request_id: int, result: Any) -> Any:
    (reply,) = from_server(broker, answer(request_id, result)).to_page
    return reply["result"]


def completed(broker: LanguageBroker, items: list[Any], request_id: int = 40) -> list[Any]:
    """The items of a completion answer that carries `items`, as the page receives them."""
    page_asks(broker, request_id, "textDocument/completion")
    return answered(broker, request_id, {"isIncomplete": False, "items": items})["items"]


def without_data(found: Any) -> Any:
    """An item, or a list of them, without the `data` the broker holds for the server."""
    if isinstance(found, list):
        return [without_data(item) for item in found]
    return {name: value for name, value in found.items() if name != "data"}


def test_an_answer_goes_to_the_page_with_its_id(broker):
    page_asks(broker, 4, "textDocument/hover")
    assert from_server(broker, answer(4, None)) == Delivery(to_page=(answer(4, None),))


def test_an_error_answer_goes_back_unchanged(broker):
    page_asks(broker, 4, "textDocument/hover")
    failure = {
        "jsonrpc": "2.0",
        "id": 4,
        "error": {"code": -32800, "message": "cancelled", "data": 1},
    }
    assert from_server(broker, failure) == Delivery(to_page=(failure,))


def test_an_answer_to_nothing_the_page_asked_is_dropped(broker):
    assert from_server(broker, answer(99, {"x": 1})) == NOTHING


def test_an_answer_is_delivered_once(broker):
    page_asks(broker, 4, "textDocument/hover")
    from_server(broker, answer(4, None))
    assert from_server(broker, answer(4, None)) == NOTHING


def test_an_answer_to_a_request_of_the_brokers_own_is_dropped(broker):
    assert from_server(broker, answer("cstudy-shutdown", None)) == NOTHING


def test_hover_contents_are_sent_as_html_the_page_may_insert(broker):
    page_asks(broker, 4, "textDocument/hover")
    result = {"contents": {"kind": "markdown", "value": "**sorted**(x)"}, "range": {"start": {}}}
    assert answered(broker, 4, result) == {
        "contents": {"kind": HTML, "value": "<p><strong>sorted</strong>(x)</p>\n"},
        "range": {"start": {}},
    }


def test_hover_html_in_the_contents_is_text(broker):
    page_asks(broker, 4, "textDocument/hover")
    result = {"contents": {"kind": "markdown", "value": "<script>alert(1)</script>"}}
    assert "<script" not in answered(broker, 4, result)["contents"]["value"]


def test_a_hover_that_renders_to_nothing_is_answered_null(broker):
    page_asks(broker, 4, "textDocument/hover")
    assert answered(broker, 4, {"contents": {"kind": "markdown", "value": "  "}}) is None


def test_a_list_of_marked_strings_is_one_piece_of_html(broker):
    page_asks(broker, 4, "textDocument/hover")
    contents = [{"language": "python", "value": "def f(): ..."}, "Docs."]
    value = answered(broker, 4, {"contents": contents})["contents"]["value"]
    assert ("<hr>" in value, "<p>Docs.</p>" in value) == (True, True)


def test_documentation_of_a_completion_list_is_html_and_the_rest_is_unchanged(broker):
    page_asks(broker, 5, "textDocument/completion")
    items = [
        {
            "label": "heappush",
            "detail": "<b>text</b>",
            "documentation": {"kind": "markdown", "value": "Push."},
        },
        {"label": "heapify", "documentation": "plain <i>text</i>"},
        {"label": "heappop", "documentation": {"kind": "markdown", "value": ""}},
        {"label": "nlargest"},
    ]
    result = answered(broker, 5, {"isIncomplete": True, "items": items})
    result["items"] = without_data(result["items"])
    assert result == {
        "isIncomplete": True,
        "items": [
            {
                "label": "heappush",
                "detail": "<b>text</b>",
                "documentation": {"kind": HTML, "value": "<p>Push.</p>\n"},
            },
            {
                "label": "heapify",
                "documentation": {
                    "kind": HTML,
                    "value": '<pre class="doc-plain">plain &lt;i&gt;text&lt;/i&gt;</pre>',
                },
            },
            {"label": "heappop"},
            {"label": "nlargest"},
        ],
    }


def test_a_completion_answer_that_is_a_bare_array_is_rendered_too(broker):
    page_asks(broker, 5, "textDocument/completion")
    items = [{"label": "a", "documentation": {"kind": "plaintext", "value": "x"}}]
    assert without_data(answered(broker, 5, items)) == [
        {"label": "a", "documentation": {"kind": HTML, "value": '<pre class="doc-plain">x</pre>'}}
    ]


def test_a_resolved_item_has_html_documentation_and_a_detail_that_stays_text(broker):
    (listed,) = completed(broker, [{"label": "sorted"}])
    page_asks(broker, 6, "completionItem/resolve", listed)
    item = {
        "label": "sorted",
        "detail": "(x) -> list",
        "documentation": {"kind": "markdown", "value": "Sort."},
    }
    assert without_data(answered(broker, 6, item)) == {
        "label": "sorted",
        "detail": "(x) -> list",
        "documentation": {"kind": HTML, "value": "<p>Sort.</p>\n"},
    }


# completion items: what the page may resolve

SENT = {
    "label": "sorted",
    "kind": 3,
    "data": {"uri": INSIDE, "symbolLabel": "sorted", "moduleUri": "file:///lib/builtins.pyi"},
}


def resolve(broker: LanguageBroker, item: Any, request_id: int = 50) -> Delivery:
    return from_page(broker, request(request_id, "completionItem/resolve", item))


def test_the_data_of_a_completion_item_stays_with_the_broker(broker):
    (listed,) = completed(broker, [SENT])
    assert (isinstance(listed["data"], str), "moduleUri" in json.dumps(listed)) == (True, False)


def test_every_item_of_an_answer_gets_a_token_of_its_own_with_or_without_data(broker):
    listed = completed(broker, [SENT, {"label": "heappush"}, {**SENT, "label": "heappop"}])
    tokens = [item["data"] for item in listed]
    assert len(set(tokens)) == 3


def test_what_is_not_an_item_passes_through_a_completion_answer(broker):
    assert completed(broker, [7, "x", None]) == [7, "x", None]


def test_the_items_of_a_bare_array_answer_get_tokens_too(broker):
    page_asks(broker, 5, "textDocument/completion")
    (listed,) = answered(broker, 5, [SENT])
    assert isinstance(listed["data"], str)


def test_a_resolve_reaches_the_server_with_the_item_as_the_server_sent_it(broker):
    (listed,) = completed(broker, [SENT])
    delivery = resolve(broker, listed, 51)
    assert delivery == Delivery(to_server=(request(51, "completionItem/resolve", SENT),))


def test_the_pages_changes_to_an_item_never_reach_the_server(broker):
    (listed,) = completed(broker, [SENT])
    forged = {**listed, "label": "x", "uri": "file:///etc/passwd", "textEdit": {"newText": "y"}}
    delivery = resolve(broker, forged)
    assert delivery.to_server[0]["params"] == SENT


def test_an_item_without_data_is_resolved_as_the_server_sent_it(broker):
    (listed,) = completed(broker, [{"label": "heappush"}])
    delivery = resolve(broker, listed)
    assert delivery.to_server[0]["params"] == {"label": "heappush"}


@pytest.mark.parametrize(
    "item",
    [
        {"label": "x"},
        {"label": "x", "data": None},
        {"label": "x", "data": 7},
        {"label": "x", "data": {"uri": "file:///etc/passwd"}},
        {
            "label": "x",
            "data": {"uri": INSIDE, "moduleUri": "file:///ws/.cs/build/python/ref/a.py"},
        },
        {"label": "x", "data": "cstudy-item-1.0"},
        {"label": "x", "data": ["cstudy-item-1.0"]},
        {"label": "x", "data": {"x": 1}, "uri": "file:///etc/passwd"},
        None,
        [1],
        "x",
    ],
    ids=lambda item: json.dumps(item)[:40],
)
def test_an_item_no_completion_answer_carried_is_never_resolved(broker, item):
    delivery = resolve(broker, item)
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_the_error_of_a_refused_resolve_says_why_and_keeps_the_pages_id(broker):
    delivery = resolve(broker, {"label": "x", "data": {"uri": "file:///etc/passwd"}}, 77)
    (reply,) = delivery.to_page
    assert (reply["id"], reply["error"]["message"]) == (
        77,
        "completionItem/resolve needs an item that a completion answer of this session carried",
    )


def test_a_refused_resolve_leaves_its_id_free(broker):
    resolve(broker, {"label": "x"}, 9)
    message = request(9, "textDocument/definition", document(INSIDE))
    assert from_page(broker, message) == Delivery(to_server=(message,))


def test_a_resolved_item_goes_back_with_the_token_and_not_the_servers_data(broker):
    (listed,) = completed(broker, [SENT])
    resolve(broker, listed, 51)
    resolved = {**SENT, "detail": "(x) -> list", "documentation": "Sort."}
    assert answered(broker, 51, resolved)["data"] == listed["data"]


def test_a_resolved_item_without_data_in_the_answer_still_carries_the_token(broker):
    (listed,) = completed(broker, [SENT])
    resolve(broker, listed, 51)
    assert answered(broker, 51, {"label": "sorted", "detail": "d"})["data"] == listed["data"]


def test_a_resolve_answer_that_is_no_item_goes_back_as_it_is(broker):
    (listed,) = completed(broker, [SENT])
    resolve(broker, listed, 51)
    assert answered(broker, 51, None) is None


def test_an_item_may_be_resolved_again(broker):
    (listed,) = completed(broker, [SENT])
    resolve(broker, listed, 51)
    answered(broker, 51, SENT)
    assert resolve(broker, listed, 52).to_server[0]["params"] == SENT


def test_the_answer_to_a_resolve_is_filed_under_the_token_of_that_resolve(broker):
    first, second = completed(broker, [SENT, {**SENT, "label": "sum"}])
    resolve(broker, first, 51)
    resolve(broker, second, 52)
    answers = (answered(broker, 52, {"label": "sum"}), answered(broker, 51, {"label": "sorted"}))
    assert [reply["data"] for reply in answers] == [second["data"], first["data"]]


def test_the_items_of_the_latest_answers_may_be_resolved_and_the_older_are_forgotten(broker):
    first = completed(broker, [{**SENT, "label": "first"}], 40)[0]
    for number in range(ANSWERS_KEPT):
        completed(broker, [SENT], 41 + number)
    delivery = resolve(broker, first)
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_an_answer_is_still_resolvable_while_it_is_among_the_latest(broker):
    first = completed(broker, [{**SENT, "label": "first"}], 40)[0]
    for number in range(ANSWERS_KEPT - 1):
        completed(broker, [SENT], 41 + number)
    assert resolve(broker, first).to_server[0]["params"]["label"] == "first"


def test_a_token_of_another_session_means_nothing(broker):
    (listed,) = completed(broker, [SENT])
    elsewhere = initialized(broker_for())
    delivery = resolve(elsewhere, listed)
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_typescripts_cache_id_survives_the_round_trip(broker):
    """typescript-language-server keeps the details of a list under `data.cacheId`, which it
    reads back from the item."""
    sent = {"label": "map", "data": {"cacheId": 3, "file": INSIDE, "entryNames": ["map"]}}
    (listed,) = completed(broker, [sent])
    assert resolve(broker, listed).to_server[0]["params"]["data"] == sent["data"]


def test_signature_and_parameter_documentation_are_html(broker):
    page_asks(broker, 7, "textDocument/signatureHelp")
    result = {
        "activeSignature": 0,
        "signatures": [
            {
                "label": "heappush(heap, item)",
                "documentation": {"kind": "markdown", "value": "Push `item`."},
                "parameters": [
                    {"label": "heap", "documentation": "The heap."},
                    {"label": [8, 12]},
                ],
            }
        ],
    }
    assert answered(broker, 7, result) == {
        "activeSignature": 0,
        "signatures": [
            {
                "label": "heappush(heap, item)",
                "documentation": {"kind": HTML, "value": "<p>Push <code>item</code>.</p>\n"},
                "parameters": [
                    {
                        "label": "heap",
                        "documentation": {
                            "kind": HTML,
                            "value": '<pre class="doc-plain">The heap.</pre>',
                        },
                    },
                    {"label": [8, 12]},
                ],
            }
        ],
    }


@pytest.mark.parametrize("result", [None, {}, {"signatures": []}, [], "x", 7])
def test_answers_of_another_shape_pass_through_what_they_are(broker, result):
    page_asks(broker, 8, "textDocument/signatureHelp")
    (reply,) = from_server(broker, answer(8, result)).to_page
    assert reply["result"] == result


def test_other_answers_are_not_rendered(broker):
    page_asks(broker, 9, "textDocument/definition")
    result = [{"uri": "file:///lib/x.pyi", "range": {}}]
    assert answered(broker, 9, result) == result


@pytest.mark.parametrize("text", ["", "not json", "[1, 2]", "3", "null", "[" * 100_000])
def test_what_the_server_writes_that_is_not_one_json_object_is_dropped(broker, text):
    assert from_server(broker, text) == NOTHING


# definitions and library files


def definition(broker: LanguageBroker, result: Any, uri: str = INSIDE) -> Any:
    """Sends a definition request and the server's answer `result`; what the page receives."""
    page_asks(broker, 20, "textDocument/definition", uri=uri)
    (reply,) = from_server(broker, answer(20, result)).to_page
    return reply["result"]


def inside(workspace: Path) -> str:
    """A document inside the root of a broker over `workspace`."""
    return f"{workspace.as_uri()}/python/x.py"


def library_request(broker: LanguageBroker, uri: Any, request_id: Any = 30) -> dict[str, Any]:
    delivery = from_page(broker, request(request_id, "cstudy/libraryFile", {"uri": uri}))
    assert delivery.to_server == ()
    (reply,) = delivery.to_page
    return reply


def test_a_file_the_server_never_named_is_not_a_definition_target(broker):
    reply = library_request(broker, "file:///etc/passwd")
    assert reply["error"] == {
        "code": -32803,
        "message": "not a definition target of this session",
        "data": {"reason": "not_a_definition", "path": "/etc/passwd"},
    }


def test_a_file_a_hover_or_a_diagnostic_named_is_not_a_definition_target(broker):
    page_asks(broker, 4, "textDocument/hover")
    from_server(broker, answer(4, {"contents": "see file:///lib/x.pyi"}))
    from_server(broker, diagnostics("file:///lib/x.pyi"))
    assert (
        library_request(broker, "file:///lib/x.pyi")["error"]["data"]["reason"]
        == "not_a_definition"
    )


@pytest.mark.parametrize(
    "result",
    [
        {"uri": "file:///lib/x.pyi", "range": {}},
        [{"uri": "file:///lib/x.pyi", "range": {}}],
        [{"targetUri": "file:///lib/x.pyi", "targetRange": {}, "targetSelectionRange": {}}],
        [{"uri": "file:///other/y.pyi"}, {"uri": "file:///lib/x.pyi"}],
    ],
    ids=["a location", "locations", "location links", "several"],
)
def test_every_location_of_a_definition_answer_is_a_target(broker, result):
    definition(broker, result)
    assert (
        library_request(broker, "file:///lib/x.pyi")["error"]["data"]["reason"]
        != "not_a_definition"
    )


def test_a_target_stays_a_target_for_the_whole_session(broker):
    definition(broker, [{"uri": "file:///lib/x.pyi"}])
    definition(broker, None)
    assert (
        library_request(broker, "file:///lib/x.pyi")["error"]["data"]["reason"]
        != "not_a_definition"
    )


def test_a_target_is_the_uri_as_the_server_wrote_it(broker):
    definition(broker, [{"uri": "file:///lib/x%20y.pyi"}])
    assert (
        library_request(broker, "file:///lib/x y.pyi")["error"]["data"]["reason"]
        == "not_a_definition"
    )


def test_a_target_that_is_no_file_is_refused_as_such(broker):
    definition(broker, [{"uri": "jdt://contents/java.base/String.class"}])
    reply = library_request(broker, "jdt://contents/java.base/String.class")
    assert reply["error"]["data"] == {
        "reason": "not_a_file_uri",
        "path": "jdt://contents/java.base/String.class",
    }


def test_a_definition_answer_is_still_forwarded_unchanged(broker):
    page_asks(broker, 20, "textDocument/definition")
    result = [{"uri": "file:///lib/x.pyi", "range": {"start": {"line": 3, "character": 0}}}]
    assert from_server(broker, answer(20, result)) == Delivery(to_page=(answer(20, result),))


@pytest.mark.parametrize("params", [None, {}, {"uri": 7}, {"uri": None}, [], "x"])
def test_a_library_request_without_a_uri_gets_32602(broker, params):
    delivery = from_page(broker, request(1, "cstudy/libraryFile", params))
    assert (delivery.to_server, error_of(delivery)["code"]) == ((), -32602)


def test_a_library_request_that_is_a_notification_is_dropped(broker):
    assert from_page(broker, notification("cstudy/libraryFile", {"uri": "file:///x"})) == NOTHING


def test_a_library_file_is_read_and_answered_with_its_path_and_text(tmp_path):
    workspace = tmp_path / "ws"
    builtins = workspace / ".cs" / "lsp" / "builtins.pyi"
    builtins.parent.mkdir(parents=True)
    builtins.write_text("def sorted(): ...\n")
    broker = broker_for(workspace=workspace)
    definition(broker, [{"uri": builtins.as_uri()}], inside(workspace))
    reply = library_request(broker, builtins.as_uri())
    assert reply == answer(
        30,
        {"uri": builtins.as_uri(), "path": ".cs/lsp/builtins.pyi", "text": "def sorted(): ...\n"},
    )


HIDDEN_PLACES = (
    ".cs/build/python/ref/two_sum/hash_map.py",
    ".cs/cases/two-sum/0123abcd.json",
    ".cs/runs/42-abc/request.json",
)
"""Where a reference solution, the generated cases and the run data are in a workspace."""
PUBLIC = "file:///lib/builtins.pyi"


def hidden_places(tmp_path: Path) -> tuple[Path, Path, LanguageBroker]:
    """A workspace with a file in each hidden place and in the content root, the content root,
    and a broker over them."""
    workspace, content = tmp_path / "ws", tmp_path / "content"
    for place in (*HIDDEN_PLACES, "lib/public.py"):
        written = workspace / place
        written.parent.mkdir(parents=True, exist_ok=True)
        written.write_text("secret = 1\n")
    reference = content / "problems" / "reference.py"
    reference.parent.mkdir(parents=True)
    reference.write_text("secret = 1\n")
    target = SessionTarget(BASEDPYRIGHT, workspace, "python", content)
    return workspace, content, LanguageBroker(target, VERSION, PID)


@pytest.mark.parametrize("place", HIDDEN_PLACES)
def test_a_location_in_a_hidden_directory_is_left_out_of_a_definition_answer(tmp_path, place):
    workspace, _content, broker = hidden_places(tmp_path)
    found = [{"uri": (workspace / place).as_uri(), "range": {}}, {"uri": PUBLIC}]
    assert definition(broker, found, inside(workspace)) == [{"uri": PUBLIC}]


def test_a_location_in_the_content_root_is_left_out_of_a_definition_answer(tmp_path):
    workspace, content, broker = hidden_places(tmp_path)
    found = [{"uri": (content / "problems" / "reference.py").as_uri()}, {"uri": PUBLIC}]
    assert definition(broker, found, inside(workspace)) == [{"uri": PUBLIC}]


def test_a_location_link_into_a_hidden_directory_is_left_out_of_a_definition_answer(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    hidden = {"targetUri": (workspace / HIDDEN_PLACES[0]).as_uri(), "targetRange": {}}
    shown = {"targetUri": PUBLIC, "targetRange": {}}
    assert definition(broker, [hidden, shown], inside(workspace)) == [shown]


def test_a_single_location_in_a_hidden_directory_is_answered_null(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    found = {"uri": (workspace / HIDDEN_PLACES[0]).as_uri(), "range": {}}
    assert definition(broker, found, inside(workspace)) is None


def test_locations_that_are_all_hidden_are_answered_with_none(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    found = [{"uri": (workspace / place).as_uri()} for place in HIDDEN_PLACES]
    assert definition(broker, found, inside(workspace)) == []


def test_a_location_that_reaches_a_hidden_directory_through_a_link_is_left_out(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    (workspace / "python").mkdir()
    (workspace / "python" / "shortcut").symlink_to(workspace / ".cs" / "build", True)
    through_link = workspace / "python" / "shortcut" / "python" / "ref" / "two_sum" / "hash_map.py"
    assert definition(broker, [{"uri": through_link.as_uri()}], inside(workspace)) == []


def test_a_location_that_is_not_a_file_of_this_machine_passes_through(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    found = [{"uri": "jdt://contents/java.base/String.class"}]
    assert definition(broker, found, inside(workspace)) == found


def test_a_location_that_hides_nothing_is_a_definition_target(tmp_path):
    workspace, _content, broker = hidden_places(tmp_path)
    public = (workspace / "lib" / "public.py").as_uri()
    definition(broker, [{"uri": public}], inside(workspace))
    assert library_request(broker, public)["result"]["text"] == "secret = 1\n"


@pytest.mark.parametrize("place", HIDDEN_PLACES)
def test_a_hidden_location_is_never_a_target_the_page_may_read(tmp_path, place):
    workspace, _content, broker = hidden_places(tmp_path)
    uri = (workspace / place).as_uri()
    definition(broker, [{"uri": uri}], inside(workspace))
    assert library_request(broker, uri)["error"]["data"]["reason"] == "not_a_definition"


@pytest.mark.parametrize("hidden", [".cs/build", ".cs/cases", ".cs/runs"])
def test_a_directory_that_became_a_link_to_a_hidden_one_after_the_answer_is_still_refused(
    tmp_path, hidden
):
    """Defence in depth: the read checks again, by name and with links resolved."""
    workspace, _content, broker = hidden_places(tmp_path)
    place = next(place for place in HIDDEN_PLACES if place.startswith(hidden))
    swapped = workspace / "lib" / "swapped"
    swapped.mkdir()
    (swapped / Path(place).name).write_text("secret = 1\n")
    uri = (swapped / Path(place).name).as_uri()
    definition(broker, [{"uri": uri}], inside(workspace))
    (swapped / Path(place).name).unlink()
    swapped.rmdir()
    swapped.symlink_to((workspace / place).parent, target_is_directory=True)
    reply = library_request(broker, uri)
    assert reply["error"]["data"]["reason"] == "build_area"


def test_a_file_that_is_gone_since_the_definition_is_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    uri = (workspace / "gone.py").as_uri()
    broker = broker_for(workspace=workspace)
    definition(broker, [{"uri": uri}], inside(workspace))
    assert library_request(broker, uri)["error"]["data"] == {"reason": "missing", "path": "gone.py"}


def test_a_library_file_is_read_again_each_time(tmp_path):
    workspace = tmp_path / "ws"
    target = workspace / "lib.py"
    workspace.mkdir()
    target.write_text("one\n")
    broker = broker_for(workspace=workspace)
    definition(broker, [{"uri": target.as_uri()}], inside(workspace))
    first = library_request(broker, target.as_uri(), 1)["result"]["text"]
    target.write_text("two\n")
    second = library_request(broker, target.as_uri(), 2)["result"]["text"]
    assert (first, second) == ("one\n", "two\n")


# watched files


def registering(broker: LanguageBroker, *registrations: dict[str, Any]) -> None:
    from_server(
        broker, request("r1", "client/registerCapability", {"registrations": list(registrations)})
    )


WATCH = {
    "id": "w1",
    "method": "workspace/didChangeWatchedFiles",
    "registerOptions": {"watchers": []},
}
CHANGED = FileChanged(3, "two_sum.py", "ab", "python/practice")


def test_a_change_goes_to_the_server_as_a_watched_file_event_once_it_registered(broker):
    registering(broker, WATCH)
    delivery = broker.file_changed(CHANGED)
    assert delivery == Delivery(
        to_server=(
            notification(
                "workspace/didChangeWatchedFiles",
                {"changes": [{"uri": "file:///ws/python/practice/two_sum.py", "type": 2}]},
            ),
        )
    )


def test_nothing_goes_to_a_server_that_never_registered(broker):
    assert broker.file_changed(CHANGED) == NOTHING


def test_registrations_for_other_methods_do_not_count(broker):
    registering(broker, {"id": "x", "method": "workspace/didChangeConfiguration"})
    assert broker.file_changed(CHANGED) == NOTHING


@pytest.mark.parametrize(
    ("change", "kind"),
    [
        (FileChanged(3, "a.py", "ab", "python/practice"), 2),
        (FileChanged(3, "a.py", "ab", "python/practice", created=True), 1),
        (FileChanged(3, "a.py", None, "python/practice"), 3),
    ],
    ids=["changed", "created", "deleted"],
)
def test_the_type_is_created_changed_or_deleted(broker, change, kind):
    registering(broker, WATCH)
    (sent,) = broker.file_changed(change).to_server
    assert sent["params"]["changes"][0]["type"] == kind


def test_a_change_outside_the_root_is_not_sent(broker):
    registering(broker, WATCH)
    assert broker.file_changed(FileChanged(3, "a.ts", "ab", "typescript/practice")) == NOTHING


def test_a_change_in_the_root_of_a_project_is_sent():
    broker = broker_for(root="projects/bank-project-python")
    registering(broker, WATCH)
    change = FileChanged(3, "bank/bank.py", "ab", "projects/bank-project-python")
    (sent,) = broker.file_changed(change).to_server
    assert (
        sent["params"]["changes"][0]["uri"]
        == "file:///ws/projects/bank-project-python/bank/bank.py"
    )


def test_the_registration_ends_when_the_server_unregisters_it(broker):
    registering(broker, WATCH)
    from_server(
        broker,
        request(
            "u1",
            "client/unregisterCapability",
            {"unregisterations": [{"id": "w1", "method": WATCH["method"]}]},
        ),
    )
    assert broker.file_changed(CHANGED) == NOTHING


def test_it_goes_on_while_another_registration_remains(broker):
    registering(broker, WATCH, {**WATCH, "id": "w2"})
    from_server(
        broker,
        request(
            "u1",
            "client/unregisterCapability",
            {"unregisterations": [{"id": "w1", "method": WATCH["method"]}]},
        ),
    )
    assert len(broker.file_changed(CHANGED).to_server) == 1


@pytest.mark.parametrize(
    "params", [None, {}, {"registrations": "x"}, {"registrations": [7, {"id": 1}]}]
)
def test_a_registration_of_another_shape_is_answered_and_ignored(broker, params):
    delivery = from_server(broker, request("r1", "client/registerCapability", params))
    assert (reply_to(delivery), broker.file_changed(CHANGED)) == (answer("r1", None), NOTHING)
