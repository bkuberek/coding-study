"""The broker between a code-intelligence session's socket and its language server
(docs/specs/web-ui.md#the-broker): what each message from the page and from the server becomes.

The page's messages are checked: only a short list of methods reaches the server, `initialize` is
rebuilt from the catalog, every document must lie in the session's root, a request cannot reuse
the id of one that waits for its answer, and a completion item is resolved only if the server
wrote it. The server's requests are answered here and never reach the page; its documentation is
rendered to HTML the page may insert; the places its definitions name are remembered so the page
can read them as library files; the workspace's file changes reach it as watched-file events. The
broker holds no socket and no process: it is given a message and says what to send where.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from coding_study.application.attempt_changes import FileChanged
from coding_study.application.attempt_files import EDITABLE_BYTES
from coding_study.application.code_intelligence import SessionTarget
from coding_study.domain.layout import BUILD_DIRECTORY
from coding_study.domain.workspace_projects import is_untracked
from coding_study.entrypoints.web.completion_items import CompletionItems, with_token
from coding_study.entrypoints.web.documentation import CSTUDY_HTML, documentation_html, hover_html
from coding_study.entrypoints.web.library_files import (
    LibraryRefusalError,
    Reason,
    display_path,
    file_path,
    local_path,
    read_library_file,
)

JSONRPC = "2.0"
RESERVED_ID_PREFIX = "cstudy-"
"""The broker's own requests to the server have string ids that start with this."""
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
REQUEST_FAILED = -32803
LIBRARY_FILE = "cstudy/libraryFile"
INITIALIZE = "initialize"
RESOLVE = "completionItem/resolve"
WATCHED_FILES = "workspace/didChangeWatchedFiles"
CLIENT_NAME = "cstudy"
NO_EDITS = "cstudy applies no edits from a language server"

DOCUMENT_REQUESTS = frozenset(
    {
        "textDocument/hover",
        "textDocument/definition",
        "textDocument/completion",
        "textDocument/signatureHelp",
    }
)
REQUESTS = DOCUMENT_REQUESTS | {RESOLVE}
"""The requests of the page that reach the server, `RESOLVE` only for an item the server wrote."""
DOCUMENT_NOTIFICATIONS = frozenset(
    {
        "textDocument/didOpen",
        "textDocument/didChange",
        "textDocument/didClose",
        "textDocument/didSave",
    }
)
NOTIFICATIONS = DOCUMENT_NOTIFICATIONS | {"initialized", "$/cancelRequest"}
"""The notifications of the page that reach the server."""
QUIET_REQUESTS = frozenset({"window/workDoneProgress/create", "window/showMessageRequest"})
"""The server's requests the broker answers with null: nothing is shown, so nothing is chosen."""
_REFRESH = re.compile(r"workspace/\w+/refresh")

type Id = int | str
type Fields = dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Sent:
    """A request of the page that the server has not answered."""

    method: str
    item: str | None = None
    """For `RESOLVE`, the token of the item it resolves."""


@dataclass(frozen=True, slots=True)
class Delivery:
    """What a message becomes: messages for the server and messages for the page."""

    to_server: tuple[Fields, ...] = ()
    to_page: tuple[Fields, ...] = ()


