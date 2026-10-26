"""Loads the runner conformance suite from runners/conformance/ (docs/specs/runners.md).

`cstudy verify --conformance` reads the fixtures through `conformance_repository` and judges each
language's runs against `load_conformance_suite`.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.schema_validation import SCHEMAS_DIRECTORY, SchemaValidator
from coding_study.domain.conformance import (
    ConformanceExpectation,
    ConformanceSuite,
    ExpectedOutcome,
    ExpectedStatus,
)
from coding_study.domain.errors import ContentError, ContentIssue

CONFORMANCE_DIRECTORY = "runners/conformance"
EXPECTATIONS_FILE = "expectations.json"
CONFORMANCE_SCHEMA_FILE = "conformance.schema.json"


def conformance_repository(root: Path) -> FsProblemRepository:
    return FsProblemRepository(root, CONFORMANCE_DIRECTORY)


def load_conformance_suite(root: Path) -> ConformanceSuite:
    """Raises ContentError when expectations.json is missing, malformed or off-schema."""
    source = f"{CONFORMANCE_DIRECTORY}/{EXPECTATIONS_FILE}"
    document = _parse(root / source, source)
    validator = SchemaValidator.from_file(root / SCHEMAS_DIRECTORY / CONFORMANCE_SCHEMA_FILE)
    issues = validator.violations(document, source)
    if issues:
        raise ContentError(issues)
    expectations = tuple(_expectation(entry) for entry in document["expectations"])
    return ConformanceSuite(CONFORMANCE_DIRECTORY, expectations)


def _parse(path: Path, source: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ContentError([ContentIssue(source, "", "file not found")]) from None
    except json.JSONDecodeError as error:
        location = f"line {error.lineno}, column {error.colno}"
        raise ContentError([ContentIssue(source, location, error.msg)]) from None


def _expectation(entry: Mapping[str, Any]) -> ConformanceExpectation:
    overrides = entry.get("cases", {})
    return ConformanceExpectation(
        slug=entry["problem"],
        approach_id=entry["approach"],
        outcome=_outcome(entry["outcome"]),
        case_outcomes={case_id: _outcome(outcome) for case_id, outcome in overrides.items()},
    )


def _outcome(outcome: Mapping[str, Any]) -> ExpectedOutcome:
    partial_output = outcome.get("partial_output")
    return ExpectedOutcome(
        status=ExpectedStatus(outcome["status"]),
        message=outcome.get("message"),
        op_index=outcome.get("op_index"),
        partial_output=tuple(partial_output) if partial_output is not None else None,
        stdout=outcome.get("stdout"),
        runs=outcome.get("runs"),
        min_failed=outcome.get("min_failed"),
        max_failed=outcome.get("max_failed"),
        phase=outcome.get("phase"),
        deterministic=outcome.get("deterministic", False),
        restart_requested=outcome.get("restart_requested", False),
    )
