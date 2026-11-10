"""The cases of event-sourced-ledger-typescript expect balances and versions that the store's
history adds up to: the events the baseline migration seeds, and the hidden ones `grade_setup`
appends. These tests fold that history the way the statement defines a balance, check that each
case reading an account it did not change expects what the events say, and check that the history
is one a ledger could have written."""

import json
import re
from collections.abc import Mapping
from datetime import datetime
from itertools import accumulate
from typing import Any

import pytest

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0287-event-sourced-ledger-typescript"
STARTER_BASELINE = PROBLEM / "starter" / "migrations" / "0001_baseline.sql"
GRADING_BASELINE = PROBLEM / "grading" / "baseline" / "0001_baseline.sql"
SEED_ROW_START = "    ("
SEED_ROW = re.compile(
    r"^ {4}\('([^']+)', (\d+), '([^']+)', '([a-z_]+)', '(\{[^']*\})', '([^']+)'\)"
)
CREDITS = {"deposited", "transferred_in"}
HIDDEN_PREFIX = "x-"
ACCOUNT_PATH = re.compile(r"^/accounts/([^/]+)$")
EVENTS_PATH = re.compile(r"^/accounts/([^/]+)/events$")

type Event = Mapping[str, Any]
type Case = Mapping[str, Any]


def seed_rows() -> list[str]:
    lines = STARTER_BASELINE.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.startswith(SEED_ROW_START)]


def seed_events() -> list[Event]:
    events: list[Event] = []
    for row in seed_rows():
        found = SEED_ROW.match(row)
        if found is None:
            continue
        stream_id, version, event_id, kind, data, recorded_at = found.groups()
        events.append(
            {
                "stream_id": stream_id,
                "version": int(version),
                "event_id": event_id,
                "type": kind,
                "data": json.loads(data),
                "recorded_at": recorded_at,
            }
        )
    return events


SEED = seed_events()
HIDDEN: list[Event] = json.loads(
    (PROBLEM / "grading" / "hidden_events.json").read_text(encoding="utf-8")
)
HISTORY = SEED + HIDDEN
CASES: list[Case] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))["cases"]
STREAMS = sorted({event["stream_id"] for event in HISTORY})


def moment(text: str) -> datetime:
    return datetime.fromisoformat(text)


def stream(account: str) -> list[Event]:
    events = [event for event in HISTORY if event["stream_id"] == account]
    return sorted(events, key=lambda event: event["version"])


def signed_amount(event: Event) -> int:
    amount: int = event["data"]["amount"]
    return amount if event["type"] in CREDITS else -amount


def account_as_of(account: str, as_of: str | None) -> dict[str, Any] | None:
    """The account as the statement defines it, after its events recorded by `as_of`, or None
    before its first event."""
    events = [
        event
        for event in stream(account)
        if as_of is None or moment(event["recorded_at"]) <= moment(as_of)
    ]
    if not events:
        return None
    balance = sum(signed_amount(event) for event in events)
    return {"account": account, "balance": balance, "version": len(events)}


def stored_events(account: str) -> list[dict[str, Any]]:
    return [
        {"version": event["version"], "type": event["type"], "data": event["data"]}
        for event in stream(account)
    ]


def reads_only(case: Case) -> bool:
    return "request" in case and "before" not in case and case["request"]["method"] == "GET"


def untouched_reads(path: re.Pattern[str], status: int) -> list[Any]:
    """Each case that only reads a path of this shape, with nothing sent before it, and expects
    `status`, as a `pytest.param` of its account, its query and its expected body."""
    return [
        pytest.param(
            found.group(1),
            case["request"].get("query", {}),
            case["expected"].get("body"),
            id=case["id"],
        )
        for case in CASES
        if reads_only(case)
        and case["expected"]["status"] == status
        and (found := path.match(case["request"]["path"])) is not None
    ]


def legs(kind: str) -> list[Event]:
    return [event for event in HISTORY if event["type"] == kind]


def arrives_for(departure: Event, arrival: Event) -> bool:
    sent = {"amount": departure["data"]["amount"], "from": departure["stream_id"]}
    return (
        arrival["event_id"] == departure["event_id"]
        and arrival["stream_id"] == departure["data"]["to"]
        and arrival["data"] == sent
        and arrival["recorded_at"] == departure["recorded_at"]
    )


def test_the_grading_baseline_is_the_starters():
    assert GRADING_BASELINE.read_bytes() == STARTER_BASELINE.read_bytes()


def test_every_seeded_row_is_read():
    assert len(SEED) == len(seed_rows())


def test_hidden_events_hold_only_reserved_accounts():
    assert all(event["stream_id"].startswith(HIDDEN_PREFIX) for event in HIDDEN)


def test_seeded_events_hold_no_reserved_account():
    assert not any(event["stream_id"].startswith(HIDDEN_PREFIX) for event in SEED)


@pytest.mark.parametrize("account", STREAMS)
def test_a_stream_is_numbered_from_1_with_no_gap(account: str):
    versions = [event["version"] for event in stream(account)]
    assert versions == list(range(1, len(versions) + 1))


@pytest.mark.parametrize("account", STREAMS)
def test_a_stream_is_recorded_in_order(account: str):
    times = [moment(event["recorded_at"]) for event in stream(account)]
    assert times == sorted(times)


@pytest.mark.parametrize("account", STREAMS)
def test_a_stream_never_goes_below_zero(account: str):
    balances = accumulate(signed_amount(event) for event in stream(account))
    assert min(balances) >= 0


@pytest.mark.parametrize("account", STREAMS)
def test_an_event_id_is_used_once_in_a_stream(account: str):
    ids = [event["event_id"] for event in stream(account)]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    "departure",
    [pytest.param(event, id=event["event_id"]) for event in legs("transferred_out")],
)
def test_a_transfer_arrives_where_it_was_sent(departure: Event):
    assert any(arrives_for(departure, arrival) for arrival in legs("transferred_in"))


def test_every_arrival_has_a_departure():
    assert len(legs("transferred_in")) == len(legs("transferred_out"))


def test_some_cases_read_the_history_untouched():
    assert untouched_reads(ACCOUNT_PATH, 200)


@pytest.mark.parametrize(("account", "query", "body"), untouched_reads(ACCOUNT_PATH, 200))
def test_a_read_account_is_what_its_events_add_up_to(
    account: str, query: Mapping[str, str], body: Any
):
    assert body == account_as_of(account, query.get("as_of"))


@pytest.mark.parametrize(("account", "query", "body"), untouched_reads(ACCOUNT_PATH, 404))
def test_an_unknown_account_has_no_events_by_then(
    account: str, query: Mapping[str, str], body: Any
):
    assert account_as_of(account, query.get("as_of")) is None


@pytest.mark.parametrize(("account", "query", "body"), untouched_reads(EVENTS_PATH, 200))
def test_a_read_stream_is_the_stored_events(account: str, query: Mapping[str, str], body: Any):
    assert body == stored_events(account)
