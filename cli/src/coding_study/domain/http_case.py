"""The hidden and visible HTTP cases of a service project
(docs/specs/service-projects.md#hidden-http-case). Language-neutral: a case names a request and
what must come back, and nothing about the app that answers.

A case is one request, with the requests `before` it, or an ordered list of steps
(docs/specs/service-projects.md#multi-step-cases), which can carry values from one answer into a
later request and keep cookies, as a browser would, or a burst of requests sent at once
(docs/specs/service-projects.md#parallel-cases), judged by how many answered each status.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlencode

from coding_study.domain.cases import Expected, FunctionInput, JsonValue
from coding_study.domain.problem import ComparatorSpec

type QueryValue = str | tuple[str, ...]
type ExpectedStatus = int | str
"""A status, or a class of them written as `"4xx"`."""

DEFAULT_JAR = "main"
"""The cookie jar of a step that names none."""
SUCCESS = "2xx"


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    path: str
    """The path, with the query an absolute URL carries as it was written."""
    query: Mapping[str, QueryValue] = field(default_factory=dict[str, QueryValue])
    """A key with several values is sent once per value."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    body: bytes | None = None
    """Exactly what goes out, so a case can send a malformed body."""
    origin: str | None = None
    """`http://<name>:<port>`, an origin as the stack's network names it; None is the app at the
    address the stack publishes, as every single-request case sends."""
    jar: str | None = None
    """The cookie jar that sends and keeps this request's cookies; None keeps none."""
    follow_redirects: bool = False

    @property
    def target(self) -> str:
        """The path and query, as a request line names them."""
        if not self.query:
            return self.path
        joiner = "&" if "?" in self.path else "?"
        return f"{self.path}{joiner}{urlencode(self.query, doseq=True)}"