class LanguageBroker:
    """One session's rules. `version` is cstudy's, and `pid` that of `cstudy serve`, which the
    server watches when it follows LSP's `processId` rule."""

    def __init__(self, target: SessionTarget, version: str, pid: int) -> None:
        self._target = target
        self._version = version
        self._pid = pid
        self._root = PurePosixPath(str(target.directory))
        self._root_uri = target.directory.as_uri()
        self._hidden = (target.workspace / BUILD_DIRECTORY, target.content_root)
        self._initialized = False
        self._pending: dict[Id, _Sent] = {}
        """The requests the page sent that the server has not answered, by id: the broker's own
        record of what was sent, which decides what an answer is."""
        self._items = CompletionItems()
        self._definitions: set[str] = set()
        self._watching: set[str] = set()
        """The ids of the server's `workspace/didChangeWatchedFiles` registrations."""

    async def from_page(self, message: Fields) -> Delivery:
        """A JSON object the page sent."""
        method = message.get("method")
        if not isinstance(method, str):
            if "method" in message and "id" in message:
                return _error(None, INVALID_REQUEST, "the method is not a string")
            return Delivery()
        if "id" not in message:
            return self._page_notification(message, method)
        request_id = message["id"]
        if not _is_page_id(request_id):
            return _error(None, INVALID_REQUEST, f"an id cannot be {json.dumps(request_id)}")
        return await self._page_request(message, request_id, method)

    def from_server(self, text: str) -> Delivery:
        """One message the server wrote, as the JSON it carries."""
        message = _parsed(text)
        if message is None:
            return Delivery()
        method = message.get("method")
        if isinstance(method, str):
            if "id" in message:
                return self._server_request(message, method)
            return self._server_notification(message, method)
        if "id" in message and ("result" in message or "error" in message):
            return self._answer(message)
        return Delivery()

    def file_changed(self, change: FileChanged) -> Delivery:
        """A file of an attempt changed on disk: the server hears of it while it registered to
        be told. Whether a pattern of the registration matches is for the server to say."""
        if not self._watching:
            return Delivery()
        path = self._target.workspace / change.workspace_path
        if self._relative(PurePosixPath(str(path))) is None:
            return Delivery()
        kind = 3 if change.sha256 is None else 1 if change.created else 2
        changes = [{"uri": path.as_uri(), "type": kind}]
        return Delivery(to_server=(_notification(WATCHED_FILES, {"changes": changes}),))

    # from the page

    def _page_notification(self, message: Fields, method: str) -> Delivery:
        if method not in NOTIFICATIONS:
            return Delivery()
        if method in DOCUMENT_NOTIFICATIONS and not self._is_allowed_document(method, message):
            return Delivery()
        return Delivery(to_server=(message,))

    async def _page_request(self, message: Fields, request_id: Id, method: str) -> Delivery:
        if request_id in self._pending:
            pending = f"the id {json.dumps(request_id)} is still pending"
            return _error(None, INVALID_REQUEST, pending)
        if method == INITIALIZE:
            return self._initialize(request_id)
        if method == LIBRARY_FILE:
            return await self._library_file(request_id, message.get("params"))
        if method not in REQUESTS:
            return _error(request_id, METHOD_NOT_FOUND, f"{method} is not supported")
        if method == RESOLVE:
            return self._resolve(request_id, message.get("params"))
        if method in DOCUMENT_REQUESTS:
            refusal = self._document_refusal(message.get("params"))
            if refusal is not None:
                return _error(request_id, INVALID_PARAMS, refusal)
        self._pending[request_id] = _Sent(method)
        return Delivery(to_server=(message,))

    def _resolve(self, request_id: Id, item: object) -> Delivery:
        """The server is sent the item it wrote under the token the page's item names, never the
        page's own item, so nothing the page made up reaches a server that trusts its `data`."""
        named = self._items.named_by(item)
        if named is None:
            reason = f"{RESOLVE} needs an item that a completion answer of this session carried"
            return _error(request_id, INVALID_PARAMS, reason)
        token, written = named
        self._pending[request_id] = _Sent(RESOLVE, token)
        return Delivery(to_server=(_request(request_id, RESOLVE, written),))

    def _initialize(self, request_id: Id) -> Delivery:
        """The parameters are the broker's, not the page's: the PID of `cstudy serve`, the root,
        the catalog's options and the capabilities the broker implements."""
        if self._initialized:
            return _error(request_id, INVALID_REQUEST, "initialize was already sent")
        self._initialized = True
        self._pending[request_id] = _Sent(INITIALIZE)
        server = self._target.server
        params = {
            "processId": self._pid,
            "rootUri": self._root_uri,
            "workspaceFolders": [self._folder()],
            "clientInfo": {"name": CLIENT_NAME, "version": self._version},
            "initializationOptions": server.initialization_options(str(self._target.workspace)),
            "capabilities": server.capabilities,
        }
        return Delivery(to_server=(_request(request_id, INITIALIZE, params),))

    async def _library_file(self, request_id: Id, params: object) -> Delivery:
        uri = _fields(params).get("uri")
        if not isinstance(uri, str):
            return _error(request_id, INVALID_PARAMS, f"{LIBRARY_FILE} needs a uri")
        workspace = self._target.workspace
        try:
            if uri not in self._definitions:
                raise LibraryRefusalError(Reason.NOT_A_DEFINITION, _shown(uri, workspace))
            found = await asyncio.to_thread(read_library_file, uri, workspace, self._hidden)
        except LibraryRefusalError as refusal:
            data = {"reason": refusal.reason.value, "path": refusal.path}
            return _error(request_id, REQUEST_FAILED, refusal.reason.message, data)
        result = {"uri": found.uri, "path": found.path, "text": found.text}
        return Delivery(to_page=(_response(request_id, result),))

    def _is_allowed_document(self, method: str, message: Fields) -> bool:
        params = message.get("params")
        if self._document_refusal(params) is not None:
            return False
        return _carried_bytes(method, params) <= EDITABLE_BYTES

    def _document_refusal(self, params: object) -> str | None:
        """Why the document the parameters name may not be used, in the words of the error."""
        document = _fields(_fields(params).get("textDocument"))
        uri = document.get("uri")
        if not isinstance(uri, str):
            return "textDocument.uri is missing"
        if not self._is_in_root(uri):
            return f"{uri} is outside the session's root"
        return None

    def _is_in_root(self, uri: str) -> bool:
        """A `file:` URI whose path, percent-decoded, is absolute, has no `.` or `..` segment,
        lies inside the root and in no path a tool wrote."""
        try:
            path = local_path(uri)
        except LibraryRefusalError:
            return False
        if any(segment in (".", "..") for segment in path.split("/")):
            return False
        inside = self._relative(PurePosixPath(path))
        return inside is not None and not is_untracked(inside.as_posix())

    def _relative(self, path: PurePosixPath) -> PurePosixPath | None:
        """`path` relative to the root; None if it is the root or lies outside it."""
        if not path.is_relative_to(self._root):
            return None
        inside = path.relative_to(self._root)
        return inside if inside.parts else None

    def _folder(self) -> Fields:
        return {"uri": self._root_uri, "name": self._target.directory.name}

    # from the server

    def _server_request(self, message: Fields, method: str) -> Delivery:
        """Answered here: the broker is the server's client, and the page cannot be asked."""
        request_id = message["id"]
        params = _fields(message.get("params"))
        if method == "workspace/applyEdit":
            result: object = {"applied": False, "failureReason": NO_EDITS}
        elif method == "workspace/configuration":
            result = [self._setting(item) for item in _list(params.get("items"))]
        elif method == "workspace/workspaceFolders":
            result = [self._folder()]
        elif method in ("client/registerCapability", "client/unregisterCapability"):
            self._track_registrations(method, params)
            result = None
        elif method in QUIET_REQUESTS or _REFRESH.fullmatch(method):
            result = None
        else:
            return Delivery(
                to_server=(
                    _error_response(request_id, METHOD_NOT_FOUND, f"{method} is not supported"),
                )
            )
        return Delivery(to_server=(_response(request_id, result),))

    def _setting(self, item: object) -> object:
        section = _fields(item).get("section")
        return self._target.server.settings.get(section) if isinstance(section, str) else None

    def _track_registrations(self, method: str, params: Fields) -> None:
        registering = method == "client/registerCapability"
        listed = params.get("registrations" if registering else "unregisterations")
        ids = [
            registration["id"]
            for registration in map(_fields, _list(listed))
            if registration.get("method") == WATCHED_FILES
            and isinstance(registration.get("id"), str)
        ]
        if registering:
            self._watching.update(ids)
        else:
            self._watching.difference_update(ids)

    def _server_notification(self, message: Fields, method: str) -> Delivery:
        """Only diagnostics for a file of the root reach the page."""
        if method != "textDocument/publishDiagnostics":
            return Delivery()
        uri = _fields(message.get("params")).get("uri")
        if isinstance(uri, str) and self._is_in_root_file(uri):
            return Delivery(to_page=(message,))
        return Delivery()

    def _is_in_root_file(self, uri: str) -> bool:
        try:
            inside = self._relative(PurePosixPath(local_path(uri)))
        except LibraryRefusalError:
            return False
        return inside is not None

    def _answer(self, message: Fields) -> Delivery:
        request_id = message["id"]
        if not _is_page_id(request_id):
            return Delivery()
        sent = self._pending.pop(request_id, None)
        if sent is None:
            return Delivery()
        if "result" in message:
            message = {**message, "result": self._rendered(sent, message["result"])}
        return Delivery(to_page=(message,))

    def _rendered(self, sent: _Sent, result: Any) -> Any:
        match sent.method:
            case "textDocument/hover":
                return _hover(result)
            case "textDocument/completion":
                return _completion(self._items.issued(result))
            case "completionItem/resolve":
                return with_token(sent.item, _documented(result))
            case "textDocument/signatureHelp":
                return _signature_help(result)
            case "textDocument/definition":
                self._definitions.update(_targets(result))
                return result
            case _:
                return result


