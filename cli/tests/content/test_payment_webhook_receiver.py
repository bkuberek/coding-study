"""The cases of payment-webhook-receiver-typescript carry signatures and timestamps computed when it
was written, against the secret and frozen clock in its meta.yaml, and the provider's events API
lists copies of the events the cases deliver. These tests keep all three in step, so a case refuses
a delivery only for the reason its expected answer names."""

import hashlib
import hmac
import json
from collections.abc import Callable, Mapping
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0279-payment-webhook-receiver-typescript"
TOLERANCE_S = 300
TIMESTAMP = "Provider-Timestamp"
SIGNATURE = "Provider-Signature"
BAD_SIGNATURE = {"error": "invalid signature"}
BAD_TIMESTAMP = {"error": "timestamp outside tolerance"}

type Request = Mapping[str, Any]

ENV: Mapping[str, str] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]["env"]
SECRET = ENV["WEBHOOK_SECRET"].encode()
NOW = int(ENV["CLOCK_NOW"])
CASES: list[Mapping[str, Any]] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))[
    "cases"
]


def is_delivery(request: Request) -> bool:
    return request["method"] == "POST" and request["path"] == "/webhooks/payments"


def is_signed(request: Request) -> bool:
    headers = request["headers"]
    if TIMESTAMP not in headers or SIGNATURE not in headers:
        return False
    signed = f"{headers[TIMESTAMP]}.{request['body']}".encode()
    expected = hmac.new(SECRET, signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, headers[SIGNATURE])


def is_timely(request: Request) -> bool:
    timestamp = request["headers"][TIMESTAMP]
    return timestamp.isdigit() and abs(NOW - int(timestamp)) <= TOLERANCE_S


def deliveries() -> list[tuple[str, Request, Mapping[str, Any] | None]]:
    """Each delivery a case sends, with the answer its case expects of it; None for a `before`,
    which must be accepted."""
    found: list[tuple[str, Request, Mapping[str, Any] | None]] = []
    for case in CASES:
        found += [
            (f"{case['id']} before {index + 1}", before, None)
            for index, before in enumerate(case.get("before", ()))
            if is_delivery(before)
        ]
        if is_delivery(case["request"]):
            found.append((case["id"], case["request"], case["expected"].get("body")))
    return found


def named_requests(is_wanted: Callable[[object], bool]) -> list[object]:
    """The `pytest.param` of each delivery whose expected answer is wanted, named for its case."""
    return [pytest.param(request, id=name) for name, request, body in DELIVERIES if is_wanted(body)]


DELIVERIES = deliveries()
SIGNED = [request for _name, request, body in DELIVERIES if body != BAD_SIGNATURE]


def listed_events() -> list[tuple[str, Mapping[str, Any]]]:
    """Each event the provider's events API lists, by the file that lists it."""
    return [
        (path.name, event)
        for path in sorted((PROBLEM / "mocks" / "bodies").glob("*.json"))
        for event in json.loads(path.read_text(encoding="utf-8"))["events"]
    ]


def delivered_events() -> dict[str, Mapping[str, Any]]:
    """Each event a signed delivery carries, by id."""
    events: dict[str, Mapping[str, Any]] = {}
    for request in SIGNED:
        try:
            event = json.loads(request["body"])
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and "id" in event:
            events.setdefault(event["id"], event)
    return events


DELIVERED = delivered_events()


def test_the_cases_refuse_deliveries_for_each_reason():
    refused = {json.dumps(body) for _name, _request, body in DELIVERIES}
    assert {json.dumps(BAD_SIGNATURE), json.dumps(BAD_TIMESTAMP)} <= refused


@pytest.mark.parametrize("request_", named_requests(lambda body: body == BAD_SIGNATURE))
def test_a_delivery_refused_for_its_signature_is_not_signed(request_: Request):
    assert not is_signed(request_)


@pytest.mark.parametrize("request_", named_requests(lambda body: body != BAD_SIGNATURE))
def test_every_other_delivery_is_signed(request_: Request):
    assert is_signed(request_)


@pytest.mark.parametrize("request_", named_requests(lambda body: body == BAD_TIMESTAMP))
def test_a_delivery_refused_for_its_timestamp_is_outside_the_window(request_: Request):
    assert not is_timely(request_)


@pytest.mark.parametrize(
    "request_", named_requests(lambda body: body not in (BAD_SIGNATURE, BAD_TIMESTAMP))
)
def test_every_other_delivery_is_inside_the_window(request_: Request):
    assert is_timely(request_)


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(event, id=f"{listing} {event['id']}")
        for listing, event in listed_events()
        if event["id"] in DELIVERED
    ],
)
def test_an_event_the_api_lists_is_the_event_its_delivery_carries(event: Mapping[str, Any]):
    assert DELIVERED[event["id"]] == event
