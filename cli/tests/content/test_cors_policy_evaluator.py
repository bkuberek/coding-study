"""cors-policy-evaluator promises that its hidden cases catch the classic mistakes of a server's
cross-origin policy: origins serialized with their default port, in mixed case or with the wrong
user information cut off, a request's Origin normalized or matched by prefix, a URL without an
origin quietly allowing null, a preflight safelist that is too lenient or too strict, a partial
preflight answer, the wildcard sent with credentials or every origin echoed instead, Vary missing
or misplaced, method and header wildcards that ignore credentials, patterns that match by suffix
or prefix, and a linter that reports the wrong things. These tests replay every case against a
model of the policy written from the statement, which must give every expected output, and
against that model with one mistake planted at a time, which some hidden case must fail. A
mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0350-cors-policy-evaluator"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

DEFAULTS = {"http": "80", "https": "443", "ws": "80", "wss": "443", "ftp": "21"}
URL = re.compile(r"([A-Za-z][A-Za-z0-9+.\-]*)://([^/?#]*)(?:[/?#].*)?", re.DOTALL)
AUTHORITY = re.compile(r"(?:.*@)?([A-Za-z0-9.\-]+)(?::([0-9]*))?", re.DOTALL)
PATTERN = re.compile(
    r"([A-Za-z][A-Za-z0-9+.\-]*)://\*\.((?:[A-Za-z0-9\-]+\.)*[A-Za-z0-9\-]+)(?::([0-9]+))?"
)
UNSAFE = set('"():<>?@[\\]{}') | {chr(127)} | {chr(c) for c in range(32) if c != 9}
LANGUAGE = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz *,-.;=")
FORMS = {"application/x-www-form-urlencoded", "multipart/form-data", "text/plain"}
ACAO, ACAC = "Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"


class Model:
    """The policy as the statement words it: a regex reading of URLs, one decision with four
    rules, and each check of the safelist and the linter as its own method. Each mistake below
    overrides one of them."""

    def __init__(self) -> None:
        self.listed: list[str] = []
        self.patterns: list[tuple[str, str, str]] = []
        self.methods: list[str] = []
        self.headers: list[str] = []
        self.max_age: int | None = None
        self.any = False
        self.creds = False

    # --- level 1
    def port_part(self, scheme: str, digits: str | None) -> str | None:
        if not digits:
            return ""
        if int(digits) > 65535:
            return None
        return "" if int(digits) == int(DEFAULTS[scheme]) else ":" + str(int(digits))

    def host_and_port(self, authority: str) -> tuple[str, str | None] | None:
        found = AUTHORITY.fullmatch(authority)
        return None if found is None else (found[1], found[2])

    def origin_of(self, url: str) -> str:
        found = URL.fullmatch(url)
        if found is None or found[1].lower() not in DEFAULTS:
            return "null"
        scheme = found[1].lower()
        parts = self.host_and_port(found[2])
        if parts is None:
            return "null"
        port = self.port_part(scheme, parts[1])
        return "null" if port is None else scheme + "://" + parts[0].lower() + port

    def allow_origin(self, url: str) -> str:
        origin = self.origin_of(url)
        if origin == "null" and url != "null":
            return ""
        if origin not in self.listed:
            self.listed.append(origin)
        return origin

    def is_listed(self, origin: str) -> bool:
        return origin in self.listed or any(self.matches(p, origin) for p in self.patterns)

    def decide(self, origin: str) -> str:
        if self.any and not self.creds:
            return "*"
        if self.is_listed(origin):
            return origin
        return "*" if self.any else ""

    def allow_origin_for(self, origin: str) -> str:
        return self.decide(origin)

    # --- level 2
    def allow_method(self, method: str) -> bool:
        if method in self.methods:
            return False
        self.methods.append(method)
        return True

    def allow_header(self, name: str) -> bool:
        if name.lower() in self.headers:
            return False
        self.headers.append(name.lower())
        return True

    def set_max_age(self, seconds: int) -> None:
        self.max_age = seconds

    def normalize(self, method: str) -> str:
        upper = method.upper()
        return upper if upper in ("DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT") else method

    def too_long(self, value: str) -> bool:
        return len(value) > 128

    def too_much(self, total: int) -> bool:
        return total > 1024

    def has_unsafe(self, value: str) -> bool:
        return any(c in UNSAFE for c in value)

    def essence(self, value: str) -> str:
        return value.split(";")[0].strip(" \t").lower()

    def range_ok(self, value: str) -> bool:
        found = re.fullmatch(r"bytes=([0-9]+)-([0-9]*)", value)
        return found is not None and (not found[2] or int(found[1]) <= int(found[2]))

    def language_ok(self, value: str) -> bool:
        return set(value) <= LANGUAGE

    def safelisted(self, name: str, value: str) -> bool:
        if self.too_long(value):
            return False
        key = name.lower()
        if key == "accept":
            return not self.has_unsafe(value)
        if key in ("accept-language", "content-language"):
            return self.language_ok(value)
        if key == "content-type":
            return not self.has_unsafe(value) and self.essence(value) in FORMS
        return key == "range" and self.range_ok(value)

    def needs_preflight(self, method: str, headers: list[list[str]]) -> bool:
        if self.normalize(method) not in ("GET", "HEAD", "POST"):
            return True
        if not all(self.safelisted(name, value) for name, value in headers):
            return True
        return self.too_much(sum(len(value) for _, value in headers))

    def credentialed(self, origin: str, value: str) -> bool:
        return self.creds and value not in ("", "*") and value == origin

    def method_ok(self, method: str, credentialed: bool) -> bool:
        if method in ("GET", "HEAD", "POST") or method in self.methods:
            return True
        return "*" in self.methods and not credentialed

    def header_ok(self, name: str, credentialed: bool) -> bool:
        if name in self.headers:
            return True
        return "*" in self.headers and not credentialed and name != "authorization"

    def requested(self, text: str) -> list[str]:
        return [n.strip(" \t").lower() for n in text.split(",") if n.strip(" \t")]

    def preflight_rows(self, value: str, credentialed: bool) -> list[list[str]]:
        rows = [[ACAO, value]] + ([[ACAC, "true"]] if credentialed else [])
        if self.methods:
            rows.append(["Access-Control-Allow-Methods", ", ".join(self.methods)])
        if self.headers:
            rows.append(["Access-Control-Allow-Headers", ", ".join(self.headers)])
        if self.max_age is not None:
            rows.append(["Access-Control-Max-Age", str(self.max_age)])
        return rows

    def preflight_response(self, origin: str, method: str, request_headers: str) -> list:
        value = self.decide(origin)
        if not value:
            return []
        credentialed = self.credentialed(origin, value)
        if not self.method_ok(method, credentialed):
            return []
        if not all(self.header_ok(n, credentialed) for n in self.requested(request_headers)):
            return []
        return self.preflight_rows(value, credentialed)

    # --- level 3
    def allow_any_origin(self) -> None:
        self.any = True

    def allow_credentials(self) -> None:
        self.creds = True

    def varies(self, value: str) -> bool:
        return not (self.any and not self.creds)

    def actual_response(self, origin: str) -> list[list[str]]:
        value = self.decide(origin)
        rows = [[ACAO, value]] if value else []
        if self.credentialed(origin, value):
            rows.append([ACAC, "true"])
        if self.varies(value):
            rows.append(["Vary", "Origin"])
        return rows

    # --- level 4
    def allow_pattern(self, pattern: str) -> bool:
        found = PATTERN.fullmatch(pattern)
        if found is None or found[1].lower() not in DEFAULTS:
            return False
        scheme = found[1].lower()
        port = self.port_part(scheme, found[3])
        if port is None:
            return False
        entry = (scheme, found[2].lower(), port)
        if entry in self.patterns:
            return False
        self.patterns.append(entry)
        return True

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        shape = re.escape(scheme) + r"://(?:[a-z0-9\-]+\.)+" + re.escape(host + port)
        return re.fullmatch(shape, origin) is not None

    def text(self, pattern: tuple[str, str, str]) -> str:
        return pattern[0] + "://*." + pattern[1] + pattern[2]

    def broad(self, pattern: tuple[str, str, str]) -> bool:
        return pattern[1].count(".") == 0

    def insecure(self, scheme: str) -> bool:
        return scheme not in ("https", "wss")

    def null_finding(self) -> bool:
        return "null" in self.listed

    def lint(self) -> list[list[str]]:
        rows = [["broad-pattern", self.text(p)] for p in self.patterns if self.broad(p)]
        if self.null_finding():
            rows.append(["null-origin-allowed", "null"])
        if self.creds:
            for origin in self.listed:
                if origin != "null" and self.insecure(origin.split(":")[0]):
                    rows.append(["credentials-to-insecure-origin", origin])
            for p in self.patterns:
                if self.insecure(p[0]):
                    rows.append(["credentials-to-insecure-origin", self.text(p)])
        return self.order(rows)

    def order(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows)


# --- level 1 mistakes
class KeepsTheDefaultPort(Model):
    """`https://x.example:443` keeps `:443`, so it never equals what the browser sends."""

    def port_part(self, scheme: str, digits: str | None) -> str | None:
        if digits and int(digits) > 65535:
            return None
        return ":" + str(int(digits)) if digits else ""


class KeepsLeadingZeros(Model):
    """The port is copied as written, so `:0443` is not recognized as the default."""

    def port_part(self, scheme: str, digits: str | None) -> str | None:
        if not digits:
            return ""
        if int(digits) > 65535:
            return None
        return "" if digits == DEFAULTS[scheme] else ":" + digits


class EmptyPortIsAnError(Model):
    """`https://x.example:` is read as a broken URL instead of the default port."""

    def port_part(self, scheme: str, digits: str | None) -> str | None:
        return None if digits == "" else super().port_part(scheme, digits)


class NoPortLimit(Model):
    """Ports above 65535 are accepted."""

    def port_part(self, scheme: str, digits: str | None) -> str | None:
        if not digits:
            return ""
        return "" if int(digits) == int(DEFAULTS[scheme]) else ":" + str(int(digits))


class HostCaseKept(Model):
    """The host is not lowercased."""

    def origin_of(self, url: str) -> str:
        found = URL.fullmatch(url)
        if found is None or found[1].lower() not in DEFAULTS:
            return "null"
        parts = self.host_and_port(found[2])
        if parts is None:
            return "null"
        port = self.port_part(found[1].lower(), parts[1])
        return "null" if port is None else found[1].lower() + "://" + parts[0] + port


class UserInfoUntilTheFirstAt(Model):
    """User information is cut at the first `@`, so the rest still holds a second one."""

    def host_and_port(self, authority: str) -> tuple[str, str | None] | None:
        found = re.fullmatch(r"([A-Za-z0-9.\-]+)(?::([0-9]*))?", authority.split("@", 1)[-1])
        return None if found is None else (found[1], found[2])


class UserInfoNotRemoved(Model):
    """The authority is read as host and port, so `user@host` is not a host at all."""

    def host_and_port(self, authority: str) -> tuple[str, str | None] | None:
        found = re.fullmatch(r"([A-Za-z0-9.\-]+)(?::([0-9]*))?", authority)
        return None if found is None else (found[1], found[2])


class AtSignSearchedInTheWholeUrl(Model):
    """The last `@` of the whole URL counts, including one in the path."""

    def origin_of(self, url: str) -> str:
        scheme, _, rest = url.partition("://")
        return super().origin_of(scheme + "://" + rest.rsplit("@", 1)[-1] if "@" in rest else url)


class SlashesOptional(Model):
    """`https:app.example` is read like `https://app.example`."""

    def origin_of(self, url: str) -> str:
        found = re.fullmatch(r"([A-Za-z][A-Za-z0-9+.\-]*):(?!//)(.+)", url)
        if found is not None:
            url = found[1] + "://" + found[2]
        return super().origin_of(url)


class EveryHierarchicalSchemeHasAnOrigin(Model):
    """Any `scheme://host` gets a tuple origin, so `git+ssh://` is not opaque."""

    def origin_of(self, url: str) -> str:
        found = URL.fullmatch(url)
        if found is not None and found[1].lower() not in DEFAULTS:
            parts = self.host_and_port(found[2])
            if parts is not None:
                return found[1].lower() + "://" + parts[0].lower()
        return super().origin_of(url)


class OpaqueUrlsAllowNull(Model):
    """`allowOrigin` stores `null` for any URL without an origin of its own."""

    def allow_origin(self, url: str) -> str:
        origin = self.origin_of(url)
        if origin not in self.listed:
            self.listed.append(origin)
        return origin


class RequestOriginNormalized(Model):
    """The request's Origin is lowercased and trimmed of a slash before the lookup."""

    def is_listed(self, origin: str) -> bool:
        return super().is_listed(origin.lower().rstrip("/"))

    def decide(self, origin: str) -> str:
        value = super().decide(origin)
        return origin if value and value != "*" else value


