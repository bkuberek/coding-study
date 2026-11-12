"""The session, and the checks every request passes before the app sees it
(docs/specs/web-ui.md#security).

Saving a file and starting a run executes code as the user, so only the page whose URL
`cstudy serve` printed may reach the app: its Host must be this server's (DNS rebinding), it must
hold the session cookie that the printed token buys, and every write must come from this
server's Origin with the page's CSRF token. A WebSocket handshake is a read that starts a
process, and a browser sends the cookie on it from any port of 127.0.0.1, so it needs the Origin
too, and its page proves the token in its first message instead of a header. Bodies are capped.
Every response, refusals included, carries the security headers and a Content Security Policy,
and none carries CORS headers.
"""

import hmac
import re
import secrets
from collections import deque
from dataclasses import dataclass

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection, Request
from starlette.responses import HTMLResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from coding_study.entrypoints.web.errors import ErrorCode, error_response

LOOPBACK = "127.0.0.1"
LOCAL_HOSTS = (LOOPBACK, "localhost")
SECRET_BYTES = 32
"""256 bits for the token, the cookie and the CSRF token."""
NONCE_BYTES = 16
TOKEN_PARAMETER = "token"
VIEW_PARAMETER = "view"
"""The view the login sends the browser on to, such as `/guides/hash-functions`, which the page
shows from the fragment `#/guides/hash-functions` (`cstudy learn <guide> --open`)."""
_VIEW = re.compile(r"(/[a-z0-9]+(-[a-z0-9]+)*)+")
"""Only a route of slugs: a view can name a place in the page, never another page or site."""
CSRF_HEADER = "X-Cstudy-CSRF"
SAFE_METHODS = frozenset({"GET", "HEAD"})
PAGE_PATH = "/"
API_PREFIX = "/api/"
MIB = 1024 * 1024
BODY_LIMIT = 2 * MIB
IMPORT_BODY_LIMIT = 64 * MIB
IMPORT_PATH = "/api/v1/progress/import"
NO_STORE = "no-store"
_POLICY_BEFORE_STYLES = ("default-src 'self'", "script-src 'self'")
_POLICY_AFTER_STYLES = (
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
)
_SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cross-origin-resource-policy": "same-origin",
}
_RESPONSE_STARTS = frozenset({"http.response.start", "websocket.http.response.start"})
"""The messages that begin a response: an HTTP response, or a refusal of a WebSocket handshake."""
OPEN_THE_URL = "open the URL that cstudy serve printed"
UNAUTHORIZED_PAGE = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>cstudy</title>
<p>This browser has no session with this server: {OPEN_THE_URL} in your terminal.</p>
</html>
"""
LOGIN_PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url={target}">
<title>cstudy</title>
<p><a href="{target}">Open cstudy</a></p>
</html>
"""


@dataclass(frozen=True, slots=True)
class SessionSecrets:
    """Three random values, new on every start: the token in the printed URL, the cookie it
    buys and the CSRF token the page sends with every write."""

    token: str
    cookie: str
    csrf: str

    @classmethod
    def generate(cls) -> "SessionSecrets":
        token, cookie, csrf = (secrets.token_urlsafe(SECRET_BYTES) for _ in range(3))
        return cls(token, cookie, csrf)


def cookie_name(port: int) -> str:
    """Cookies ignore ports, so two servers on one machine keep a cookie each."""
    return f"cstudy-{port}"


def login_url(port: int, token: str, view: str | None = None) -> str:
    """`view`, such as `/guides/hash-functions`, is the view the page opens on; None for the
    first one."""
    url = f"http://{LOOPBACK}:{port}{PAGE_PATH}?{TOKEN_PARAMETER}={token}"
    return url if view is None else f"{url}&{VIEW_PARAMETER}={view}"


def landing(view: str | None) -> str:
    """Where the login sends the browser on to: the page, at the fragment of `view` when that is
    a route of slugs."""
    if view is None or _VIEW.fullmatch(view) is None:
        return PAGE_PATH
    return f"{PAGE_PATH}#{view}"


def new_nonce() -> str:
    return secrets.token_urlsafe(NONCE_BYTES)


def content_security_policy(nonce: str | None = None) -> str:
    """The page's policy lets in the styles that carry its `nonce` (CodeMirror's
    `EditorView.cspNonce`); every other response gets no style but the server's files."""
    styles = "style-src 'self'" if nonce is None else f"style-src 'self' 'nonce-{nonce}'"
    return "; ".join((*_POLICY_BEFORE_STYLES, styles, *_POLICY_AFTER_STYLES))


