"""The HTTP grader's clients, on the standard library: one sends a case's requests to the app under
a limit on the whole exchange, the other works the mock control interface
(docs/specs/service-projects.md#control-interface)."""

import http.client
import json
import socket
import time
from collections.abc import Buffer, Mapping
from typing import Any
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
    return StackClients(HttpAppClient(endpoints.app_url), mocks)


class HttpAppClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        parts = urlsplit(base_url)
        self._address = (parts.hostname or "", parts.port)

    def send(self, request: HttpRequest, limit_ms: int) -> HttpResponse | ExchangeFailed:
        started = time.perf_counter_ns()

        def failed(failure: ExchangeFailure, detail: str) -> ExchangeFailed:
            return ExchangeFailed(failure, detail, time.perf_counter_ns() - started)

        said = f"{request.method} {self._base_url}{request.target}"
        if limit_ms <= 0:
            return failed(ExchangeFailure.TIMED_OUT, f"{said}: no time left in the case's limit")
        deadline = time.monotonic() + limit_ms / MILLISECONDS_PER_SECOND
        connection = _DeadlineConnection(self._address, deadline)
        try:
            status, headers, body = _exchange(connection, request)
        except TimeoutError:
            return failed(ExchangeFailure.TIMED_OUT, f"{said}: no whole answer in {limit_ms} ms")
        except ConnectionRefusedError:
            return failed(ExchangeFailure.REFUSED, f"{said}: connection refused")
        except _BodyTooLargeError:
            detail = f"{said}: the response body is over {MAX_RESPONSE_BYTES} bytes"
            return failed(ExchangeFailure.TOO_LARGE, detail)
        except (ConnectionError, http.client.IncompleteRead, _BodyCutShortError) as error:
            detail = f"{said}: the connection was dropped before the whole answer ({error})"
            return failed(ExchangeFailure.DROPPED, detail)
        except http.client.HTTPException as error:
            return failed(ExchangeFailure.NOT_HTTP, f"{said}: the answer is not HTTP ({error})")
        except OSError as error:
            return failed(ExchangeFailure.DROPPED, f"{said}: the connection failed ({error})")
        finally:
            connection.close()
        return HttpResponse(status, headers, body, time.perf_counter_ns() - started)


class _BodyTooLargeError(Exception):
    pass


class _BodyCutShortError(Exception):
    pass


def _exchange(
    connection: http.client.HTTPConnection, request: HttpRequest
) -> tuple[int, Mapping[str, str], bytes]:
    headers = {"Connection": "close", **request.headers}
    connection.request(request.method, request.target, body=request.body, headers=headers)
    response = connection.getresponse()
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise _BodyTooLargeError
    if response.length:
        raise _BodyCutShortError(f"{response.length} bytes of the body never came")
    return response.status, _joined_headers(response), body


def _joined_headers(response: http.client.HTTPResponse) -> dict[str, str]:
    joined: dict[str, str] = {}
    for name, value in response.getheaders():
        key = name.lower()
        joined[key] = f"{joined[key]}, {value}" if key in joined else value
    return joined


def _time_left(deadline: float) -> float:
    """Raises TimeoutError when none is left."""
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return left


class _DeadlineConnection(http.client.HTTPConnection):
    """A socket timeout bounds one read, so an app that sends a byte now and then would never
    reach it. This limits the whole exchange, with no thread to watch it."""

    def __init__(self, address: tuple[str, int | None], deadline: float) -> None:
        host, port = address
        super().__init__(host, port, timeout=_time_left(deadline))
        self._deadline = deadline

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
            LoggedRequest(entry["route"], entry["received_ms"], entry["responded_ms"])
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