class ListedBySuffix(Model):
    """An origin is listed when it ends with an allowed origin's host."""

    def is_listed(self, origin: str) -> bool:
        hosts = [entry.split("://")[-1] for entry in self.listed]
        return super().is_listed(origin) or any(origin.endswith(h) for h in hosts)


class ListedByPrefix(Model):
    """An origin is listed when it starts with an allowed origin."""

    def is_listed(self, origin: str) -> bool:
        return super().is_listed(origin) or any(
            origin.startswith(entry) for entry in self.listed if entry != "null"
        )


# --- level 2 mistakes
class MethodNotNormalized(Model):
    """`get` and `post` are not recognized as simple methods."""

    def normalize(self, method: str) -> str:
        return method


class LimitAtOrAbove128(Model):
    """A value of exactly 128 characters is refused."""

    def too_long(self, value: str) -> bool:
        return len(value) >= 128


class NoValueLimit(Model):
    """Values of any length are safelisted."""

    def too_long(self, value: str) -> bool:
        return False


class NoTotalLimit(Model):
    """Values may add up to any length."""

    def too_much(self, total: int) -> bool:
        return False


class TotalLimitInclusive(Model):
    """A total of exactly 1024 characters needs a preflight."""

    def too_much(self, total: int) -> bool:
        return total >= 1024


