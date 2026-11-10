"""The cases of postgres-job-queue-typescript name exact times, computed by hand when it was written
from the frozen clock in its meta.yaml and the statement's rules: a claim runs out after its
visibility, and a failed attempt waits its backoff, doubled per attempt and capped at an hour.
These tests replay each case's requests and keep every such time in step with those rules."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0283-postgres-job-queue-typescript"
DEFAULT_VISIBILITY_S = 30
DEFAULT_BACKOFF_S = 30
MAX_BACKOFF_S = 3600

type Request = Mapping[str, Any]
type Exchange = tuple[str, Request, Mapping[str, Any] | None]

ENV: Mapping[str, str] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]["env"]
NOW = datetime.fromtimestamp(int(ENV["CLOCK_NOW"]), UTC)
CASES: list[Mapping[str, Any]] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))[
    "cases"
]


def at(seconds: int) -> str:
    """The frozen clock plus some seconds, written as the answers write a time."""
    return (NOW + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def exchanges(case: Mapping[str, Any]) -> list[Exchange]:
    """Each request a case sends, in order and named for where it is, with the answer it expects;
    None for a `before`, which only has to succeed."""
    found: list[Exchange] = [
        (f"{case['id']} before {index + 1}", request, None)
        for index, request in enumerate(case.get("before", ()))
    ]
    if "request" in case:
        found.append((case["id"], case["request"], case["expected"]))
    found += [
        (f"{case['id']} step {index + 1}", step["request"], step.get("expected"))
        for index, step in enumerate(case.get("steps", ()))
    ]
    if "after" in case:
        found.append((f"{case['id']} after", case["after"]["request"], case["after"]["expected"]))
    return found


def timed_field(request: Request) -> str | None:
    """The field of the answer to which the rules give a time: when a claim runs out, when a new
    job may run, or when a failed one may run again."""
    if request["method"] != "POST":
        return None
    if request["path"].endswith("/claim"):
        return "expires_at"
    if request["path"].endswith(("/jobs", "/fail")):
        return "run_after"
    return None


def backoff_s(request: Request, backoffs: Mapping[str, int]) -> int:
    """How long a failed attempt waits before the cap: its job's backoff, doubled per attempt."""
    job = request["path"].split("/")[2]
    return backoffs[job] * 2 ** (request["json"]["attempt"] - 1)


def ruled_time(request: Request, backoffs: Mapping[str, int]) -> str:
    """The time the rules give the answer to this request, which `timed_field` names."""
    if request["path"].endswith("/claim"):
        return at(request["json"].get("visibility_seconds", DEFAULT_VISIBILITY_S))
    if request["path"].endswith("/fail"):
        return at(min(backoff_s(request, backoffs), MAX_BACKOFF_S))
    return at(0)


def timed_answers() -> list[tuple[str, Request, str, str]]:
    """Each answer that expects a time: where it is, its request, the time it expects, and the
    time the rules give it."""
    found: list[tuple[str, Request, str, str]] = []
    for case in CASES:
        backoffs: dict[str, int] = {}
        for name, request, expected in exchanges(case):
            body = request.get("json")
            if request["path"].endswith("/jobs") and isinstance(body, dict) and "id" in body:
                backoffs[body["id"]] = body.get("backoff_seconds", DEFAULT_BACKOFF_S)
            answer = (expected or {}).get("body")
            field = timed_field(request)
            if isinstance(answer, dict) and field in answer and answer[field] is not None:
                found.append((name, request, answer[field], ruled_time(request, backoffs)))
    return found


TIMED = timed_answers()


def test_some_case_expects_a_backoff_cut_to_its_cap():
    capped = [
        name
        for name, request, expected, _ruled in TIMED
        if request["path"].endswith("/fail") and expected == at(MAX_BACKOFF_S)
    ]
    assert capped != []


@pytest.mark.parametrize(
    ("expected", "ruled"),
    [pytest.param(expected, ruled, id=name) for name, _request, expected, ruled in TIMED],
)
def test_a_time_a_case_expects_follows_from_the_clock_and_the_rules(expected: str, ruled: str):
    assert expected == ruled
