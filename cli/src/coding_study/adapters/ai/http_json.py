"""JSON over HTTP for the provider adapters (docs/specs/ai.md#http and #errors).

The standard library's `urllib.request` with an opener of its own: TLS from
`ssl.create_default_context()`, proxies as urllib reads them, no redirects (a redirect would carry
the key's header to another host), no retries, a connect deadline and a deadline for the whole
request, and a reply limit. Every error text has the key replaced by `<key>`.
"""

import http.client
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from functools import partial
from http.client import HTTPConnection, HTTPSConnection
from typing import Any, cast
from urllib.parse import urlsplit

from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.ai_models import ProviderError, ProviderErrorKind
from coding_study.domain.errors import ConfigError

ENDPOINT_VARIABLE = "CSTUDY_AI_ENDPOINT"
CONNECT_TIMEOUT_S = 10.0
MAX_REPLY_BYTES = 4 * 1024 * 1024
MESSAGE_CHARACTERS = 200
"""How much of a provider's own message an error text carries."""
CHUNK_BYTES = 64 * 1024
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
ENDPOINT_SHAPE = "expected http://127.0.0.1:<port> or http://[::1]:<port>"

type JsonObject = Mapping[str, object]


def endpoint_override(environ: Mapping[str, str]) -> str | None:
    """The origin `CSTUDY_AI_ENDPOINT` names, or None when it is unset. Raises ConfigError (exit
    code 4) for any value but a loopback address and a port, before anything is sent."""
    value = environ.get(ENDPOINT_VARIABLE)
    if value is None:
        return None
    refusal = ConfigError(ENDPOINT_VARIABLE, [f'{ENDPOINT_SHAPE}, not "{value}"'])
    try:
        parts = urlsplit(value)
        host, port = parts.hostname, parts.port
    except ValueError:
        raise refusal from None
    plain = (
        parts.scheme == "http"
        and host in LOOPBACK_HOSTS
        and port is not None
        and port > 0
        and parts.username is None
        and parts.password is None
        and parts.path in ("", "/")
        and not parts.query
        and not parts.fragment
    )
    if not plain:
        raise refusal
    return f"http://[{host}]:{port}" if host == "::1" else f"http://{host}:{port}"


