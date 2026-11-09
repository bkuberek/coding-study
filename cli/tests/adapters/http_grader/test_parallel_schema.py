"""Parallel cases in schemas/tests.schema.json (docs/specs/service-projects.md#parallel-cases)."""

from typing import Any

import pytest

from coding_study.adapters.schema_validation import TESTS_SCHEMA_FILE, SchemaValidator
from tests.helpers import SCHEMAS_DIRECTORY

SOURCE = "tests.json"
RESERVE = {"method": "POST", "path": "/reservations", "json": {"order": "o{i}"}}


@pytest.fixture(scope="module")
def validator() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / TESTS_SCHEMA_FILE)


def full_case() -> dict[str, Any]:
    return {
        "id": "h21",
        "level": 2,
        "fresh": True,
        "repeat": 3,
        "note": "10 checkouts for the last 3 lamps",
        "before": [{"method": "POST", "path": "/seed"}],
        "parallel": {"count": 10, "request": RESERVE},
        "expected_statuses": {"201": 3, "4xx": 7},
        "after": {
            "request": {"method": "GET", "path": "/products/lamp"},
            "expected": {"status": 200, "body": {"sku": "lamp", "available": 0}},
        },
    }


def violations(validator: SchemaValidator, case: dict[str, Any]) -> list[str]:
    document = {"version": 1, "cases": [case]}
    return [issue.location for issue in validator.violations(document, SOURCE)]


def with_fields(**fields: Any) -> dict[str, Any]:
    return full_case() | fields


def without(field: str) -> dict[str, Any]:
    case = full_case()
    del case[field]
    return case


def test_a_parallel_case_with_every_field_is_valid(validator: SchemaValidator):
    assert violations(validator, full_case()) == []


def test_the_smallest_parallel_case_is_valid(validator: SchemaValidator):
    case = {
        "id": "h1",
        "level": 1,
        "parallel": {"count": 2, "request": RESERVE},
        "expected_statuses": {"201": 2},
    }
    assert violations(validator, case) == []


@pytest.mark.parametrize(
    ("label", "case"),
    [
        ("no expected statuses", without("expected_statuses")),
        ("no level", without("level")),
        ("an expected answer too", with_fields(expected={"status": 201})),
        ("a request too", with_fields(request=RESERVE)),
        ("steps too", with_fields(steps=[{"request": RESERVE}])),
        ("one request", with_fields(parallel={"count": 1, "request": RESERVE})),
        ("more than 64 requests", with_fields(parallel={"count": 65, "request": RESERVE})),
        ("no count", with_fields(parallel={"request": RESERVE})),
        ("no request", with_fields(parallel={"count": 2})),
        (
            "an origin's url",
            with_fields(
                parallel={"count": 2, "request": {"method": "GET", "url": "http://idp:8080/"}}
            ),
        ),
        ("a status that is no status", with_fields(expected_statuses={"2000": 1})),
        ("a count of no answers", with_fields(expected_statuses={"201": 0})),
        ("no run", with_fields(repeat=0)),
        ("more than 10 runs", with_fields(repeat=11)),
        ("an after with no expected", with_fields(after={"request": RESERVE})),
    ],
)
def test_a_parallel_case_is_refused_for(
    validator: SchemaValidator, label: str, case: dict[str, Any]
):
    assert violations(validator, case) != [], label


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expected_statuses", {"201": 1}),
        ("after", full_case()["after"]),
        ("repeat", 2),
    ],
)
def test_a_parallel_field_needs_a_parallel_burst(
    validator: SchemaValidator, field: str, value: Any
):
    case = {
        "id": "h1",
        "level": 1,
        "request": RESERVE,
        "expected": {"status": 201},
        field: value,
    }
    assert violations(validator, case) != []
