"""An HTTP case from its entry in a schema-valid tests.json
(docs/specs/service-projects.md#hidden-http-case)."""

import json
from collections.abc import Mapping
from typing import Any

from coding_study.domain.cases import Expected
from coding_study.domain.http_case import (
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    LogAssertion,
    QueryValue,
)
from coding_study.domain.problem import DEFAULT_FLOAT_TOLERANCE, ComparatorSpec, ComparatorType

type Document = Mapping[str, Any]

CONTENT_TYPE = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
_MOCKS_FIELD = "mocks"


def http_case_input(case: Document) -> HttpCaseInput:
    request: Document = case["request"]
    mocks: Mapping[str, str] = case.get(_MOCKS_FIELD, {})
    comparator: Document | None = case.get("comparator")
    return HttpCaseInput(
        arguments={**request, _MOCKS_FIELD: dict(mocks)} if mocks else dict(request),
        request=_request(request),
        expected=_expected(case["expected"]),
        mocks=dict(mocks),
        before=tuple(_request(before) for before in case.get("before", ())),
        comparator=_comparator(comparator) if comparator is not None else None,
        log=tuple(_log_assertion(entry) for entry in case.get("log", ())),
        fresh=case.get("fresh", False),
    )


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


def _comparator(comparator: Document) -> ComparatorSpec:
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
    )