class UnsafeCharactersIgnored(Model):
    """`accept` and `content-type` values are not checked for unsafe characters."""

    def has_unsafe(self, value: str) -> bool:
        return False


class TabIsUnsafe(Model):
    """The tab is counted with the other control characters."""

    def has_unsafe(self, value: str) -> bool:
        return super().has_unsafe(value) or "\t" in value


class EssenceCaseSensitive(Model):
    """`Text/Plain` is not recognized as `text/plain`."""

    def essence(self, value: str) -> str:
        return value.split(";")[0].strip(" \t")


class EssenceNotTrimmed(Model):
    """A space before the `;` makes the essence unknown."""

    def essence(self, value: str) -> str:
        return value.split(";")[0].lower()


class EssenceByPrefix(Model):
    """Any value starting with a form type is accepted, such as `text/plain+json`."""

    def essence(self, value: str) -> str:
        for form in FORMS:
            if value.lower().startswith(form):
                return form
        return super().essence(value)


class LanguageAllowsAnything(Model):
    """`accept-language` values are not checked."""

    def language_ok(self, value: str) -> bool:
        return True


class RangeAcceptsASuffix(Model):
    """`bytes=-500` is safelisted."""

    def range_ok(self, value: str) -> bool:
        return super().range_ok(value) or re.fullmatch(r"bytes=-[0-9]+", value) is not None


