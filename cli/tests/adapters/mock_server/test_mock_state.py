from concurrent.futures import ThreadPoolExecutor

import pytest

from coding_study.adapters.mock_server.config import (
    Body,
    MockDefinition,
    ResponseFields,
    Route,
    Scenario,
)
from coding_study.adapters.mock_server.matching import MockRequest
from coding_study.adapters.mock_server.mock_state import MockState, UnknownScenarioError
from coding_study.adapters.mock_server.replies import json_reply

ROOMS = Route(
    id="rooms",
    method="GET",
    path="/rooms",
    query={},
    response=ResponseFields(status=200, body=Body(b"rooms")),
)
DESKS = Route(
    id="desks", method="GET", path="/desks", query={}, response=ResponseFields(status=200)
)
OUTAGE = Scenario("outage", None, (ResponseFields(status=503),))
ROOMS_ONLY = Scenario("rooms_only", "rooms", (ResponseFields(status=500),))
THEN_OK = Scenario(
    "then_ok",
    None,
    (ResponseFields(status=429, headers={"Retry-After": "1"}), ResponseFields(status=200)),
)
ROOMS_SEQUENCE = Scenario(
    "rooms_sequence", "rooms", (ResponseFields(status=429), ResponseFields(status=201))
)
SLOW = Scenario("slow", None, (ResponseFields(delay_ms=25),))
DEFINITION = MockDefinition(
    "room-vendor",
    (ROOMS, DESKS),
    {s.name: s for s in (OUTAGE, ROOMS_ONLY, THEN_OK, ROOMS_SEQUENCE, SLOW)},
)


def request(path: str = "/rooms") -> MockRequest:
    return MockRequest(method="GET", path=path, query={}, headers={}, body=b"")


def new_state() -> MockState:
    return MockState(DEFINITION)


def entries_of(state: MockState) -> list[dict[str, object]]:
    entries = state.log_document()["entries"]
    assert isinstance(entries, list)
    return entries


def numbered_state() -> MockState:
    numbered = Body(b"n-{{seq}}", template="n-{{seq}}")
    route = Route("n", "GET", "/rooms", {}, ResponseFields(status=200, body=numbered))
    return MockState(MockDefinition("room-vendor", (route,), {}))


def test_a_run_time_value_counts_requests_from_one():
    state = numbered_state()
    bodies = [state.receive(request()).reply.body for _ in range(2)]
    assert bodies == [b"n-1", b"n-2"]


def test_a_reset_counts_requests_from_one_again():
    state = numbered_state()
    state.receive(request())
    state.reset()
    assert state.receive(request()).reply.body == b"n-1"


def test_no_scenario_answers_the_routes_own_response():
    reply = new_state().receive(request()).reply
    assert (reply.status, reply.body) == (200, b"rooms")


def test_a_set_scenario_overrides_the_matched_response():
    state = new_state()
    state.set_scenario("outage")
    assert state.receive(request()).reply.status == 503


def test_a_scenario_keeps_fields_it_leaves_out():
    state = new_state()
    state.set_scenario("outage")
    assert state.receive(request()).reply.body == b"rooms"


def test_a_scenario_gives_its_delay():
    state = new_state()
    state.set_scenario("slow")
    assert state.receive(request()).reply.delay_ms == 25


def test_a_scenario_on_one_route_leaves_another_alone():
    state = new_state()
    state.set_scenario("rooms_only")
    assert state.receive(request("/desks")).reply.status == 200


def test_a_scenario_on_one_route_applies_there():
    state = new_state()
    state.set_scenario("rooms_only")
    assert state.receive(request()).reply.status == 500


def test_a_scenario_never_applies_to_an_unmatched_request():
    state = new_state()
    state.set_scenario("outage")
    assert state.receive(request("/other")).reply.status == 404


def test_an_unmatched_request_names_the_mock_server_in_its_answer():
    reply = new_state().receive(request("/other")).reply
    assert reply.body == json_reply(404, _no_route("/other")).body


def _no_route(path: str) -> dict[str, str]:
    return {"error": "no route", "mock": "room-vendor", "method": "GET", "path": path}


