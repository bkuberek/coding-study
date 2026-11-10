"""An HTTP case from its entry in a schema-valid tests.json
(docs/specs/service-projects.md#hidden-http-case).

A multi-step case's flows are written out here, once, as it is read: a `use` step becomes the
flow's steps, with each name its `with` gives filled in, so nothing after loading knows of flows.
A parallel case's burst is written out the same way, one request per index.
"""

import base64
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from coding_study.domain.cases import Expected
from coding_study.domain.http_captures import CaptureSyntaxError, capture_source
from coding_study.domain.http_case import (
    DEFAULT_JAR,
    BytesBody,
    ExpectedStatus,
    FormBody,
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    HttpStep,
    JsonBody,
    LogAssertion,
    OutputCheck,
    OutputPattern,
    ParallelBurst,
    QueryValue,
    RequestTemplate,
    SameBody,
    TemplateBody,
    TextBody,
)
from coding_study.domain.http_templates import bound
from coding_study.domain.problem import DEFAULT_FLOAT_TOLERANCE, ComparatorSpec, ComparatorType

type Document = Mapping[str, Any]
type Flows = Mapping[str, Sequence[Document]]

CONTENT_TYPE = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
_MOCKS_FIELD = "mocks"
_STEPS_FIELD = "steps"
_PARALLEL_FIELD = "parallel"
_BASE64_BODY_FIELD = "body_base64"
"""A binary body, which a JSON string cannot hold byte for byte."""
INDEX_PLACEHOLDER = "{i}"
"""Where each request of a parallel case's burst gets its index."""
_BOUND_FIELDS = ("request", "expected", "with")
"""The parts of a flow's step that its `with` fills in; captures name places, not values."""


class CaseDocumentError(ValueError):
    """A case that names what tests.json does not hold, such as a flow; the message names the
    step."""


def http_case_input(case: Document, flows: Flows | None = None) -> HttpCaseInput:
    """Raises CaseDocumentError for a step that uses a flow tests.json lacks, a flow that uses
    itself, or a capture that names no place in an answer."""
    if _STEPS_FIELD in case:
        return _steps_case(case, flows or {})
    if _PARALLEL_FIELD in case:
        return _parallel_case(case)
    request: Document = case["request"]
    mocks: Mapping[str, str] = case.get(_MOCKS_FIELD, {})
    return HttpCaseInput(
        arguments={**request, _MOCKS_FIELD: dict(mocks)} if mocks else dict(request),
        request=_request(request),
        expected=_expected(case["expected"]),
        mocks=dict(mocks),
        before=tuple(_request(before) for before in case.get("before", ())),
        comparator=_optional_comparator(case),
        log=tuple(_log_assertion(entry) for entry in case.get("log", ())),
        fresh=case.get("fresh", False),
        app_output=_output_check(case),
    )


def _steps_case(case: Document, flows: Flows) -> HttpCaseInput:
    mocks: Mapping[str, str] = case.get(_MOCKS_FIELD, {})
    steps: Sequence[Document] = case[_STEPS_FIELD]
    arguments: dict[str, Any] = {_STEPS_FIELD: list(steps)}
    if mocks:
        arguments[_MOCKS_FIELD] = dict(mocks)
    expander = _Expander(flows)
    return HttpCaseInput(
        arguments=arguments,
        mocks=dict(mocks),
        comparator=_optional_comparator(case),
        log=tuple(_log_assertion(entry) for entry in case.get("log", ())),
        fresh=case.get("fresh", False),
        steps=expander.steps(steps, _Place("step")),
        cleanup=expander.steps(case.get("cleanup", ()), _Place("cleanup")),
        app_output=_output_check(case),
    )


