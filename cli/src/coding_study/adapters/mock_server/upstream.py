"""Passing a request through to a mock server's upstream, a service on the stack's network such as
an identity provider, and bringing its answer back whole, each `Set-Cookie` line apart."""

import http.client
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from .replies import Reply, json_reply

UPSTREAM_TIMEOUT_S = 10.0
"""As long as a client of the mock server may stall: an upstream gets no more than they do."""
MAX_UPSTREAM_BODY_BYTES = 8 * 1024 * 1024
"""Past what any grader keeps, and a bound on what the mock server holds for one answer."""
DEFAULT_HTTP_PORT = 80
BAD_GATEWAY = 502
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
"""Headers about one connection, which a proxy never passes on (RFC 9110, section 7.6.1)."""
LENGTH = "content-length"
ACCEPT_ENCODING = "accept-encoding"
IDENTITY = "identity"
"""What the upstream is asked to answer in, so that a JWT in its body can be read and rewritten."""


@dataclass(frozen=True)
class ForwardedRequest:
    method: str
    target: str
    """The path and query as the client sent them."""
    headers: Mapping[str, str]
    """Lowercase names, `host` among them: the upstream hears the name the client asked for."""
    body: bytes


def fetched(upstream: str, request: ForwardedRequest, mock: str) -> Reply:
    """The upstream's answer, or a 502 that names it when it gives none."""
    parts = urlsplit(upstream)
    connection = http.client.HTTPConnection(
        parts.hostname or "", parts.port or DEFAULT_HTTP_PORT, timeout=UPSTREAM_TIMEOUT_S
    )
    try:
        connection.request(
            request.method, request.target, body=request.body or None, headers=_sent(request)
        )
        response = connection.getresponse()
        body = response.read(MAX_UPSTREAM_BODY_BYTES + 1)
    except (OSError, http.client.HTTPException) as error:
        return _bad_gateway(mock, upstream, f"it did not answer: {error}")
    finally:
        connection.close()
    if len(body) > MAX_UPSTREAM_BODY_BYTES:
        return _bad_gateway(mock, upstream, f"its body is over {MAX_UPSTREAM_BODY_BYTES} bytes")
    lines = tuple((name, value) for name, value in response.getheaders() if _returned(name.lower()))
    return Reply(response.status, {}, body, header_lines=lines)


def _sent(request: ForwardedRequest) -> dict[str, str]:
    kept = {
        name: value
        for name, value in request.headers.items()
        if name not in HOP_BY_HOP and name not in {LENGTH, ACCEPT_ENCODING}
    }
    return {**kept, ACCEPT_ENCODING: IDENTITY}


def _returned(name: str) -> bool:
    """The mock server writes its own `Content-Length`, after any rewrite of the body."""
    return name not in HOP_BY_HOP and name != LENGTH


def _bad_gateway(mock: str, upstream: str, detail: str) -> Reply:
    document = {"error": "bad gateway", "mock": mock, "upstream": upstream, "detail": detail}
    return json_reply(BAD_GATEWAY, document)