@dataclass(frozen=True, slots=True)
class HttpExpected:
    status: ExpectedStatus
    body: Expected | None = None
    """None accepts any body; `Expected(None)` asks for a JSON null."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    """Each listed header must match."""
    first_byte_ms_max: int | None = None
    """The most milliseconds from sending the request to the first byte of its body; None allows
    any (docs/specs/service-projects.md#hidden-http-case)."""


@dataclass(frozen=True, slots=True)
class SameBody:
    """The first request a mock server logged on a route, whose JSON body fields another request's
    must equal (docs/specs/service-projects.md#logged-bodies)."""

    mock: str
    route: str | None
    """None is the mock server's first request, whatever its route."""
    fields: tuple[str, ...]
    """Dotted paths, such as `messages`."""


@dataclass(frozen=True, slots=True)
class LogAssertion:
    """What the request log of a mock server must show when the case's answer is in."""

    mock: str
    route: str | None = None
    """None covers every request the mock server logged, matched or not."""
    count: int | None = None
    min_count: int | None = None
    max_count: int | None = None
    min_gap_ms: int | None = None
    """From each response to the next request (docs/specs/service-projects.md#hidden-http-case)."""
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    """Only requests that carried each of these headers count; values may name `{{captures}}`."""
    form: Mapping[str, str] = field(default_factory=dict[str, str])
    """Only requests whose form-encoded body held each of these fields count."""
    body: Mapping[str, JsonValue] | None = None
    """Only requests whose JSON body held this subset count; its strings may name `{{captures}}`."""
    body_max: Mapping[str, float] = field(default_factory=dict[str, float])
    """Only requests whose JSON body had a number at most this at each dotted path count."""
    body_same_as: SameBody | None = None
    """Only requests whose JSON body fields equal those of another logged request count."""
    body_prefix_stable: str | None = None
    """A dotted path: each request that counts, in order, holds there a text or list that starts
    with the previous one's whole value."""


@dataclass(frozen=True, slots=True)
class JsonBody:
    value: JsonValue
    """Its strings may name `{{captures}}`."""


@dataclass(frozen=True, slots=True)
class FormBody:
    fields: Mapping[str, str]
    """Sent as `application/x-www-form-urlencoded`; values may name `{{captures}}`."""


@dataclass(frozen=True, slots=True)
class TextBody:
    text: str


@dataclass(frozen=True, slots=True)
class BytesBody:
    """Sent byte for byte, as `body_base64` wrote it; it names no `{{captures}}`."""

    data: bytes


type TemplateBody = JsonBody | FormBody | TextBody | BytesBody


@dataclass(frozen=True, slots=True)
class RequestTemplate:
    """A step's request as tests.json writes it. Its texts may name values by `{{name}}`, which
    are filled in when the step runs."""

    method: str
    target: str
    """A path, which goes to the app, or an absolute URL, `http://idp:8080/...`."""
    query: Mapping[str, QueryValue] = field(default_factory=dict[str, QueryValue])
    headers: Mapping[str, str] = field(default_factory=dict[str, str])
    body: TemplateBody | None = None
    jar: str = DEFAULT_JAR
    follow_redirects: bool = False


class CaptureKind(StrEnum):
    STATUS = "status"
    HEADER = "header"
    BODY = "body"
    FORM = "form"
    """An attribute of the HTML `<form>` with this `id`."""
    INPUT = "input"
    """An attribute of the HTML `<input>` with this `name`."""


@dataclass(frozen=True, slots=True)
class CaptureSource:
    """Where a value comes from in an answer, as `header.location.query.code` says."""

    kind: CaptureKind
    path: tuple[str, ...] = ()
    """What follows the kind: a header's name, then `query` and a parameter; a body's dotted path;
    a form's id or an input's name, then an attribute."""

    @property
    def written(self) -> str:
        return ".".join((self.kind, *self.path))


@dataclass(frozen=True, slots=True)
class HttpStep:
    label: str
    """How a reason names the step: `step 2`, or `step 1, login step 3` inside a flow; empty for
    the request of a single-request case, which needs no name."""
    request: HttpRequest | RequestTemplate
    """A template for a step of a multi-step case; a request, sent as it is, for a single-request
    case, whose texts never name a capture."""
    expected: HttpExpected | None = None
    """None accepts any answer. A template step's expected texts may name `{{captures}}` too."""
    captures: Mapping[str, CaptureSource] = field(default_factory=dict[str, CaptureSource])


@dataclass(frozen=True, slots=True)
class OutputPattern:
    regex: str
    """Python's regular expression syntax, searched for anywhere in the output."""


type AbsentOutput = str | OutputPattern
"""A text, which may name a `{{capture}}`, or a pattern."""


@dataclass(frozen=True, slots=True)
class ParallelBurst:
    """Requests sent at once against limited capacity
    (docs/specs/service-projects.md#parallel-cases)."""

    requests: tuple[HttpRequest, ...]
    """Each with its index, from 0, filled in where the case wrote `{i}`."""
    statuses: Mapping[ExpectedStatus, int]
    """How many answers must come back with each status, or class of them. The verdict counts
    statuses, never their order."""
    after: HttpStep | None = None
    """Sent once every answer is in, to judge the state the burst left."""
    repeat: int = 1
    """How many times the whole case runs, each time from a reset."""


@dataclass(frozen=True, slots=True)
class OutputCheck:
    """What the app may not print, on standard output or error, while a case runs."""

    absent: tuple[AbsentOutput, ...]


@dataclass(frozen=True, slots=True)
class HttpCaseInput(FunctionInput):
    """What an HTTP case does. It is a `FunctionInput` whose `arguments` hold the request, or the
    steps, as tests.json wrote them, with the scenarios it set, so that every report and event that
    shows a case's input shows this one with no code of its own."""

    request: HttpRequest | None = None
    """The request of a single-request case; None for a multi-step one."""
    expected: HttpExpected | None = None
    mocks: Mapping[str, str] = field(default_factory=dict[str, str])
    """The scenario per mock server; one left out has none."""
    before: tuple[HttpRequest, ...] = ()
    """Sent first, for a case that needs state; each must answer 2xx."""
    comparator: ComparatorSpec | None = None
    """None uses the problem's."""
    log: tuple[LogAssertion, ...] = ()
    fresh: bool = False
    """Restart the app and reset its data first."""
    steps: tuple[HttpStep, ...] = ()
    """A multi-step case's steps, with every flow it uses written out."""
    cleanup: tuple[HttpStep, ...] = ()
    """Steps that run after the case whatever happened, to undo what it changed."""
    app_output: OutputCheck | None = None
    parallel: ParallelBurst | None = None
    """A parallel case's burst, sent after its `before` requests."""

    @property
    def runs(self) -> int:
        """How many times the case runs: a parallel case may repeat."""
        return self.parallel.repeat if self.parallel is not None else 1

    def exchange_steps(self) -> tuple[HttpStep, ...]:
        """Every step the case sends, in order: a single-request case's `before` requests, each of
        which must answer 2xx, then its request."""
        if self.steps or self.request is None:
            return self.steps
        return (*self.before_steps(), HttpStep("", self.request, self.expected))

    def before_steps(self) -> tuple[HttpStep, ...]:
        """The `before` requests, each of which must answer 2xx."""
        return tuple(
            HttpStep(f"before[{index}] {request.method} {request.target}", request, BEFORE_EXPECTED)
            for index, request in enumerate(self.before)
        )


BEFORE_EXPECTED = HttpExpected(SUCCESS)