class JsonClient:
    """What the provider adapters send through. One per process; a request opens its own
    connection."""

    def __init__(self, environ: Mapping[str, str], version: str) -> None:
        """Raises ConfigError for a `CSTUDY_AI_ENDPOINT` that is not a loopback address."""
        self._endpoint = endpoint_override(environ)
        self._user_agent = f"cstudy/{version}"
        self._context: ssl.SSLContext | None = None

    def get(
        self,
        provider: Provider,
        origin: str,
        path: str,
        *,
        headers: Mapping[str, str],
        key: ApiKey,
        deadline_s: float,
    ) -> JsonObject:
        """The JSON object the provider answers a GET with. Raises ProviderError."""
        return self._send(provider, "GET", origin, path, None, headers, key, deadline_s, None)

    def post(
        self,
        provider: Provider,
        origin: str,
        path: str,
        body: JsonObject,
        *,
        headers: Mapping[str, str],
        key: ApiKey,
        deadline_s: float,
        model_id: str | None = None,
    ) -> JsonObject:
        """The JSON object the provider answers a POST of `body` with. `model_id` is the model the
        request names, which a 404, or a 400 that names it, is reported against. Raises
        ProviderError."""
        data = json.dumps(body, ensure_ascii=False).encode()
        return self._send(provider, "POST", origin, path, data, headers, key, deadline_s, model_id)

    def _send(
        self,
        provider: Provider,
        method: str,
        origin: str,
        path: str,
        data: bytes | None,
        headers: Mapping[str, str],
        key: ApiKey,
        deadline_s: float,
        model_id: str | None,
    ) -> JsonObject:
        base = self._endpoint or origin
        url = f"{base}{path}"
        host = urlsplit(url).hostname or base
        link = _Deadline(deadline_s)
        sent = {"User-Agent": self._user_agent, **headers}
        if data is not None:
            sent["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=sent, method=method)
        try:
            status, body = self._exchange(request, link)
        except TimeoutError:
            raise _failed(key, *_timed_out(provider, host, deadline_s, link)) from None
        except _ReplyTooLargeError:
            message = f"{provider} sent a reply over 4 MiB"
            raise _failed(key, ProviderErrorKind.INVALID_REPLY, message) from None
        except (OSError, http.client.HTTPException) as error:
            message = f"could not reach {host}: {_reason(error)}"
            raise _failed(key, ProviderErrorKind.NETWORK, message) from None
        parsed = _json_object(body)
        if 200 <= status < 300:
            if parsed is None:
                message = f"{provider} sent a reply that is not a JSON object"
                raise _failed(key, ProviderErrorKind.INVALID_REPLY, message)
            return parsed
        text = body.decode("utf-8", errors="replace")
        if provider is Provider.GOOGLE and status == 400 and _invalid_key(parsed):
            raise _refused_key(provider, status, key)
        raise status_error(provider, status, _message(parsed, text), key, model_id)

    def _exchange(self, request: urllib.request.Request, link: "_Deadline") -> tuple[int, bytes]:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}) if self._endpoint else urllib.request.ProxyHandler(),
            _PlainHandler(link),
            _SecureHandler(link, self._tls()),
            _NoRedirect(),
        )
        try:
            with opener.open(request, timeout=link.connect_s) as response:
                return response.status, _read(response, link)
        except urllib.error.HTTPError as error:
            with error:
                return error.code, _read(error, link)
        except urllib.error.URLError as error:
            if isinstance(error.reason, Exception):
                raise error.reason from None
            raise OSError(str(error.reason)) from None

    def _tls(self) -> ssl.SSLContext:
        if self._context is None:
            self._context = ssl.create_default_context()
        return self._context


def status_error(
    provider: Provider, status: int, message: str, key: ApiKey, model_id: str | None
) -> ProviderError:
    """The error for an HTTP status that is not a success (docs/specs/ai.md#errors). `message` is
    the provider's own text, which this shortens and scrubs of the key."""
    if status in (401, 403):
        return _refused_key(provider, status, key)
    if status == 429:
        text = f"{provider} is limiting this key's requests (429): try again later"
        return _failed(key, ProviderErrorKind.RATE_LIMIT, text)
    if model_id is not None and (
        status == 404 or (status == 400 and _names_model(message, model_id))
    ):
        text = (
            f"{provider} has no model {model_id}, or it cannot answer in a JSON schema: "
            f"see cstudy ai models {provider}"
        )
        return _failed(key, ProviderErrorKind.MODEL, text)
    shown = " ".join(key.scrub(message).split())[:MESSAGE_CHARACTERS]
    return _failed(key, ProviderErrorKind.PROVIDER, f"{provider} failed ({status}): {shown}")


def _refused_key(provider: Provider, status: int, key: ApiKey) -> ProviderError:
    text = f"{provider} refused the key ({status}): set it again with cstudy ai key {provider}"
    return _failed(key, ProviderErrorKind.AUTH, text)


def _invalid_key(parsed: JsonObject | None) -> bool:
    """Whether a Google error document gives `API_KEY_INVALID` as a detail's reason."""
    error = parsed.get("error") if parsed is not None else None
    details = cast("JsonObject", error).get("details") if isinstance(error, dict) else None
    if not isinstance(details, list):
        return False
    return any(
        isinstance(detail, dict) and cast("JsonObject", detail).get("reason") == "API_KEY_INVALID"
        for detail in cast("list[object]", details)
    )


def _names_model(message: str, model_id: str) -> bool:
    lowered = message.lower()
    return model_id.lower() in lowered or any(
        word in lowered for word in ("schema", "structured", "response_format")
    )


def _failed(key: ApiKey, kind: ProviderErrorKind, message: str) -> ProviderError:
    return ProviderError(kind, key.scrub(message))