def _hover(result: Any) -> Any:
    fields = _fields(result)
    if "contents" not in fields:
        return result
    html = hover_html(fields["contents"])
    return None if html is None else {**fields, "contents": _html(html)}


def _completion(result: Any) -> Any:
    if isinstance(result, list):
        return [_documented(item) for item in cast(list[object], result)]
    fields = _fields(result)
    if not isinstance(fields.get("items"), list):
        return result
    return {**fields, "items": [_documented(item) for item in _list(fields["items"])]}


def _signature_help(result: Any) -> Any:
    fields = _fields(result)
    if not isinstance(fields.get("signatures"), list):
        return result
    return {**fields, "signatures": [_signature(item) for item in _list(fields["signatures"])]}


def _signature(signature: object) -> object:
    fields = _fields(signature)
    if not fields:
        return signature
    documented = cast(dict[str, Any], _documented(fields))
    if isinstance(documented.get("parameters"), list):
        documented["parameters"] = [_documented(item) for item in _list(documented["parameters"])]
    return documented


def _documented(item: object) -> object:
    """`item` with its `documentation` as HTML the page may insert, or without it when there is
    nothing to show."""
    fields = _fields(item)
    if "documentation" not in fields:
        return item
    html = documentation_html(fields["documentation"])
    rest = {name: value for name, value in fields.items() if name != "documentation"}
    return rest if html is None else {**rest, "documentation": _html(html)}


