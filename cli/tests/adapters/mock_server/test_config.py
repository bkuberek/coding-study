import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.mock_server.config import (
    Body,
    ConfigError,
    StackConfig,
    load_stack_config,
)

type Mutation = Callable[[dict[str, Any]], None]


def valid_document() -> dict[str, Any]:
    return {
        "control_token": "secret",
        "mocks": {
            "room-vendor": {
                "routes": [
                    {
                        "id": "rooms",
                        "method": "GET",
                        "path": "/v1/rooms/{room_id}",
                        "query": {"date": "2027-03-01"},
                        "response": {"status": 200, "body": {"rooms": []}},
                    }
                ],
                "scenarios": {
                    "outage": {"visible": True, "status": 503},
                    "rate_limited_then_ok": {
                        "route": "rooms",
                        "sequence": [
                            {"status": 429, "headers": {"Retry-After": "1"}},
                            {"status": 200, "delay_ms": 5},
                        ],
                    },
                },
            }
        },
    }


def load(document: dict[str, Any], folder: Path) -> StackConfig:
    path = folder / "mocks.json"
    path.write_text(json.dumps(document))
    return load_stack_config(path)


def mock_of(document: dict[str, Any]) -> dict[str, Any]:
    return document["mocks"]["room-vendor"]


def route_of(document: dict[str, Any]) -> dict[str, Any]:
    return mock_of(document)["routes"][0]


def response_of(document: dict[str, Any]) -> dict[str, Any]:
    return route_of(document)["response"]


def scenarios_of(document: dict[str, Any]) -> dict[str, Any]:
    return mock_of(document)["scenarios"]


def test_it_reads_the_control_token(tmp_path: Path):
    assert load(valid_document(), tmp_path).control_token == "secret"


def test_it_keeps_every_mock_server_by_name(tmp_path: Path):
    document = valid_document()
    document["mocks"]["second-vendor"] = mock_of(document)
    assert [mock.name for mock in load(document, tmp_path).mocks] == [
        "room-vendor",
        "second-vendor",
    ]


def test_it_reads_a_route(tmp_path: Path):
    route = load(valid_document(), tmp_path).mocks[0].routes[0]
    assert (route.id, route.method, route.path, route.query) == (
        "rooms",
        "GET",
        "/v1/rooms/{room_id}",
        {"date": "2027-03-01"},
    )


def test_a_mapping_body_is_compact_json_with_its_content_type(tmp_path: Path):
    response = load(valid_document(), tmp_path).mocks[0].routes[0].response
    assert response.body == Body(content=b'{"rooms":[]}', content_type="application/json")


def test_a_list_body_is_json_too(tmp_path: Path):
    document = valid_document()
    response_of(document)["body"] = [1, 2]
    assert load(document, tmp_path).mocks[0].routes[0].response.body == Body(
        content=b"[1,2]", content_type="application/json"
    )


def test_a_string_body_is_sent_as_it_is(tmp_path: Path):
    document = valid_document()
    response_of(document)["body"] = '{"rooms": ['
    assert load(document, tmp_path).mocks[0].routes[0].response.body == Body(content=b'{"rooms": [')


def test_a_body_file_is_read_relative_to_the_config(tmp_path: Path):
    (tmp_path / "bodies").mkdir()
    (tmp_path / "bodies" / "raw.bin").write_bytes(b"\xff\x00raw")
    document = valid_document()
    del response_of(document)["body"]
    response_of(document)["body_file"] = "bodies/raw.bin"
    assert load(document, tmp_path).mocks[0].routes[0].response.body == Body(content=b"\xff\x00raw")


def test_a_plain_scenario_is_a_sequence_of_one(tmp_path: Path):
    outage = load(valid_document(), tmp_path).mocks[0].scenarios["outage"]
    assert [entry.status for entry in outage.entries] == [503]


def test_a_sequence_keeps_its_entries_in_order(tmp_path: Path):
    sequence = load(valid_document(), tmp_path).mocks[0].scenarios["rate_limited_then_ok"]
    assert [entry.status for entry in sequence.entries] == [429, 200]


def test_a_scenario_keeps_its_route(tmp_path: Path):
    sequence = load(valid_document(), tmp_path).mocks[0].scenarios["rate_limited_then_ok"]
    assert sequence.route_id == "rooms"


def test_scenarios_are_optional(tmp_path: Path):
    document = valid_document()
    del mock_of(document)["scenarios"]
    assert load(document, tmp_path).mocks[0].scenarios == {}