class SecurityMiddleware:
    """The outermost layer of the app, so even a crash's response gets the headers."""

    def __init__(self, app: ASGIApp, port: int, session: SessionSecrets) -> None:
        self._app = app
        self._session = session
        self._cookie = cookie_name(port)
        self._hosts = frozenset(f"{host}:{port}" for host in LOCAL_HOSTS)
        self._origins = frozenset(f"http://{host}" for host in self._hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await self._upgrade(scope, receive, send)
            return
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        secured = _with_security_headers(scope, send)
        request = Request(scope)
        refusal = self._refusal(request)
        if refusal is not None:
            await refusal(scope, receive, secured)
            return
        limit = _body_limit(request)
        body = await _read_body(request, receive, limit)
        if body is None:
            too_large = error_response(ErrorCode.TOO_LARGE, f"the body is over {limit // MIB} MiB")
            await too_large(scope, receive, secured)
            return
        await self._app(scope, _replaying(body, receive), secured)

    async def _upgrade(self, scope: Scope, receive: Receive, send: Send) -> None:
        """A refusal is an HTTP response in place of the upgrade; the app sees only a handshake
        that passed."""
        secured = _with_security_headers(scope, send)
        refusal = self._upgrade_refusal(HTTPConnection(scope))
        if refusal is not None:
            await refusal(scope, receive, secured)
            return
        await self._app(scope, receive, secured)

    def _refusal(self, request: Request) -> Response | None:
        host_refusal = self._host_refusal(request)
        if host_refusal is not None:
            return host_refusal
        query = request.query_params
        if request.scope["path"] == PAGE_PATH and TOKEN_PARAMETER in query:
            return self._login(query[TOKEN_PARAMETER], landing(query.get(VIEW_PARAMETER)))
        if not self._has_session(request):
            return _unauthorized(request)
        if request.method not in SAFE_METHODS:
            return self._cross_site_refusal(request)
        return None

    def _upgrade_refusal(self, connection: HTTPConnection) -> Response | None:
        """The Host, then the cookie, then the Origin, in the order the spec fixes. The cookie
        alone keeps no page on another port out: browsers send it, since cookies ignore ports."""
        host_refusal = self._host_refusal(connection)
        if host_refusal is not None:
            return host_refusal
        if not self._has_session(connection):
            return _unauthorized(connection)
        origin = connection.headers.get("origin")
        if origin not in self._origins:
            message = f"a WebSocket must come from this server's page, not {origin}"
            return error_response(ErrorCode.FORBIDDEN, message)
        return None

    def _host_refusal(self, connection: HTTPConnection) -> Response | None:
        host = connection.headers.get("host", "").lower()
        if host in self._hosts:
            return None
        return error_response(
            ErrorCode.FORBIDDEN, f"{host or 'no host'} is not this server; {OPEN_THE_URL}"
        )

    def _has_session(self, connection: HTTPConnection) -> bool:
        return matches(connection.cookies.get(self._cookie), self._session.cookie)

    def _login(self, token: str, target: str) -> Response:
        """The token buys the cookie, then a page that sends the browser on to the page, at
        `target`, takes it out of the address bar. Not a redirect: after a navigation another
        site started, as the `--open` file does, a browser withholds a SameSite=Strict cookie
        from the redirect it follows, and sends it on a navigation this server's own page
        starts."""
        if not matches(token, self._session.token):
            return HTMLResponse(UNAUTHORIZED_PAGE, status_code=401)
        page = LOGIN_PAGE.format(target=target)
        response = HTMLResponse(page, headers={"cache-control": NO_STORE})
        response.set_cookie(
            self._cookie, self._session.cookie, path=PAGE_PATH, httponly=True, samesite="strict"
        )
        return response

    def _cross_site_refusal(self, request: Request) -> Response | None:
        """Another page in the browser can send a write without the cookie (SameSite=Strict),
        but never with this Origin, and never with the CSRF header without a CORS preflight."""
        origin = request.headers.get("origin")
        if origin not in self._origins:
            message = f"a {request.method} must come from this server's page, not {origin}"
            return error_response(ErrorCode.FORBIDDEN, message)
        if not matches(request.headers.get(CSRF_HEADER), self._session.csrf):
            message = f"a {request.method} needs the page's {CSRF_HEADER} header"
            return error_response(ErrorCode.FORBIDDEN, message)
        return None


def matches(given: str | None, secret: str) -> bool:
    """In constant time, as bytes: `compare_digest` refuses a str that is not ASCII."""
    return given is not None and hmac.compare_digest(given.encode(), secret.encode())


def _unauthorized(request: HTTPConnection) -> Response:
    if request.scope["path"].startswith(API_PREFIX):
        return error_response(ErrorCode.UNAUTHORIZED, f"no session; {OPEN_THE_URL}")
    return HTMLResponse(UNAUTHORIZED_PAGE, status_code=401)


def _with_security_headers(scope: Scope, send: Send) -> Send:
    is_api = scope["path"].startswith(API_PREFIX)

    async def secured(message: Message) -> None:
        if message["type"] in _RESPONSE_STARTS:
            headers = MutableHeaders(raw=list(message.get("headers", [])))
            headers.update(_SECURITY_HEADERS)
            headers.setdefault("content-security-policy", content_security_policy())
            if is_api:
                headers["cache-control"] = NO_STORE
            message = {**message, "headers": headers.raw}
        await send(message)

    return secured


def _body_limit(request: Request) -> int:
    is_import = request.method == "POST" and request.scope["path"] == IMPORT_PATH
    return IMPORT_BODY_LIMIT if is_import else BODY_LIMIT


async def _read_body(request: Request, receive: Receive, limit: int) -> list[Message] | None:
    """The request's messages up to the end of its body; None, reading no further, once the
    body is over `limit`, and at once when its declared length is."""
    if _declared_length(request) > limit:
        return None
    messages: list[Message] = []
    size = 0
    while True:
        message = await receive()
        messages.append(message)
        if message["type"] != "http.request":
            return messages
        size += len(message.get("body", b""))
        if size > limit:
            return None
        if not message.get("more_body", False):
            return messages


def _declared_length(request: Request) -> int:
    try:
        return int(request.headers.get("content-length", "0"))
    except ValueError:
        return 0


def _replaying(messages: list[Message], receive: Receive) -> Receive:
    """`receive` for the app: the messages already read, then the connection's own."""
    pending = deque(messages)

    async def replay() -> Message:
        return pending.popleft() if pending else await receive()

    return replay