class RangeNotOrdered(Model):
    """`bytes=10-5` is safelisted."""

    def range_ok(self, value: str) -> bool:
        return re.fullmatch(r"bytes=[0-9]+-[0-9]*", value) is not None


class RangeNeverSafelisted(Model):
    """`range` is treated like any other header."""

    def range_ok(self, value: str) -> bool:
        return False


class HeaderNamesCaseSensitive(Model):
    """`CONTENT-TYPE` is not recognized as `content-type`."""

    def safelisted(self, name: str, value: str) -> bool:
        return name == name.lower() and super().safelisted(name, value)


class ServerSafelistsSimpleHeaders(Model):
    """The server lets `content-type` through without it being allowed."""

    def header_ok(self, name: str, credentialed: bool) -> bool:
        return name == "content-type" or super().header_ok(name, credentialed)


class MethodsCompareWithoutCase(Model):
    """`patch` matches the allowed `PATCH`."""

    def method_ok(self, method: str, credentialed: bool) -> bool:
        return super().method_ok(method.upper(), credentialed)


class SimpleMethodsMustBeListed(Model):
    """A preflight for `POST` fails unless `POST` was allowed."""

    def method_ok(self, method: str, credentialed: bool) -> bool:
        return method in self.methods or ("*" in self.methods and not credentialed)