def test_an_unmatched_request_is_logged_as_unmatched():
    state = new_state()
    state.receive(request("/other"))
    entry = entries_of(state)[0]
    assert (entry["matched"], entry["route"], entry["status"]) == (False, None, 404)


def test_a_matched_request_logs_its_route_and_scenario():
    state = new_state()
    state.set_scenario("outage")
    state.receive(request())
    entry = entries_of(state)[0]
    assert (entry["matched"], entry["route"], entry["scenario"], entry["status"]) == (
        True,
        "rooms",
        "outage",
        503,
    )


def test_a_scenario_that_does_not_apply_is_not_logged_as_applied():
    state = new_state()
    state.set_scenario("rooms_only")
    state.receive(request("/desks"))
    assert entries_of(state)[0]["scenario"] is None


def test_a_sequence_advances_one_entry_per_request():
    state = new_state()
    state.set_scenario("then_ok")
    statuses = [state.receive(request()).reply.status for _ in range(2)]
    assert statuses == [429, 200]


def test_a_sequence_repeats_its_last_entry():
    state = new_state()
    state.set_scenario("then_ok")
    statuses = [state.receive(request()).reply.status for _ in range(4)]
    assert statuses == [429, 200, 200, 200]


def test_a_request_the_sequence_does_not_apply_to_does_not_advance_it():
    state = new_state()
    state.set_scenario("rooms_sequence")
    state.receive(request("/desks"))
    assert state.receive(request()).reply.status == 429


def test_an_unmatched_request_does_not_advance_a_sequence():
    state = new_state()
    state.set_scenario("then_ok")
    state.receive(request("/other"))
    assert state.receive(request()).reply.status == 429


def test_setting_a_scenario_restarts_its_sequence():
    state = new_state()
    state.set_scenario("then_ok")
    state.receive(request())
    state.set_scenario("then_ok")
    assert state.receive(request()).reply.status == 429


def test_setting_no_scenario_clears_it():
    state = new_state()
    state.set_scenario("outage")
    state.set_scenario(None)
    assert state.receive(request()).reply.status == 200


def test_an_unknown_scenario_is_refused():
    with pytest.raises(UnknownScenarioError):
        new_state().set_scenario("flood")


def test_an_unknown_scenario_leaves_the_current_one():
    state = new_state()
    state.set_scenario("outage")
    with pytest.raises(UnknownScenarioError):
        state.set_scenario("flood")
    assert state.receive(request()).reply.status == 503


def test_the_refusal_lists_the_known_scenarios():
    with pytest.raises(UnknownScenarioError) as refusal:
        new_state().set_scenario("flood")
    assert "outage" in refusal.value.known


def test_reset_restarts_a_sequence():
    state = new_state()
    state.set_scenario("then_ok")
    state.receive(request())
    state.reset()
    state.set_scenario("then_ok")
    assert state.receive(request()).reply.status == 429


def test_reset_clears_the_scenario():
    state = new_state()
    state.set_scenario("outage")
    state.reset()
    assert state.receive(request()).reply.status == 200


def test_reset_clears_the_log():
    state = new_state()
    state.receive(request())
    state.reset()
    assert entries_of(state) == []


def test_finishing_marks_the_response_time():
    state = new_state()
    state.finish(state.receive(request()))
    assert isinstance(entries_of(state)[0]["responded_ms"], int)


def test_a_refused_request_is_logged_with_its_answer():
    state = new_state()
    state.refuse(request(), json_reply(413, {"error": "too large"}))
    entry = entries_of(state)[0]
    assert (entry["matched"], entry["status"]) == (False, 413)


def test_a_refused_request_does_not_advance_a_sequence():
    state = new_state()
    state.set_scenario("then_ok")
    state.refuse(request(), json_reply(413, {"error": "too large"}))
    assert state.receive(request()).reply.status == 429


def test_concurrent_requests_each_get_their_own_sequence_entry():
    long_sequence = Scenario(
        "long", None, tuple(ResponseFields(status=200 + i) for i in range(200))
    )
    state = MockState(MockDefinition("room-vendor", (ROOMS,), {"long": long_sequence}))
    state.set_scenario("long")
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: state.receive(request()).reply.status, range(200)))
    assert sorted(statuses) == [200 + i for i in range(200)]
