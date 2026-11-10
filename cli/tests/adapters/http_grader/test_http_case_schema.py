"""The HTTP case in schemas/tests.schema.json, beside the shapes every problem already uses."""

import json
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.schema_validation import TESTS_SCHEMA_FILE, SchemaValidator
from tests.helpers import CATALOG_PROBLEMS, REPOSITORY_ROOT, SCHEMAS_DIRECTORY

SOURCE = "tests.json"
CONFORMANCE_PROBLEMS = REPOSITORY_ROOT / "runners" / "conformance"


@pytest.fixture(scope="module")
def validator() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / TESTS_SCHEMA_FILE)


def full_case() -> dict[str, Any]:
    return {
        "id": "h14",
        "level": 3,
        "note": "a 429 from the room vendor: wait for Retry-After, then retry once",
        "hang_guard_ms": 8000,
        "fresh": True,
        "mocks": {"room-vendor": "rate_limited_then_ok"},
        "before": [{"method": "POST", "path": "/seed", "json": {"rooms": 1}}],
        "request": {
            "method": "GET",
            "path": "/availability",
            "query": {"date": "2027-03-01", "room": ["oak", "elm"]},
            "headers": {"Accept": "application/json"},
        },
        "expected": {
            "status": 200,
            "body": [{"product": "desk_pass", "available": 12}],
            "headers": {"Content-Type": "application/json"},
        },
        "comparator": {"type": "float", "tolerance": 0.01},
        "log": [{"mock": "room-vendor", "route": "availability", "count": 2, "min_gap_ms": 950}],
    }


def violations(validator: SchemaValidator, case: dict[str, Any]) -> list[str]:
    document = {"version": 1, "cases": [case]}
    return [issue.location for issue in validator.violations(document, SOURCE)]


def with_fields(**fields: Any) -> dict[str, Any]:
    return full_case() | fields


def request_with(**fields: Any) -> dict[str, Any]:
    return {"method": "GET", "path": "/"} | fields


def without(field: str) -> dict[str, Any]:
    case = full_case()
    del case[field]
    return case


def test_a_case_with_every_field_is_valid(validator: SchemaValidator):
    assert violations(validator, full_case()) == []


def test_a_request_may_carry_a_raw_malformed_body(validator: SchemaValidator):
    request = {"method": "POST", "path": "/bookings", "body": '{"member": '}
    assert violations(validator, with_fields(request=request)) == []


def test_a_request_may_carry_json_null(validator: SchemaValidator):
    request = {"method": "POST", "path": "/bookings", "json": None}
    assert violations(validator, with_fields(request=request)) == []


def test_an_expected_body_may_be_null(validator: SchemaValidator):
    assert violations(validator, with_fields(expected={"status": 200, "body": None})) == []


def test_a_log_assertion_may_cover_a_whole_mock_server(validator: SchemaValidator):
    assert violations(validator, with_fields(log=[{"mock": "room-vendor", "count": 1}])) == []


BODY_ASSERTION = {
    "mock": "backup",
    "route": "chat",
    "count": 1,
    "body": {"stream": True},
    "body_max": {"max_tokens": 256},
    "body_same_as": {"mock": "primary", "route": "chat", "fields": ["messages"]},
}


def test_a_log_assertion_may_judge_a_logged_body(validator: SchemaValidator):
    assert violations(validator, with_fields(log=[BODY_ASSERTION])) == []


def test_prefix_stability_is_an_assertion_alone(validator: SchemaValidator):
    entry = {"mock": "llm", "body_prefix_stable": "messages"}
    assert violations(validator, with_fields(log=[entry])) == []


@pytest.mark.parametrize(
    ("label", "changes"),
    [
        ("a body subset that is a list", {"body": [1]}),
        ("a maximum that is no number", {"body_max": {"max_tokens": "256"}}),
        ("an empty maximum", {"body_max": {}}),
        ("a maximum on an empty path", {"body_max": {"a..b": 1}}),
        ("a reference with no fields", {"body_same_as": {"mock": "primary", "fields": []}}),
        ("a reference with no mock", {"body_same_as": {"fields": ["messages"]}}),
        (
            "a reference with an extra field",
            {"body_same_as": {"mock": "p", "fields": ["m"], "x": 1}},
        ),
        ("a prefix on an empty path", {"body_prefix_stable": ""}),
    ],
)
def test_a_body_assertion_is_refused_for(
    validator: SchemaValidator, label: str, changes: dict[str, Any]
):
    case = with_fields(log=[{**BODY_ASSERTION, **changes}])
    assert violations(validator, case) != [], label


@pytest.mark.parametrize(
    ("label", "case"),
    [
        ("no expected", without("expected")),
        ("no level", without("level")),
        ("no status", with_fields(expected={"body": []})),
        ("a status below 100", with_fields(expected={"status": 99})),
        ("an unknown expected field", with_fields(expected={"status": 200, "bodyy": []})),
        ("both json and body", with_fields(request=request_with(json=1, body=""))),
        ("a lowercase method", with_fields(request={"method": "get", "path": "/"})),
        ("a path without a slash", with_fields(request={"method": "GET", "path": "a"})),
        ("a query inside the path", with_fields(request={"method": "GET", "path": "/a?b=1"})),
        ("a space in the path", with_fields(request={"method": "GET", "path": "/a b"})),
        ("a path no request line can carry", with_fields(request={"method": "GET", "path": "/é"})),
        ("a tolerance on exact", with_fields(comparator={"type": "exact", "tolerance": 0.1})),
        ("a line break in a header", with_fields(request=request_with(headers={"A": "b\r\nc"}))),
        ("an input as well", with_fields(input={"a": 1})),
        ("ops as well", with_fields(ops=["A"], args=[[]])),
        ("the checker comparator", with_fields(comparator={"type": "checker"})),
        ("the ops comparator", with_fields(comparator={"type": "ops"})),
        ("a zero tolerance", with_fields(comparator={"type": "float", "tolerance": 0})),
        ("a log entry with no assertion", with_fields(log=[{"mock": "room-vendor"}])),
        ("a log entry with no mock", with_fields(log=[{"count": 1}])),
        ("a negative gap", with_fields(log=[{"mock": "m", "min_gap_ms": -1}])),
        ("a scenario that is not a name", with_fields(mocks={"room-vendor": None})),
    ],
)
def test_a_case_is_refused_for(validator: SchemaValidator, label: str, case: dict[str, Any]):
    assert violations(validator, case) != [], label


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mocks", {"room-vendor": "outage"}),
        ("before", [{"method": "POST", "path": "/seed"}]),
        ("comparator", {"type": "exact"}),
        ("log", [{"mock": "room-vendor", "count": 1}]),
        ("fresh", True),
    ],
)
def test_an_http_field_needs_a_request(validator: SchemaValidator, field: str, value: Any):
    case = {"id": "h1", "input": {"a": 1}, "expected": 1, field: value}
    assert violations(validator, case) != []


def test_a_case_of_today_stays_valid(validator: SchemaValidator):
    assert violations(validator, {"id": "h1", "input": {"a": 1}, "expected": 1}) == []


def every_tests_file() -> list[Path]:
    roots = (CATALOG_PROBLEMS, CONFORMANCE_PROBLEMS)
    return [path for root in roots for path in sorted(root.glob("*/tests.json"))]


def test_the_catalog_is_where_this_test_looks():
    assert len(every_tests_file()) > 100


def test_every_tests_json_of_the_catalog_stays_valid(validator: SchemaValidator):
    broken = {
        str(path): issues
        for path in every_tests_file()
        if (issues := validator.violations(json.loads(path.read_text()), str(path)))
    }
    assert broken == {}
