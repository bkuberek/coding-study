"""An HTTP case from its entry in a schema-valid tests.json
(docs/specs/service-projects.md#hidden-http-case).

A multi-step case's flows are written out here, once, as it is read: a `use` step becomes the
flow's steps, with each name its `with` gives filled in, so nothing after loading knows of flows.
"""

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from coding_study.domain.cases import Expected
from coding_study.domain.http_captures import CaptureSyntaxError, capture_source
from coding_study.domain.http_case import (
    DEFAULT_JAR,
    FormBody,
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    HttpStep,
    JsonBody,
    LogAssertion,
    OutputCheck,
    OutputPattern,
    QueryValue,
    RequestTemplate,
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
    return {
        key: _bound_value(value, bindings) if key in _BOUND_FIELDS else value
        for key, value in step.items()
    }


def _bound_value(value: object, bindings: Mapping[str, str]) -> object:
    if isinstance(value, str):
        return bound(value, bindings)
    if isinstance(value, list):
        return [_bound_value(item, bindings) for item in cast(list[object], value)]
    if isinstance(value, dict):
        members = cast(dict[str, object], value)
        return {key: _bound_value(item, bindings) for key, item in members.items()}
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
    body: str | None = request.get("body")
    return body.encode() if body is not None else None


def _expected(expected: Document) -> HttpExpected:
    return HttpExpected(
        status=expected["status"],
        body=Expected(expected["body"]) if "body" in expected else None,
        headers=dict(expected.get("headers", {})),
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
    )


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
