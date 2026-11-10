"""price-cache-rate-limits-typescript has no clock its cases can move, so a case that needs a price
to expire asks for the anvil in between, which the engine takes longer than that price's lifetime
to answer and never lets the app keep. These tests keep those lifetimes, the anvil's delay and the
cases in step, and the store free of anything it would write to its read-only disk."""

import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0285-price-cache-rate-limits-typescript"
ENGINE: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "mocks" / "pricing.yaml").read_text(encoding="utf-8")
)
COMPOSE: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "services" / "compose.yaml").read_text(encoding="utf-8")
)
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
ROUTES = {route["id"]: route for route in ENGINE["routes"]}
WAIT_PATH = ROUTES["anvil"]["path"].replace("/v1", "")
API_KEY = re.compile(r"[A-Za-z0-9_-]{1,64}")
EXPIRES_AFTER_ONE_WAIT = ("kettle",)
EXPIRES_AFTER_TWO_WAITS = ("fan",)


def lifetime_ms(route_id: str) -> int:
    """How long the engine lets the app keep a route's price, stale time included."""
    header = ROUTES[route_id]["response"]["headers"]["Cache-Control"]
    seconds = re.findall(r"(?:max-age|stale-while-revalidate)=(\d+)", header)
    return 1000 * sum(int(found) for found in seconds)


def requests_of(case: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield from case.get("before", [])
    if "request" in case:
        yield case["request"]
    for step in case.get("steps", []):
        yield step["request"]
    if "parallel" in case:
        parallel = case["parallel"]
        yield from parallel.get("requests", [parallel.get("request")])
    if "after" in case:
        yield case["after"]["request"]


def keyed_requests() -> Iterator[tuple[str, str]]:
    """Each API key a case sends, with the case's id."""
    for case in TESTS["cases"]:
        for request in requests_of(case):
            key = request.get("headers", {}).get("X-Api-Key")
            if key is not None:
                yield case["id"], key.replace("{i}", "0")


def test_the_anvil_is_never_kept_so_each_wait_reaches_the_engine():
    assert ROUTES["anvil"]["response"]["headers"]["Cache-Control"] == "no-store"


@pytest.mark.parametrize("route_id", EXPIRES_AFTER_ONE_WAIT)
def test_one_wait_outlasts_a_price_a_case_expires_with_one(route_id: str):
    assert ROUTES["anvil"]["response"]["delay_ms"] > lifetime_ms(route_id)


@pytest.mark.parametrize("route_id", EXPIRES_AFTER_TWO_WAITS)
def test_two_waits_outlast_a_price_a_case_expires_with_two(route_id: str):
    assert 2 * ROUTES["anvil"]["response"]["delay_ms"] > lifetime_ms(route_id)


def test_every_case_that_waits_for_the_anvil_has_the_longer_hang_guard():
    waiting = [
        case["id"]
        for case in TESTS["cases"]
        if any(request["path"] == WAIT_PATH for request in requests_of(case))
    ]

    assert [case["id"] for case in TESTS["cases"] if "hang_guard_ms" in case] == waiting


@pytest.mark.parametrize(("case_id", "key"), sorted(set(keyed_requests())))
def test_a_key_the_rule_refuses_is_sent_only_by_a_case_that_expects_401(case_id: str, key: str):
    case = next(found for found in TESTS["cases"] if found["id"] == case_id)

    assert API_KEY.fullmatch(key) or case["expected"]["status"] == 401


@pytest.mark.parametrize(("flag", "off"), [("--save", ""), ("--appendonly", "no")])
def test_the_store_writes_nothing_to_its_read_only_disk(flag: str, off: str):
    command = COMPOSE["services"]["store"]["command"]

    assert command[command.index(flag) + 1] == off
