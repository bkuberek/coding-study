"""Origins as a stack's network names them, `http://idp:8080`: what a case's absolute URL may name
(docs/specs/service-projects.md#multi-step-cases).

The grader reaches none of them by that name. It dials the address the stack publishes for each,
through the forwarder, and sends the name as the request's `Host`.
"""

from collections.abc import Iterable
from urllib.parse import urlsplit

from coding_study.domain.sandbox import APP_SERVICE, MOCK_PORT

HTTP = "http"
DEFAULT_HTTP_PORT = 80
ABSOLUTE_PREFIXES = ("http://", "https://")


def is_absolute(target: str) -> bool:
    return target.lower().startswith(ABSOLUTE_PREFIXES)


def origin_of(base: str, port: int) -> str:
    return f"{HTTP}://{base.lower()}:{port}"


def split_url(url: str) -> tuple[str, str] | None:
    """The origin, `http://<name>:<port>` with the port always written, and the path with its
    query; None for a URL the grader cannot send, over `https` or with no name. A fragment never
    leaves a browser, so it is dropped."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() != HTTP or not parts.hostname:
        return None
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return origin_of(parts.hostname, port or DEFAULT_HTTP_PORT), path


def host_header(origin: str) -> str:
    """What a request to `origin` sends as its `Host`: the name and port it was written with."""
    return origin.removeprefix(f"{HTTP}://")


def app_origin(app_port: int) -> str:
    """The app's own origin inside the stack, where a provider sends a browser back to it."""
    return origin_of(APP_SERVICE, app_port)


def declared_origins(app_port: int, mocks: Iterable[str]) -> frozenset[str]:
    """What S23 lets a case's absolute URL name: the app and each mock server. P10 adds each
    backing service a problem publishes to the grader."""
    return frozenset({app_origin(app_port), *(origin_of(mock, MOCK_PORT) for mock in mocks)})
