import json

import pytest

from coding_study.adapters.mock_server.config import (
    MockDefinition,
    ResponseFields,
    Route,
    Scenario,
)
from coding_study.adapters.mock_server.control import ControlInterface, ControlRequest
from coding_study.adapters.mock_server.matching import MockRequest
from coding_study.adapters.mock_server.mock_state import MockState
from coding_study.adapters.mock_server.replies import Reply

TOKEN = "stack-token"
BEARER = f"Bearer {TOKEN}"
ROUTE = Route(
    id="rooms", method="GET", path="/rooms", query={}, response=ResponseFields(status=200)
)
OUTAGE = Scenario("outage", None, (ResponseFields(status=503),))
THEN_OK = Scenario("then_ok", None, (ResponseFields(status=429), ResponseFields(status=200)))
SCENARIO_BODY = json.dumps({"scenario": "outage"}).encode()
SCENARIO_PATH = "/mocks/room-vendor/scenario"
LOG_PATH = "/mocks/room-vendor/log"
GET_ROOMS = MockRequest(method="GET", path="/rooms", query={}, headers={}, body=b"")


def mock_states() -> dict[str, MockState]:
    scenarios = {"outage": OUTAGE, "then_ok": THEN_OK}
    return {
        name: MockState(MockDefinition(name, (ROUTE,), scenarios))
        for name in ("room-vendor", "second-vendor")
    }


def control_call(mocks: dict[str, MockState], **fields) -> Reply:
    defaults = {"method": "GET", "target": "/health", "authorization": BEARER, "body": b""}
    return ControlInterface(mocks, TOKEN).handle(ControlRequest(**{**defaults, **fields}))


def status_of(mocks: dict[str, MockState]) -> int:
    return mocks["room-vendor"].receive(GET_ROOMS).reply.status


def document_of(reply: Reply) -> dict:
    return json.loads(reply.body)


def test_health_answers_without_a_token():
    assert control_call(mock_states(), authorization=None).status == 200


def test_health_gives_nothing_away():
    assert document_of(control_call(mock_states(), authorization=None)) == {"status": "ok"}


@pytest.mark.parametrize(
    "authorization",
    [None, "", "Bearer", "Bearer ", "Bearer wrong", TOKEN, f"Basic {TOKEN}", f"{BEARER} extra"],
)
def test_anything_but_the_token_is_refused(authorization: str | None):
    reply = control_call(mock_states(), method="POST", target="/reset", authorization=authorization)
    assert reply.status == 401


def test_a_refusal_asks_for_a_bearer_token():
    reply = control_call(mock_states(), method="POST", target="/reset", authorization=None)
    assert reply.headers["WWW-Authenticate"] == "Bearer"


def test_a_token_outside_ascii_is_refused_without_an_error():
    reply = control_call(
        mock_states(), method="POST", target="/reset", authorization="Bearer tökén"
    )
    assert reply.status == 401


def test_an_unknown_path_without_a_token_gets_the_same_refusal():
    assert control_call(mock_states(), target="/mocks", authorization=None).status == 401


def test_a_refused_call_changes_nothing():
    mocks = mock_states()
    control_call(
        mocks, method="PUT", target=SCENARIO_PATH, authorization="Bearer no", body=SCENARIO_BODY
    )
    assert status_of(mocks) == 200


def test_setting_a_scenario_applies_it():
    mocks = mock_states()
    control_call(mocks, method="PUT", target=SCENARIO_PATH, body=SCENARIO_BODY)
    assert status_of(mocks) == 503


def test_setting_a_scenario_answers_what_is_set():
    reply = control_call(mock_states(), method="PUT", target=SCENARIO_PATH, body=SCENARIO_BODY)
    assert (reply.status, document_of(reply)) == (
        200,
        {"mock": "room-vendor", "scenario": "outage"},
    )


