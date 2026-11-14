import re

DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443, "ftp": 21}
SECURE_SCHEMES = ("https", "wss")
SAFELISTED_METHODS = ("GET", "HEAD", "POST")
NORMALIZED_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT")
OPAQUE = "null"
WILDCARD = "*"

SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")
HOST = re.compile(r"[A-Za-z0-9.-]+")
PORT = re.compile(r"[0-9]*")
LABELS = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*")
PATTERN = re.compile(r"([^:/]+)://\*\.([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)(?::([0-9]+))?")
RANGE = re.compile(r"bytes=([0-9]+)-([0-9]*)")
LANGUAGE_VALUE = re.compile(r"[0-9A-Za-z *,\-.;=]*")
UNSAFE_BYTES = frozenset('"():<>?@[\\]{}\x7f')
SIMPLE_CONTENT_TYPES = ("application/x-www-form-urlencoded", "multipart/form-data", "text/plain")
MAX_SAFELISTED_VALUE = 128
MAX_SAFELISTED_TOTAL = 1024

ALLOW_ORIGIN = "Access-Control-Allow-Origin"
ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials"
ALLOW_METHODS = "Access-Control-Allow-Methods"
ALLOW_HEADERS = "Access-Control-Allow-Headers"
MAX_AGE = "Access-Control-Max-Age"


def port_suffix(scheme: str, digits: str) -> str | None:
    """`:port` for a port that differs from the scheme's default, `` otherwise, None if invalid."""
    if digits == "":
        return ""
    port = int(digits)
    if port > 65535:
        return None
    return "" if port == DEFAULT_PORTS[scheme] else f":{port}"


def serialize_origin(url: str) -> str:
    scheme, colon, rest = url.partition(":")
    if not colon or not SCHEME.fullmatch(scheme):
        return OPAQUE
    scheme = scheme.lower()
    if scheme not in DEFAULT_PORTS or not rest.startswith("//"):
        return OPAQUE
    authority = re.split(r"[/?#]", rest[2:], maxsplit=1)[0]
    host_and_port = authority.rpartition("@")[2]
    host, _, digits = host_and_port.partition(":")
    if not HOST.fullmatch(host) or not PORT.fullmatch(digits):
        return OPAQUE
    suffix = port_suffix(scheme, digits)
    return OPAQUE if suffix is None else f"{scheme}://{host.lower()}{suffix}"


def unsafe(value: str) -> bool:
    return any((ord(c) < 0x20 and c != "\t") or c in UNSAFE_BYTES for c in value)


def safelisted_header(name: str, value: str) -> bool:
    """CORS-safelisted request-header, after the Fetch standard."""
    if len(value) > MAX_SAFELISTED_VALUE:
        return False
    name = name.lower()
    if name == "accept":
        return not unsafe(value)
    if name in ("accept-language", "content-language"):
        return LANGUAGE_VALUE.fullmatch(value) is not None
    if name == "content-type":
        essence = value.split(";", 1)[0].strip(" \t").lower()
        return not unsafe(value) and essence in SIMPLE_CONTENT_TYPES
    if name == "range":
        match = RANGE.fullmatch(value)
        return match is not None and (match[2] == "" or int(match[1]) <= int(match[2]))
    return False


class _Pattern:
    """`scheme://*.host[:port]`: one or more labels in front of `.host`, same scheme and port."""

    __slots__ = ("broad", "prefix", "secure", "suffix", "text")

    def __init__(self, scheme: str, host: str, port: str) -> None:
        self.prefix = f"{scheme}://"
        self.suffix = f".{host}{port}"
        self.text = f"{scheme}://*.{host}{port}"
        self.secure = scheme in SECURE_SCHEMES
        self.broad = "." not in host

    def matches(self, origin: str) -> bool:
        if not (origin.startswith(self.prefix) and origin.endswith(self.suffix)):
            return False
        middle = origin[len(self.prefix) : len(origin) - len(self.suffix)]
        return LABELS.fullmatch(middle) is not None


