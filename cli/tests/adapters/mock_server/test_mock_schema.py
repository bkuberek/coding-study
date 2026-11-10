import json
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from coding_study.adapters.schema_validation import SchemaValidator
from tests.helpers import SCHEMAS_DIRECTORY
from tests.mock_server_support import sample_document

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


@pytest.mark.parametrize("name", sample_document()["mocks"])
def test_the_sample_mock_servers_are_valid(name: str):
    assert violations(sample_document()["mocks"][name]) == []


def test_scenarios_are_optional():
    config = valid_config()
    del config["scenarios"]
    assert violations(config) == []


def test_a_broken_json_body_is_allowed_by_design():
    config = valid_config()
    config["scenarios"]["malformed"]["body"] = '{"rooms": ['
    assert violations(config) == []


def test_a_config_may_record_its_shape_version():
    config = valid_config()
    config["shape_version"] = "generic chat-completions style, docs read 2026-11"
    assert violations(config) == []


def test_a_shape_version_is_a_text():
    config = valid_config()
    config["shape_version"] = 2026
    assert violations(config) != []


def test_a_route_may_match_on_its_body():
    config = valid_config()
    first_route(config)["match"] = {"body": {"stream": True}, "body_contains": "refund"}
    assert violations(config) == []


def streaming_config() -> dict[str, Any]:
    return {
        "routes": [
            {
                "id": "chat",
                "method": "POST",
                "path": "/v1/chat",
                "response": {
                    "status": 200,
                    "stream": [
                        {"event": "delta", "data": '{"t": "Desk"}', "after_ms": 20},
                        {"raw": ": keep-alive\n\n"},
                        {"data": "[DONE]"},
                    ],
                },
            }
        ],
        "scenarios": {
            "dropped": {"visible": True, "drop_after_chunks": 1},
            "stalled": {"sequence": [{"stall_after_chunks": 0}, {"status": 200}]},
            "malformed": {"stream": [{"data": '{"t": '}]},
        },
    }


def test_a_streaming_mock_server_is_valid():
    assert violations(streaming_config()) == []


def chat_response(config: dict[str, Any]) -> dict[str, Any]:
    return first_route(config)["response"]


STREAMING_INVALID: dict[str, Mutation] = {
    "body next to a stream": lambda config: chat_response(config).update(body="x"),
    "empty stream": lambda config: chat_response(config).update(stream=[]),
    "chunk with neither data nor raw": lambda config: chat_response(config).update(
        stream=[{"event": "delta"}]
    ),
    "chunk with raw and data": lambda config: chat_response(config).update(
        stream=[{"raw": "x", "data": "y"}]
    ),
    "chunk with raw and event": lambda config: chat_response(config).update(
        stream=[{"raw": "x", "event": "y"}]
    ),
    "event with a line break": lambda config: chat_response(config).update(
        stream=[{"event": "a\nb", "data": "y"}]
    ),
    "unknown chunk field": lambda config: chat_response(config).update(
        stream=[{"data": "y", "id": "1"}]
    ),
    "drop and stall together": lambda config: config["scenarios"]["dropped"].update(
        stall_after_chunks=1
    ),
    "negative drop": lambda config: config["scenarios"]["dropped"].update(drop_after_chunks=-1),
    "drop in a route's response": lambda config: chat_response(config).update(drop_after_chunks=1),
    "drop next to a sequence": lambda config: config["scenarios"]["stalled"].update(
        drop_after_chunks=1
    ),
}


@pytest.mark.parametrize("mutate", STREAMING_INVALID.values(), ids=STREAMING_INVALID.keys())
def test_invalid_streaming_configs_are_refused(mutate: Mutation):
    config = streaming_config()
    mutate(config)
    assert violations(config) != []


def pass_through_config() -> dict[str, Any]:
    return {
        "upstream": "http://keycloak:8080",
        "routes": [{"id": "token", "method": "POST", "path": "/realms/pp3/token"}],
        "scenarios": {
            "alg_none": {"route": "token", "jwt": {"field": "id_token", "tamper": "alg_none"}},
            "bad_signature": {
                "route": "token",
                "sequence": [{"jwt": {"field": "id_token", "tamper": "bad_signature"}}],
            },
        },
    }


def test_a_pass_through_mock_server_with_jwt_scenarios_is_valid():
    assert violations(pass_through_config()) == []


PASS_THROUGH_INVALID: dict[str, Mutation] = {
    "upstream with a path": lambda config: config.update(upstream="http://keycloak:8080/x"),
    "upstream over https": lambda config: config.update(upstream="https://keycloak:8443"),
    "unknown tamper": lambda config: config["scenarios"]["alg_none"]["jwt"].update(tamper="sign"),
    "jwt without a field": lambda config: config["scenarios"]["alg_none"]["jwt"].pop("field"),
    "jwt with an extra field": lambda config: config["scenarios"]["alg_none"]["jwt"].update(key=1),
    "jwt in a route's response": lambda config: first_route(config).update(
        response={"status": 200, "jwt": {"field": "id_token", "tamper": "alg_none"}}
    ),
    "route without a response and no upstream": lambda config: config.pop("upstream"),
}


@pytest.mark.parametrize("mutate", PASS_THROUGH_INVALID.values(), ids=PASS_THROUGH_INVALID.keys())
def test_invalid_pass_through_configs_are_refused(mutate: Mutation):
    config = pass_through_config()
    mutate(config)
    assert violations(config) != []


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
    "scenario overriding nothing": lambda config: config["scenarios"].update(
        idle={"visible": True}
    ),
    "sequence next to status": lambda config: config["scenarios"]["rate_limited_then_ok"].update(
        status=503
    ),
    "empty sequence": lambda config: config["scenarios"]["rate_limited_then_ok"].update(
        sequence=[]
    ),
    "empty sequence entry": lambda config: config["scenarios"]["rate_limited_then_ok"].update(
        sequence=[{}]
    ),
    "scenario name with a space": lambda config: config["scenarios"].update(
        {"two words": {"status": 503}}
    ),
    "unknown scenario field": lambda config: config["scenarios"]["outage"].update(extra=1),
    "visible as a string": lambda config: config["scenarios"]["outage"].update(visible="yes"),
    "match with no condition": lambda config: first_route(config).update(match={}),
    "match body as a list": lambda config: first_route(config).update(match={"body": [1]}),
    "empty body_contains": lambda config: first_route(config).update(match={"body_contains": ""}),
    "unknown match field": lambda config: first_route(config).update(match={"headers": {}}),
}


@pytest.mark.parametrize("mutate", INVALID.values(), ids=INVALID.keys())
def test_invalid_configs_are_refused(mutate: Mutation):
    config = valid_config()
    mutate(config)
    assert violations(config) != []