class RequestedNamesNotTrimmed(Model):
    """Spaces around requested names are kept."""

    def requested(self, text: str) -> list[str]:
        return [name.lower() for name in text.split(",") if name]


class AnswersOnlyTheRequestedMethod(Model):
    """`Access-Control-Allow-Methods` holds only the method asked for."""

    def preflight_rows(self, value: str, credentialed: bool) -> list[list[str]]:
        rows = super().preflight_rows(value, credentialed)
        return [r for r in rows if r[0] != "Access-Control-Allow-Methods"] + (
            [["Access-Control-Allow-Methods", self.methods[0]]] if self.methods else []
        )


class DefaultMaxAgeSent(Model):
    """The default 5 seconds is sent when no max age was set."""

    def preflight_rows(self, value: str, credentialed: bool) -> list[list[str]]:
        rows = super().preflight_rows(value, credentialed)
        return rows if self.max_age is not None else [*rows, ["Access-Control-Max-Age", "5"]]


class PartialPreflightAnswer(Model):
    """A refused method or header still gets the origin header."""

    def preflight_response(self, origin: str, method: str, request_headers: str) -> list:
        rows = super().preflight_response(origin, method, request_headers)
        value = self.decide(origin)
        return rows if rows or not value else [[ACAO, value]]


# --- level 3 mistakes
class WildcardWithCredentials(Model):
    """`*` is sent together with `Access-Control-Allow-Credentials`."""

    def credentialed(self, origin: str, value: str) -> bool:
        return self.creds and value != ""


class EchoesAnyOriginWithCredentials(Model):
    """With any origin and credentials allowed, every origin is echoed with credentials."""

    def decide(self, origin: str) -> str:
        if self.any and self.creds and origin:
            return origin
        return super().decide(origin)

    def credentialed(self, origin: str, value: str) -> bool:
        return self.creds and value not in ("", "*") and value == origin


class ListedOriginsBeatTheStaticWildcard(Model):
    """An allow-listed origin is echoed even when the answer could be a static `*`."""

    def decide(self, origin: str) -> str:
        return origin if self.is_listed(origin) else super().decide(origin)


class VaryOnlyWhenAllowed(Model):
    """`Vary` is sent only next to an allowed origin."""

    def varies(self, value: str) -> bool:
        return value not in ("", "*")


class VaryAlways(Model):
    """`Vary` is sent even with the static `*`."""

    def varies(self, value: str) -> bool:
        return True


class CredentialsForAnEmptyOrigin(Model):
    """An empty Origin gets credentials, because `""` equals itself."""

    def credentialed(self, origin: str, value: str) -> bool:
        return self.creds and value != "*" and value == origin


class MethodWildcardIgnoresCredentials(Model):
    """`*` allows any method also next to credentials."""

    def method_ok(self, method: str, credentialed: bool) -> bool:
        return super().method_ok(method, False)


class HeaderWildcardIgnoresCredentials(Model):
    """`*` allows any header also next to credentials."""

    def header_ok(self, name: str, credentialed: bool) -> bool:
        return super().header_ok(name, False)