def test_a_scenario_is_set_on_one_mock_server_only():
    mocks = mock_states()
    control_call(mocks, method="PUT", target=SCENARIO_PATH, body=SCENARIO_BODY)
    assert mocks["second-vendor"].receive(GET_ROOMS).reply.status == 200


def test_null_clears_the_scenario():
    mocks = mock_states()
    control_call(mocks, method="PUT", target=SCENARIO_PATH, body=SCENARIO_BODY)
    control_call(mocks, method="PUT", target=SCENARIO_PATH, body=b'{"scenario": null}')
    assert status_of(mocks) == 200


def test_an_unknown_scenario_is_404_with_the_known_names():
    reply = control_call(
        mock_states(), method="PUT", target=SCENARIO_PATH, body=b'{"scenario": "flood"}'
    )
    assert (reply.status, document_of(reply)["known"]) == (404, ["outage", "then_ok"])


@pytest.mark.parametrize("target", ["/mocks/nobody/scenario", "/mocks/nobody/log"])
def test_an_unknown_mock_server_is_404_with_the_known_names(target: str):
    method = "PUT" if target.endswith("scenario") else "GET"
    reply = control_call(mock_states(), method=method, target=target, body=SCENARIO_BODY)
    assert (reply.status, document_of(reply)["known"]) == (404, ["room-vendor", "second-vendor"])


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not json",
        b"[]",
        b"{}",
        b'{"scenario": 1}',
        b'{"scenario": "outage", "extra": 1}',
        b"\xff",
    ],
)
def test_a_bad_scenario_body_is_400(body: bytes):
    assert control_call(mock_states(), method="PUT", target=SCENARIO_PATH, body=body).status == 400


def test_reset_clears_every_mock_servers_scenario():
    mocks = mock_states()
    control_call(mocks, method="PUT", target=SCENARIO_PATH, body=SCENARIO_BODY)
    control_call(mocks, method="POST", target="/reset")
    assert status_of(mocks) == 200


def test_reset_clears_every_mock_servers_log():
    mocks = mock_states()
    mocks["second-vendor"].receive(GET_ROOMS)
    control_call(mocks, method="POST", target="/reset")
    assert mocks["second-vendor"].log_document()["entries"] == []


def test_reset_answers_200():
    assert control_call(mock_states(), method="POST", target="/reset").status == 200


def test_the_log_is_read_per_mock_server():
    mocks = mock_states()
    mocks["room-vendor"].receive(GET_ROOMS)
    reply = control_call(mocks, target=LOG_PATH)
    assert [entry["path"] for entry in document_of(reply)["entries"]] == ["/rooms"]


def test_another_mock_servers_log_holds_nothing_of_it():
    mocks = mock_states()
    mocks["room-vendor"].receive(GET_ROOMS)
    reply = control_call(mocks, target="/mocks/second-vendor/log")
    assert document_of(reply)["entries"] == []


@pytest.mark.parametrize(
    ("method", "target", "allowed"),
    [
        ("GET", "/reset", "POST"),
        ("POST", SCENARIO_PATH, "PUT"),
        ("POST", LOG_PATH, "GET"),
        ("DELETE", LOG_PATH, "GET"),
    ],
)
def test_the_wrong_method_is_405_and_names_the_right_one(method: str, target: str, allowed: str):
    reply = control_call(mock_states(), method=method, target=target)
    assert (reply.status, reply.headers["Allow"]) == (405, allowed)


@pytest.mark.parametrize(
    "target", ["/", "/rooms", "/mocks", "/mocks/room-vendor", "/mocks/room-vendor/other", "/reset/"]
)
def test_an_unknown_path_with_the_token_is_404(target: str):
    assert control_call(mock_states(), target=target).status == 404


def test_a_query_on_a_control_path_is_ignored():
    assert control_call(mock_states(), method="POST", target="/reset?x=1").status == 200


def test_no_answer_carries_cors_headers():
    headers = control_call(mock_states(), target=LOG_PATH).headers
    assert not [name for name in headers if name.lower().startswith("access-control")]
