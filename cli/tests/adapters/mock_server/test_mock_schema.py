import json
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from coding_study.adapters.schema_validation import SchemaValidator
from tests.helpers import SCHEMAS_DIRECTORY

MOCK_SCHEMA = SCHEMAS_DIRECTORY / "mock.schema.json"
SOURCE = "problems/x/mocks/room-vendor.yaml"

VALID_CONFIG = """
routes:
  - id: availability
    method: GET
    path: /v1/rooms/availability
    query: {date: "2027-03-01"}
    response:
      status: 200
      headers: {Content-Type: application/json}
      body_file: bodies/availability.json
  - id: room
    method: GET
    path: /v1/rooms/{room_id}
    response:
      status: 200
      body: {rooms: []}
scenarios:
  outage:
    visible: true
    status: 503
  slow:
    visible: true
    delay_ms: 2000
  malformed:
    route: availability
    status: 200
    headers: {Content-Type: application/json}
    body: '{"rooms": ['
  rate_limited:
    visible: true
    status: 429
    headers: {Retry-After: "2"}
  rate_limited_then_ok:
    sequence:
      - {status: 429, headers: {Retry-After: "1"}}
      - {status: 200, body_file: bodies/availability.json}
"""

type Mutation = Callable[[dict[str, Any]], None]


def valid_config() -> dict[str, Any]:
    return yaml.safe_load(VALID_CONFIG)


def violations(config: dict[str, Any]) -> list[str]:
    issues = SchemaValidator.from_file(MOCK_SCHEMA).violations(config, SOURCE)
    return [issue.message for issue in issues]


def first_route(config: dict[str, Any]) -> dict[str, Any]:
    return config["routes"][0]


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(json.loads(MOCK_SCHEMA.read_text()))


def test_the_spec_shaped_example_is_valid():
    assert violations(valid_config()) == []


def test_scenarios_are_optional():
    config = valid_config()
    del config["scenarios"]
    assert violations(config) == []


def test_a_broken_json_body_is_allowed_by_design():
    config = valid_config()
    config["scenarios"]["malformed"]["body"] = '{"rooms": ['
    assert violations(config) == []


INVALID: dict[str, Mutation] = {
    "no routes key": lambda config: config.pop("routes"),
    "empty routes": lambda config: config.update(routes=[]),
    "unknown top-level field": lambda config: config.update(extra=1),
    "route without id": lambda config: first_route(config).pop("id"),
    "route without method": lambda config: first_route(config).pop("method"),
    "route without path": lambda config: first_route(config).pop("path"),
    "route without response": lambda config: first_route(config).pop("response"),
    "response without status": lambda config: first_route(config)["response"].pop("status"),
    "unknown route field": lambda config: first_route(config).update(extra=1),
    "unknown response field": lambda config: first_route(config)["response"].update(extra=1),
    "lowercase method": lambda config: first_route(config).update(method="get"),
    "path without a slash": lambda config: first_route(config).update(path="v1/rooms"),
    "path with a query": lambda config: first_route(config).update(path="/v1/rooms?a=1"),
    "parameter inside a segment": lambda config: first_route(config).update(path="/v1/r{id}"),
    "query value that is a number": lambda config: first_route(config).update(query={"limit": 10}),
    "status below range": lambda config: first_route(config)["response"].update(status=199),
    "status above range": lambda config: first_route(config)["response"].update(status=600),
    "status as a string": lambda config: first_route(config)["response"].update(status="200"),
    "header value as a number": lambda config: first_route(config)["response"].update(
        headers={"Retry-After": 2}
    ),
    "header value with a line break": lambda config: first_route(config)["response"].update(
        headers={"X-Note": "a\nb"}
    ),
    "body and body_file together": lambda config: first_route(config)["response"].update(
        body="x", body_file="bodies/x.json"
    ),
    "body as a number": lambda config: config["routes"][1]["response"].update(body=1),
    "absolute body_file": lambda config: first_route(config)["response"].update(
        body_file="/etc/hosts"
    ),
    "body_file climbing out": lambda config: first_route(config)["response"].update(
        body_file="../secret.json"
    ),
    "negative delay": lambda config: config["scenarios"]["slow"].update(delay_ms=-1),
    "scenario overriding nothing": lambda config: config["scenarios"].update(idle={"visible": True}),
    "sequence next to status": lambda config: config["scenarios"]["rate_limited_then_ok"].update(
        status=503
    ),
    "empty sequence": lambda config: config["scenarios"]["rate_limited_then_ok"].update(sequence=[]),
    "empty sequence entry": lambda config: config["scenarios"]["rate_limited_then_ok"].update(
        sequence=[{}]
    ),
    "scenario name with a space": lambda config: config["scenarios"].update(
        {"two words": {"status": 503}}
    ),
    "unknown scenario field": lambda config: config["scenarios"]["outage"].update(extra=1),
    "visible as a string": lambda config: config["scenarios"]["outage"].update(visible="yes"),
}


@pytest.mark.parametrize("mutate", INVALID.values(), ids=INVALID.keys())
def test_invalid_configs_are_refused(mutate: Mutation):
    config = valid_config()
    mutate(config)
    assert violations(config) != []
