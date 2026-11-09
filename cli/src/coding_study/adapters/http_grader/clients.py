"""The HTTP grader's clients, on the standard library: one sends a case's requests under a limit on
the whole exchange, as a browser would, the other works the mock control interface
(docs/specs/service-projects.md#control-interface)."""

import http.client
import json
import socket
import time
import urllib.request
from collections.abc import Buffer, Mapping
from dataclasses import dataclass
from email.message import Message
from http.cookiejar import CookieJar
from typing import Any, cast
from urllib.parse import quote, urlsplit

from coding_study.application.http_grading_ports import MockControl, StackClients, StackEndpoints
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import (
    ExchangeFailed,
    ExchangeFailure,
    HttpResponse,
    LoggedRequest,
    MockLog,
)
from coding_study.domain.http_origins import host_header
from coding_study.domain.http_redirects import MAX_REDIRECTS, redirected

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
"""More than any case compares, and a bound on what an app can make the grader hold in memory."""
CONTROL_TIMEOUT_S = 30.0
"""How long the control interface, which answers at once, may take on a busy machine."""
MILLISECONDS_PER_SECOND = 1000
NOT_FOUND = 404
OK = 200
ERROR_BODY_LIMIT = 200


def open_stack_clients(endpoints: StackEndpoints) -> StackClients:
    control_url = endpoints.control_url
    mocks: MockControl = (
        _NoMockServers()
        if control_url is None
        else HttpMockControl(control_url, endpoints.control_token)
    )
    return StackClients(HttpAppClient(endpoints.app_url, endpoints), mocks)


@dataclass(frozen=True, slots=True)
class _Answered:
    status: int
    lines: tuple[tuple[str, str], ...]
    """Every header as it came, so that each `Set-Cookie` stays apart."""
    body: bytes


class _Received:
    """All that `CookieJar.extract_cookies` reads of the response it is typed to take: `info()`,
    its headers."""

    def __init__(self, lines: tuple[tuple[str, str], ...]) -> None:
        self._message = Message()
        for name, value in lines:
            self._message[name] = value

    def info(self) -> Message:
        return self._message


class HttpAppClient:
    """Sends a request to the address the stack publishes for its origin, with the origin's name as
    its `Host`; a path alone goes to the app as it always has. A request with a jar sends and keeps
    cookies as a browser would, by the name the request was written with, so that `/login` and
    `http://app:8000/callback` share the app's."""

    def __init__(self, app_url: str, endpoints: StackEndpoints | None = None) -> None:
        self._endpoints = endpoints or StackEndpoints(app_url, None, "", ())
        self._jars: dict[str, CookieJar] = {}

    def clear_cookies(self) -> None:
        self._jars.clear()

    def send(self, request: HttpRequest, limit_ms: int) -> HttpResponse | ExchangeFailed:
        """Within `limit_ms` for every hop together."""
        started = time.perf_counter_ns()
        clock = _Deadline(started, time.monotonic() + limit_ms / MILLISECONDS_PER_SECOND, limit_ms)
        sent = self._sent_once(request, clock)
        for _hop in range(MAX_REDIRECTS):
            if not request.follow_redirects or not isinstance(sent, HttpResponse):
                break
            following = redirected(request, sent, self._cookie_url(request))
            if following is None or self._endpoints.address_of(following.origin) is None:
                break
            request = following
            sent = self._sent_once(request, clock)
        return sent

    def _sent_once(self, request: HttpRequest, clock: "_Deadline") -> HttpResponse | ExchangeFailed:
        said = f"{request.method} {self._shown_url(request)}"
        address = self._endpoints.address_of(request.origin)
        if address is None:
            detail = f"{said}: the stack publishes no address for this origin"
            return clock.failed(ExchangeFailure.REFUSED, detail)
        left_s = clock.left_s()
        if left_s <= 0:
            return clock.failed(
                ExchangeFailure.TIMED_OUT, f"{said}: no time left in the case's limit"
            )
        parts = urlsplit(address)
        connection = DeadlineConnection((parts.hostname or "", parts.port), left_s)
        try:
            answered = _exchange(connection, request, self._browser_headers(request))
        except TimeoutError:
            detail = f"{said}: no whole answer in {clock.limit_ms} ms"
            return clock.failed(ExchangeFailure.TIMED_OUT, detail)
        except ConnectionRefusedError:
            return clock.failed(ExchangeFailure.REFUSED, f"{said}: connection refused")
        except _BodyTooLargeError:
            detail = f"{said}: the response body is over {MAX_RESPONSE_BYTES} bytes"
            return clock.failed(ExchangeFailure.TOO_LARGE, detail)
        except (ConnectionError, http.client.IncompleteRead, _BodyCutShortError) as error:
            detail = f"{said}: the connection was dropped before the whole answer ({error})"
            return clock.failed(ExchangeFailure.DROPPED, detail)
        except http.client.HTTPException as error:
            detail = f"{said}: the answer is not HTTP ({error})"
            return clock.failed(ExchangeFailure.NOT_HTTP, detail)
        except OSError as error:
            return clock.failed(ExchangeFailure.DROPPED, f"{said}: the connection failed ({error})")
        finally:
            connection.close()
        self._keep_cookies(request, answered)
        headers = _joined_headers(answered.lines)
        return HttpResponse(answered.status, headers, answered.body, clock.spent_ns())

    def _browser_headers(self, request: HttpRequest) -> dict[str, str]:
        """`Host` for a named origin, and the jar's cookies."""
        headers: dict[str, str] = {}
        if request.origin is not None:
            headers["Host"] = host_header(request.origin)
        if request.jar is not None:
            asked = self._cookie_request(request)
            self._jar(request.jar).add_cookie_header(asked)
            cookie = asked.get_header("Cookie")
            if cookie:
                headers["Cookie"] = cookie
        return headers

    def _keep_cookies(self, request: HttpRequest, answered: _Answered) -> None:
        if request.jar is not None:
            received = cast(http.client.HTTPResponse, _Received(answered.lines))
            self._jar(request.jar).extract_cookies(received, self._cookie_request(request))

    def _jar(self, name: str) -> CookieJar:
        return self._jars.setdefault(name, CookieJar())

    def _cookie_request(self, request: HttpRequest) -> urllib.request.Request:
        return urllib.request.Request(self._cookie_url(request), method=request.method)

    def _cookie_url(self, request: HttpRequest) -> str:
        """Where the request went by the name it was written with: a path alone is the app's."""
        origin = request.origin or self._endpoints.app_origin or self._endpoints.app_url
        return f"{origin}{request.target}"

    def _shown_url(self, request: HttpRequest) -> str:
        origin = request.origin or self._endpoints.app_url
        return f"{origin}{request.target}"