def _timed_out(
    provider: Provider, host: str, deadline_s: float, link: "_Deadline"
) -> tuple[ProviderErrorKind, str]:
    if not link.connected:
        return ProviderErrorKind.NETWORK, f"could not reach {host}: connecting timed out"
    return ProviderErrorKind.TIMEOUT, f"{provider} did not answer within {deadline_s:g} s"


def _reason(error: BaseException) -> str:
    if isinstance(error, OSError) and error.strerror:
        return error.strerror
    return str(error) or type(error).__name__


def _json_object(body: bytes) -> JsonObject | None:
    try:
        parsed: object = json.loads(body)
    except ValueError:
        return None
    return cast("JsonObject", parsed) if isinstance(parsed, dict) else None


def _message(parsed: JsonObject | None, text: str) -> str:
    """What a provider's error document says: `error.message`, `error`, or `message`."""
    if parsed is None:
        return text
    error = parsed.get("error")
    if isinstance(error, dict):
        nested = cast("JsonObject", error).get("message")
        if isinstance(nested, str):
            return nested
    if isinstance(error, str):
        return error
    message = parsed.get("message")
    return message if isinstance(message, str) else text


class _ReplyTooLargeError(Exception):
    pass


class _Deadline:
    """The clock of one request, and the socket its connection opened."""

    def __init__(self, deadline_s: float) -> None:
        self._end = time.monotonic() + deadline_s
        self.connect_s = min(CONNECT_TIMEOUT_S, deadline_s)
        self.socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self.socket is not None

    def adopt(self, connected: socket.socket) -> None:
        """Takes the connection's socket, which waits for the rest of the request's time."""
        self.socket = connected
        self.arm()

    def arm(self) -> None:
        """Lets the next read wait only for the time that is left. Raises TimeoutError once the
        request is out of time."""
        left = self._end - time.monotonic()
        if left <= 0:
            raise TimeoutError
        if self.socket is not None:
            try:
                self.socket.settimeout(left)
            except OSError:
                return


def _read(response: Any, link: _Deadline) -> bytes:
    """The body, at most `MAX_REPLY_BYTES`, within the request's deadline."""
    declared: str = response.headers.get("Content-Length", "")
    if declared.isdigit() and int(declared) > MAX_REPLY_BYTES:
        raise _ReplyTooLargeError
    chunks: list[bytes] = []
    total = 0
    while True:
        link.arm()
        chunk: bytes = response.read1(min(CHUNK_BYTES, MAX_REPLY_BYTES + 1 - total))
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_REPLY_BYTES:
            raise _ReplyTooLargeError
        chunks.append(chunk)


class _PlainConnection(HTTPConnection):
    """Once connected, waits for the rest of the request's time instead of the connect timeout."""

    def __init__(self, *arguments: Any, link: _Deadline, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self._link = link

    def connect(self) -> None:
        super().connect()
        self._link.adopt(self.sock)


class _SecureConnection(HTTPSConnection):
    """As `_PlainConnection`, after the TLS handshake."""

    def __init__(self, *arguments: Any, link: _Deadline, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self._link = link

    def connect(self) -> None:
        super().connect()
        self._link.adopt(self.sock)


class _PlainHandler(urllib.request.HTTPHandler):
    """Only the test endpoint is plain HTTP."""

    def __init__(self, link: _Deadline) -> None:
        super().__init__()
        self._link = link

    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(partial(_PlainConnection, link=self._link), req)


class _SecureHandler(urllib.request.HTTPSHandler):
    def __init__(self, link: _Deadline, context: ssl.SSLContext) -> None:
        super().__init__(context=context)
        self._link = link
        self._tls = context

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        connection = partial(_SecureConnection, link=self._link)
        return self.do_open(connection, req, context=self._tls)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is a failure: following it would send the key's header to another host."""

    def redirect_request(self, *_arguments: Any, **_keywords: Any) -> None:
        return None