def _targets(result: object) -> list[str]:
    """The URI of each location of a definition answer: a `Location`'s `uri`, a
    `LocationLink`'s `targetUri`."""
    locations = _list(result) or [result]
    uris = (_fields(found).get("uri") or _fields(found).get("targetUri") for found in locations)
    return [uri for uri in uris if isinstance(uri, str)]


def _html(html: str) -> Fields:
    return {"kind": CSTUDY_HTML, "value": html}


def _carried_bytes(method: str, params: object) -> int:
    """The bytes of text a `didOpen` or a `didChange` carries."""
    fields = _fields(params)
    if method == "textDocument/didOpen":
        text = _fields(fields.get("textDocument")).get("text")
        return len(text.encode()) if isinstance(text, str) else 0
    if method == "textDocument/didChange":
        texts = (_fields(change).get("text") for change in _list(fields.get("contentChanges")))
        return sum(len(text.encode()) for text in texts if isinstance(text, str))
    return 0


def _shown(uri: str, workspace: Path) -> str:
    try:
        return display_path(file_path(uri), workspace)
    except LibraryRefusalError:
        return uri


def _is_page_id(request_id: object) -> bool:
    """An integer, or a string of the page's own: not a boolean, not null and not an id the
    broker uses for its requests to the server."""
    if isinstance(request_id, bool):
        return False
    if isinstance(request_id, int):
        return True
    return isinstance(request_id, str) and not request_id.startswith(RESERVED_ID_PREFIX)


def _parsed(text: str) -> Fields | None:
    try:
        message: object = json.loads(text)
    except (ValueError, RecursionError):
        return None
    return cast(Fields, message) if isinstance(message, dict) else None


def _fields(value: object) -> Fields:
    return cast(Fields, value) if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _request(request_id: Id, method: str, params: object) -> Fields:
    return {"jsonrpc": JSONRPC, "id": request_id, "method": method, "params": params}


def _notification(method: str, params: object) -> Fields:
    return {"jsonrpc": JSONRPC, "method": method, "params": params}


def _response(request_id: Id, result: object) -> Fields:
    return {"jsonrpc": JSONRPC, "id": request_id, "result": result}


def _error_response(request_id: Id | None, code: int, message: str, data: object = None) -> Fields:
    error: Fields = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC, "id": request_id, "error": error}


def _error(request_id: Id | None, code: int, message: str, data: object = None) -> Delivery:
    """An error answer for the page."""
    return Delivery(to_page=(_error_response(request_id, code, message, data),))