REFUSED: dict[str, tuple[Mutation, str]] = {
    "no token": (lambda doc: doc.pop("control_token"), "control_token"),
    "empty token": (lambda doc: doc.update(control_token=""), "control_token"),
    "no mock servers": (lambda doc: doc.update(mocks={}), "mocks"),
    "uppercase mock server name": (
        lambda doc: doc.update(mocks={"Room": mock_of(doc)}),
        "mocks.Room",
    ),
    "unknown top-level field": (lambda doc: doc.update(extra=1), "extra"),
    "routes not a list": (lambda doc: mock_of(doc).update(routes={}), "routes"),
    "no routes": (lambda doc: mock_of(doc).update(routes=[]), "routes"),
    "unknown route field": (lambda doc: route_of(doc).update(extra=1), "extra"),
    "duplicate route id": (lambda doc: mock_of(doc)["routes"].append(route_of(doc)), "rooms"),
    "lowercase method": (lambda doc: route_of(doc).update(method="get"), "method"),
    "path without a slash": (lambda doc: route_of(doc).update(path="rooms"), "path"),
    "parameter inside a segment": (lambda doc: route_of(doc).update(path="/r{id}"), "path"),
    "path with a trailing line break": (lambda doc: route_of(doc).update(path="/r\n"), "path"),
    "query value not a string": (lambda doc: route_of(doc).update(query={"a": 1}), "query"),
    "no status": (lambda doc: response_of(doc).pop("status"), "status"),
    "status a boolean": (lambda doc: response_of(doc).update(status=True), "status"),
    "status out of range": (lambda doc: response_of(doc).update(status=199), "status"),
    "header not a string": (lambda doc: response_of(doc).update(headers={"A": 1}), "headers"),
    "header with a line break": (
        lambda doc: response_of(doc).update(headers={"A": "b\r\nC: d"}),
        "headers",
    ),
    "header outside latin-1": (lambda doc: response_of(doc).update(headers={"A": "é€"}), "headers"),
    "body and body_file": (
        lambda doc: response_of(doc).update(body_file="x"),
        "body_file",
    ),
    "body a number": (lambda doc: response_of(doc).update(body=1), "body"),
    "negative delay": (lambda doc: response_of(doc).update(delay_ms=-1), "delay_ms"),
    "unknown response field": (lambda doc: response_of(doc).update(extra=1), "extra"),
    "scenario route unknown": (lambda doc: scenarios_of(doc)["outage"].update(route="no"), "no"),
    "unknown scenario field": (lambda doc: scenarios_of(doc)["outage"].update(extra=1), "extra"),
    "scenario overriding nothing": (
        lambda doc: scenarios_of(doc).update(idle={"visible": True}),
        "idle",
    ),
    "sequence next to status": (
        lambda doc: scenarios_of(doc)["rate_limited_then_ok"].update(status=503),
        "sequence",
    ),
    "empty sequence": (
        lambda doc: scenarios_of(doc)["rate_limited_then_ok"].update(sequence=[]),
        "sequence",
    ),
}


@pytest.mark.parametrize(("mutate", "named"), REFUSED.values(), ids=REFUSED.keys())
def test_a_bad_config_is_refused_with_its_location(mutate: Mutation, named: str, tmp_path: Path):
    document = valid_document()
    mutate(document)
    with pytest.raises(ConfigError, match=named):
        load(document, tmp_path)


@pytest.mark.parametrize("body_file", ["../secret", "/etc/hosts", "a/../../secret"])
def test_a_body_file_outside_the_config_folder_is_refused(body_file: str, tmp_path: Path):
    document = valid_document()
    del response_of(document)["body"]
    response_of(document)["body_file"] = body_file
    with pytest.raises(ConfigError, match="body_file"):
        load(document, tmp_path)


def test_a_body_file_linking_outside_the_config_folder_is_refused(tmp_path: Path):
    folder = tmp_path / "rendered"
    folder.mkdir()
    (tmp_path / "secret").write_text("x")
    (folder / "link").symlink_to(tmp_path / "secret")
    document = valid_document()
    del response_of(document)["body"]
    response_of(document)["body_file"] = "link"
    with pytest.raises(ConfigError, match="body_file"):
        load(document, folder)


def test_a_missing_body_file_is_refused_at_start(tmp_path: Path):
    document = valid_document()
    del response_of(document)["body"]
    response_of(document)["body_file"] = "gone.json"
    with pytest.raises(ConfigError, match=r"gone\.json"):
        load(document, tmp_path)


def test_a_missing_config_file_is_refused(tmp_path: Path):
    with pytest.raises(ConfigError, match=r"absent\.json"):
        load_stack_config(tmp_path / "absent.json")


def test_a_file_that_is_not_json_is_refused(tmp_path: Path):
    path = tmp_path / "mocks.json"
    path.write_text("routes: []")
    with pytest.raises(ConfigError, match=r"mocks\.json"):
        load_stack_config(path)