class WildcardCoversAuthorization(Model):
    """`*` also allows `authorization`."""

    def header_ok(self, name: str, credentialed: bool) -> bool:
        return name in self.headers or ("*" in self.headers and not credentialed)


class PreflightWithoutCredentials(Model):
    """The preflight answer never allows credentials."""

    def preflight_rows(self, value: str, credentialed: bool) -> list[list[str]]:
        return super().preflight_rows(value, False)


# --- level 4 mistakes
class PatternBySuffix(Model):
    """A pattern matches any origin that ends with its host, without the dot."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        return origin.startswith(scheme + "://") and origin.endswith(host + port)


class PatternByContainment(Model):
    """A pattern matches an origin that has `.host` anywhere after the scheme."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        return origin.startswith(scheme + "://") and "." + host + port in origin


class PatternMatchesTheApex(Model):
    """`*.example.com` also matches `example.com`."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        return super().matches(pattern, origin) or origin == scheme + "://" + host + port


class PatternOneLabelOnly(Model):
    """The wildcard stands for exactly one label."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        shape = re.escape(scheme) + r"://[a-z0-9\-]+\." + re.escape(host + port)
        return re.fullmatch(shape, origin) is not None


class PatternIgnoresThePort(Model):
    """A pattern matches its host on any port."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, _ = pattern
        shape = re.escape(scheme) + r"://(?:[a-z0-9\-]+\.)+" + re.escape(host) + r"(?::[0-9]+)?"
        return re.fullmatch(shape, origin) is not None


class PatternIgnoresTheScheme(Model):
    """A pattern matches its host under any scheme."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        _, host, port = pattern
        shape = r"[a-z]+://(?:[a-z0-9\-]+\.)+" + re.escape(host + port)
        return re.fullmatch(shape, origin) is not None


class PatternAllowsAnyCharacters(Model):
    """The labels in front may hold any characters, such as `_` or capitals."""

    def matches(self, pattern: tuple[str, str, str], origin: str) -> bool:
        scheme, host, port = pattern
        shape = re.escape(scheme) + r"://[^/:]+\." + re.escape(host + port)
        return re.fullmatch(shape, origin) is not None


class PatternNotNormalized(Model):
    """Patterns are kept as written."""

    def allow_pattern(self, pattern: str) -> bool:
        found = PATTERN.fullmatch(pattern)
        if found is None or found[1].lower() not in DEFAULTS:
            return False
        entry = (found[1], found[2], ":" + found[3] if found[3] else "")
        if entry in self.patterns:
            return False
        self.patterns.append(entry)
        return True


class PatternAcceptsATrailingSlash(Model):
    """`https://*.example.com/` is accepted."""

    def allow_pattern(self, pattern: str) -> bool:
        return super().allow_pattern(pattern.removesuffix("/"))


class NullReportedOnlyWithCredentials(Model):
    """`null` is reported only when credentials are allowed."""

    def null_finding(self) -> bool:
        return self.creds and super().null_finding()


class InsecureEvenWithoutCredentials(Model):
    """Plain `http` origins are reported whether or not credentials are allowed."""

    def lint(self) -> list[list[str]]:
        creds, self.creds = self.creds, True
        rows = super().lint()
        self.creds = creds
        return rows


class WsCountsAsSecure(Model):
    """`ws` is treated like `wss`."""

    def insecure(self, scheme: str) -> bool:
        return scheme not in ("https", "wss", "ws")


class TwoLabelsAreBroad(Model):
    """A host of two labels, such as `co.uk`, is reported as broad as well."""

    def broad(self, pattern: tuple[str, str, str]) -> bool:
        return pattern[1].count(".") <= 1


class FindingsInTheOrderFound(Model):
    """The findings are not sorted."""

    def order(self, rows: list[list[str]]) -> list[list[str]]:
        return rows


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_report_every_lint_code():
    codes = {
        row[0]
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "lint"
        for row in got
    }
    assert codes == {"broad-pattern", "credentials-to-insecure-origin", "null-origin-allowed"}