def _parallel_case(case: Document) -> HttpCaseInput:
    """Each request of the burst with its index, from 0, in place of each `{i}`; with several
    requests written, the burst takes them in turn."""
    parallel: Document = case[_PARALLEL_FIELD]
    mocks: Mapping[str, str] = case.get(_MOCKS_FIELD, {})
    arguments: dict[str, Any] = {_PARALLEL_FIELD: dict(parallel)}
    if mocks:
        arguments[_MOCKS_FIELD] = dict(mocks)
    templates: Sequence[Document] = (
        (parallel["request"],) if "request" in parallel else parallel["requests"]
    )
    statuses: Mapping[str, int] = case["expected_statuses"]
    burst = ParallelBurst(
        requests=tuple(
            _request(_indexed(templates[index % len(templates)], index))
            for index in range(parallel["count"])
        ),
        statuses={_status(written): count for written, count in statuses.items()},
        after=_after(case["after"]) if "after" in case else None,
        repeat=case.get("repeat", 1),
    )
    return HttpCaseInput(
        arguments=arguments,
        mocks=dict(mocks),
        before=tuple(_request(before) for before in case.get("before", ())),
        comparator=_optional_comparator(case),
        log=tuple(_log_assertion(entry) for entry in case.get("log", ())),
        fresh=case.get("fresh", False),
        app_output=_output_check(case),
        parallel=burst,
    )


def _indexed(request: Document, index: int) -> Document:
    def with_index(text: str) -> str:
        return text.replace(INDEX_PLACEHOLDER, str(index))

    return cast(Document, _with_texts(request, with_index))


def _status(written: str) -> ExpectedStatus:
    """`"201"` is a status; `"4xx"` stays a class."""
    return int(written) if written.isdigit() else written


def _after(after: Document) -> HttpStep:
    request = _request(after["request"])
    label = f"after {request.method} {request.target}"
    return HttpStep(label, request, _expected(after["expected"]))


@dataclass(frozen=True, slots=True)
class _Place:
    """Where a list of steps sits, for their labels: `step`, or `step 2, login step` inside the
    flow that step 2 uses."""

    prefix: str
    flows: tuple[str, ...] = ()
    """The flows being written out here, outermost first, so that a flow cannot use itself."""

    def label(self, number: int) -> str:
        return f"{self.prefix} {number}"

    def into(self, number: int, flow: str) -> "_Place":
        return _Place(f"{self.label(number)}, {flow} step", (*self.flows, flow))


@dataclass(frozen=True, slots=True)
class _Expander:
    flows: Flows

    def steps(self, documents: Sequence[Document], place: _Place) -> tuple[HttpStep, ...]:
        return tuple(self._expanded(documents, place))

    def _expanded(self, documents: Sequence[Document], place: _Place) -> Iterator[HttpStep]:
        for number, document in enumerate(documents, start=1):
            if "use" in document:
                yield from self._used(document, place, number)
            else:
                yield _step(document, place.label(number))

    def _used(self, document: Document, place: _Place, number: int) -> Iterator[HttpStep]:
        name: str = document["use"]
        if name not in self.flows:
            raise CaseDocumentError(f"{place.label(number)}: no flow named {name}")
        if name in place.flows:
            raise CaseDocumentError(f"{place.label(number)}: the flow {name} uses itself")
        bindings: Mapping[str, str] = document.get("with", {})
        written = [_bound_step(step, bindings) for step in self.flows[name]]
        yield from self._expanded(written, place.into(number, name))


def _bound_step(step: Document, bindings: Mapping[str, str]) -> Document:
    if not bindings:
        return step

    def bound_text(text: str) -> str:
        return bound(text, bindings)

    return {
        key: _with_texts(value, bound_text) if key in _BOUND_FIELDS else value
        for key, value in step.items()
    }


def _with_texts(value: object, change: Callable[[str], str]) -> object:
    """`value` with each string in it, at any depth, changed."""
    if isinstance(value, str):
        return change(value)
    if isinstance(value, list):
        return [_with_texts(item, change) for item in cast(list[object], value)]
    if isinstance(value, dict):
        members = cast(dict[str, object], value)
        return {key: _with_texts(item, change) for key, item in members.items()}
    return value