@dataclass(frozen=True, slots=True)
class _Deadline:
    """One limit for every hop of a request."""

    started_ns: int
    deadline: float
    limit_ms: int

    def left_s(self) -> float:
        return self.deadline - time.monotonic()

    def spent_ns(self) -> int:
        return time.perf_counter_ns() - self.started_ns

    def failed(self, failure: ExchangeFailure, detail: str) -> ExchangeFailed:
        return ExchangeFailed(failure, detail, self.spent_ns())


class _BodyTooLargeError(Exception):
    pass


class _BodyCutShortError(Exception):
    pass


def _exchange(
    connection: http.client.HTTPConnection, request: HttpRequest, browser: Mapping[str, str]
) -> _Answered:
    headers = {"Connection": "close", **browser, **request.headers}
    connection.request(request.method, request.target, body=request.body, headers=headers)
    response = connection.getresponse()
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise _BodyTooLargeError
    if response.length:
        raise _BodyCutShortError(f"{response.length} bytes of the body never came")
    return _Answered(response.status, tuple(response.getheaders()), body)


def _joined_headers(lines: tuple[tuple[str, str], ...]) -> dict[str, str]:
    joined: dict[str, str] = {}
    for name, value in lines:
        key = name.lower()
        joined[key] = f"{joined[key]}, {value}" if key in joined else value
    return joined


def _time_left(deadline: float) -> float:
    """Raises TimeoutError when none is left."""
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return left


class DeadlineConnection(http.client.HTTPConnection):
    """A socket timeout bounds one read, so an app that sends a byte now and then would never
    reach it. This limits the whole exchange, with no thread to watch it."""

    def __init__(self, address: tuple[str, int | None], limit_s: float) -> None:
        host, port = address
        super().__init__(host, port, timeout=limit_s)
        self._deadline = time.monotonic() + limit_s

    def connect(self) -> None:
        super().connect()
        self.sock = _DeadlineSocket(self.sock, self._deadline)


class _DeadlineSocket(socket.socket):
    def __init__(self, connected: socket.socket, deadline: float) -> None:
        super().__init__(fileno=connected.detach())
        self._deadline = deadline
        self.settimeout(_time_left(deadline))

    def recv_into(self, buffer: Buffer, nbytes: int = 0, flags: int = 0) -> int:
        self.settimeout(_time_left(self._deadline))
        return super().recv_into(buffer, nbytes, flags)


class HttpMockControl:
    def __init__(self, control_url: str, token: str) -> None:
        self._control_url = control_url
        parts = urlsplit(control_url)
        self._address = (parts.hostname or "", parts.port)
        self._token = token

    def reset(self) -> None:
        self._require_ok("POST", "/reset")

    def set_scenario(self, mock: str, scenario: str) -> bool:
        path = f"/mocks/{quote(mock)}/scenario"
        status, body = self._call("PUT", path, json.dumps({"scenario": scenario}).encode())
        if status == NOT_FOUND:
            return False
        self._check(status, body)
        return True

    def log(self, mock: str) -> MockLog:
        document: dict[str, Any] = json.loads(self._require_ok("GET", f"/mocks/{quote(mock)}/log"))
        entries = tuple(
            LoggedRequest(
                entry["route"],
                entry["received_ms"],
                entry["responded_ms"],
                entry["headers"],
                entry["body"],
                entry.get("truncated", False),
            )
            for entry in document["entries"]
        )
        return MockLog(entries, document["dropped"])

    def _require_ok(self, method: str, path: str) -> bytes:
        status, body = self._call(method, path)
        self._check(status, body)
        return body

    def _check(self, status: int, body: bytes) -> None:
        if status != OK:
            answered = body[:ERROR_BODY_LIMIT].decode(errors="replace")
            raise RunnerStartError(
                f"the mock control interface at {self._control_url} answered {status}: {answered}"
            )

    def _call(self, method: str, path: str, body: bytes | None = None) -> tuple[int, bytes]:
        host, port = self._address
        connection = http.client.HTTPConnection(host, port, timeout=CONTROL_TIMEOUT_S)
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        except (OSError, http.client.HTTPException) as error:
            raise RunnerStartError(
                f"the mock control interface at {self._control_url} did not answer: {error}"
            ) from error
        finally:
            connection.close()


class _NoMockServers:
    """The control interface of a stack with no mock servers, which no case can name."""

    def reset(self) -> None:
        return

    def set_scenario(self, mock: str, scenario: str) -> bool:
        return False

    def log(self, mock: str) -> MockLog:
        return MockLog()