class CorsPolicy:
    def __init__(self) -> None:
        self._origins: set[str] = set()
        self._patterns: dict[str, _Pattern] = {}
        self._methods: list[str] = []
        self._headers: list[str] = []
        self._max_age: int | None = None
        self._any_origin = False
        self._credentials = False

    # Level 1
    def origin_of(self, url: str) -> str:
        return serialize_origin(url)

    def allow_origin(self, url: str) -> str:
        # Only the literal text null allows the opaque origin; a URL without an origin is refused.
        origin = serialize_origin(url)
        if origin == OPAQUE and url != OPAQUE:
            return ""
        self._origins.add(origin)
        return origin

    def allow_origin_for(self, origin: str) -> str:
        if self._any_origin and not self._credentials:
            return WILDCARD
        if self._listed(origin):
            return origin
        return WILDCARD if self._any_origin else ""

    # Level 2
    def allow_method(self, method: str) -> bool:
        if method in self._methods:
            return False
        self._methods.append(method)
        return True

    def allow_header(self, name: str) -> bool:
        name = name.lower()
        if name in self._headers:
            return False
        self._headers.append(name)
        return True

    def set_max_age(self, seconds: int) -> None:
        self._max_age = seconds

    def needs_preflight(self, method: str, headers: list[list[str]]) -> bool:
        if method.upper() in NORMALIZED_METHODS:
            method = method.upper()
        if method not in SAFELISTED_METHODS:
            return True
        safelisted = [value for name, value in headers if safelisted_header(name, value)]
        if len(safelisted) < len(headers):
            return True
        return sum(len(value) for value in safelisted) > MAX_SAFELISTED_TOTAL

    def preflight_response(self, origin: str, method: str, request_headers: str) -> list[list[str]]:
        allowed_origin = self.allow_origin_for(origin)
        if not allowed_origin:
            return []
        credentialed = self._credentialed(origin, allowed_origin)
        requested = [n.strip(" \t").lower() for n in request_headers.split(",") if n.strip(" \t")]
        if not self._method_allowed(method, credentialed) or not all(
            self._header_allowed(name, credentialed) for name in requested
        ):
            return []
        rows = [[ALLOW_ORIGIN, allowed_origin]]
        if credentialed:
            rows.append([ALLOW_CREDENTIALS, "true"])
        if self._methods:
            rows.append([ALLOW_METHODS, ", ".join(self._methods)])
        if self._headers:
            rows.append([ALLOW_HEADERS, ", ".join(self._headers)])
        if self._max_age is not None:
            rows.append([MAX_AGE, str(self._max_age)])
        return rows

    # Level 3
    def allow_any_origin(self) -> None:
        self._any_origin = True

    def allow_credentials(self) -> None:
        self._credentials = True

    def actual_response(self, origin: str) -> list[list[str]]:
        allowed_origin = self.allow_origin_for(origin)
        rows = [[ALLOW_ORIGIN, allowed_origin]] if allowed_origin else []
        if self._credentialed(origin, allowed_origin):
            rows.append([ALLOW_CREDENTIALS, "true"])
        if not (self._any_origin and not self._credentials):
            rows.append(["Vary", "Origin"])
        return rows

    # Level 4
    def allow_pattern(self, pattern: str) -> bool:
        match = PATTERN.fullmatch(pattern)
        if match is None or match[1].lower() not in DEFAULT_PORTS:
            return False
        scheme = match[1].lower()
        suffix = port_suffix(scheme, match[3] or "")
        if suffix is None:
            return False
        compiled = _Pattern(scheme, match[2].lower(), suffix)
        if compiled.text in self._patterns:
            return False
        self._patterns[compiled.text] = compiled
        return True

    def lint(self) -> list[list[str]]:
        findings = [["broad-pattern", p.text] for p in self._patterns.values() if p.broad]
        if OPAQUE in self._origins:
            findings.append(["null-origin-allowed", OPAQUE])
        if self._credentials:
            findings += [
                ["credentials-to-insecure-origin", origin]
                for origin in self._origins
                if origin != OPAQUE and origin.split("://")[0] not in SECURE_SCHEMES
            ]
            findings += [
                ["credentials-to-insecure-origin", p.text]
                for p in self._patterns.values()
                if not p.secure
            ]
        return sorted(findings)

    def _listed(self, origin: str) -> bool:
        return origin in self._origins or any(p.matches(origin) for p in self._patterns.values())

    def _credentialed(self, origin: str, allowed_origin: str) -> bool:
        """Credentials are allowed only next to the requesting origin itself, never next to *."""
        return (
            self._credentials and allowed_origin not in ("", WILDCARD) and allowed_origin == origin
        )

    def _method_allowed(self, method: str, credentialed: bool) -> bool:
        if method in SAFELISTED_METHODS or method in self._methods:
            return True
        return WILDCARD in self._methods and not credentialed

    def _header_allowed(self, name: str, credentialed: bool) -> bool:
        if name in self._headers:
            return True
        return WILDCARD in self._headers and not credentialed and name != "authorization"