def _step(step: Document, label: str) -> HttpStep:
    request: Document = step["request"]
    template = RequestTemplate(
        method=request["method"],
        target=request.get("url") or request["path"],
        query=_query(request.get("query", {})),
        headers=dict(request.get("headers", {})),
        body=_template_body(request),
        jar=request.get("jar", DEFAULT_JAR),
        follow_redirects=request.get("follow_redirects", False),
    )
    named = f"{label} {template.method} {template.target}"
    expected = _expected(step["expected"]) if "expected" in step else None
    try:
        captures = {name: capture_source(text) for name, text in step.get("capture", {}).items()}
    except CaptureSyntaxError as error:
        raise CaseDocumentError(f"{label}: capture {error}") from None
    return HttpStep(named, template, expected, captures)


def _template_body(request: Document) -> TemplateBody | None:
    if "json" in request:
        return JsonBody(request["json"])
    if "form" in request:
        return FormBody(dict(request["form"]))
    if "body" in request:
        return TextBody(request["body"])
    if _BASE64_BODY_FIELD in request:
        return BytesBody(_decoded(request))
    return None


def _request(request: Document) -> HttpRequest:
    headers: dict[str, str] = dict(request.get("headers", {}))
    return HttpRequest(
        method=request["method"],
        path=request["path"],
        query=_query(request.get("query", {})),
        headers=_with_json_type(headers) if "json" in request else headers,
        body=_body(request),
    )


def _query(query: Document) -> dict[str, QueryValue]:
    return {
        name: value if isinstance(value, str) else tuple(value) for name, value in query.items()
    }


def _with_json_type(headers: dict[str, str]) -> dict[str, str]:
    if any(name.lower() == CONTENT_TYPE.lower() for name in headers):
        return headers
    return {**headers, CONTENT_TYPE: JSON_CONTENT_TYPE}


def _body(request: Document) -> bytes | None:
    if "json" in request:
        return json.dumps(request["json"]).encode()
    if _BASE64_BODY_FIELD in request:
        return _decoded(request)
    body: str | None = request.get("body")
    return body.encode() if body is not None else None


def _decoded(request: Document) -> bytes:
    """The schema holds `body_base64` to the standard alphabet, padded."""
    return base64.b64decode(request[_BASE64_BODY_FIELD], validate=True)


def _expected(expected: Document) -> HttpExpected:
    return HttpExpected(
        status=expected["status"],
        body=Expected(expected["body"]) if "body" in expected else None,
        headers=dict(expected.get("headers", {})),
        first_byte_ms_max=expected.get("first_byte_ms_max"),
    )


def _optional_comparator(case: Document) -> ComparatorSpec | None:
    comparator: Document | None = case.get("comparator")
    if comparator is None:
        return None
    return ComparatorSpec(
        type=ComparatorType(comparator["type"]),
        tolerance=comparator.get("tolerance", DEFAULT_FLOAT_TOLERANCE),
    )


def _log_assertion(entry: Document) -> LogAssertion:
    return LogAssertion(
        mock=entry["mock"],
        route=entry.get("route"),
        count=entry.get("count"),
        min_count=entry.get("min_count"),
        max_count=entry.get("max_count"),
        min_gap_ms=entry.get("min_gap_ms"),
        headers=dict(entry.get("headers", {})),
        form=dict(entry.get("form", {})),
        body=entry.get("body"),
        body_max=dict(entry.get("body_max", {})),
        body_same_as=_same_body(entry.get("body_same_as")),
        body_prefix_stable=entry.get("body_prefix_stable"),
    )


def _same_body(reference: Document | None) -> SameBody | None:
    if reference is None:
        return None
    return SameBody(reference["mock"], reference.get("route"), tuple(reference["fields"]))


def _output_check(case: Document) -> OutputCheck | None:
    check: Document | None = case.get("app_output")
    if check is None:
        return None
    return OutputCheck(
        tuple(
            text if isinstance(text, str) else OutputPattern(text["regex"])
            for text in check["absent"]
        )
    )
