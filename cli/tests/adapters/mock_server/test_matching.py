from coding_study.adapters.mock_server.config import Body, ResponseFields, Route, Scenario
from coding_study.adapters.mock_server.matching import (
    MockRequest,
    find_route,
    parse_target,
    reply_for,
    scenario_applies,
    scenario_entry,
)

JSON_BODY = Body(content=b'{"rooms":[]}', content_type="application/json")
OK_RESPONSE = ResponseFields(status=200)


def route(path: str = "/v1/rooms", **fields) -> Route:
    defaults = {"id": "rooms", "method": "GET", "query": {}, "response": OK_RESPONSE}
    return Route(path=path, **{**defaults, **fields})


def request(target: str = "/v1/rooms", method: str = "GET") -> MockRequest:
    path, query = parse_target(target)
    return MockRequest(method=method, path=path, query=query, headers={}, body=b"")


def scenario(*entries: ResponseFields, route_id: str | None = None) -> Scenario:
    return Scenario(name="any", route_id=route_id, entries=entries)


def test_a_route_matches_its_exact_method_and_path():
    rooms = route()
    assert find_route((rooms,), request()) is rooms


def test_another_path_does_not_match():
    assert find_route((route(),), request("/v1/other")) is None


def test_another_method_does_not_match():
    assert find_route((route(),), request(method="POST")) is None


def test_a_trailing_slash_is_another_path():
    assert find_route((route(),), request("/v1/rooms/")) is None


def test_a_parameter_matches_one_segment():
    room = route("/v1/rooms/{room_id}/slots")
    assert find_route((room,), request("/v1/rooms/oak/slots")) is room


def test_a_parameter_does_not_match_two_segments():
    assert find_route((route("/v1/rooms/{room_id}"),), request("/v1/rooms/oak/slots")) is None


def test_a_parameter_does_not_match_an_empty_segment():
    assert find_route((route("/v1/rooms/{room_id}"),), request("/v1/rooms/")) is None


def test_a_listed_query_key_must_match():
    dated = route(query={"date": "2027-03-01"})
    assert find_route((dated,), request("/v1/rooms?date=2027-03-01")) is dated


def test_a_listed_query_key_with_another_value_does_not_match():
    dated = route(query={"date": "2027-03-01"})
    assert find_route((dated,), request("/v1/rooms?date=2027-03-02")) is None


def test_a_missing_query_key_does_not_match():
    assert find_route((route(query={"date": "2027-03-01"}),), request()) is None


def test_an_unlisted_query_key_is_ignored():
    rooms = route()
    assert find_route((rooms,), request("/v1/rooms?page=2")) is rooms


def test_a_repeated_query_key_matches_on_any_of_its_values():
    tagged = route(query={"tag": "b"})
    assert find_route((tagged,), request("/v1/rooms?tag=a&tag=b")) is tagged


def test_the_first_match_wins():
    first = route(id="first")
    assert find_route((first, route(id="second")), request()) is first


def test_an_earlier_query_route_falls_through_to_a_later_plain_one():
    plain = route(id="plain")
    assert find_route((route(query={"date": "x"}), plain), request()) is plain


def test_a_blank_query_value_is_kept():
    assert parse_target("/x?a=&b=1") == ("/x", {"a": ("",), "b": ("1",)})


def test_a_target_without_a_query_has_an_empty_one():
    assert parse_target("/x") == ("/x", {})


def test_a_double_slash_target_stays_a_path():
    assert parse_target("//x/y") == ("//x/y", {})


def test_a_scenario_without_a_route_applies_to_every_route():
    assert scenario_applies(scenario(OK_RESPONSE), route())


def test_a_scenario_with_its_route_applies():
    assert scenario_applies(scenario(OK_RESPONSE, route_id="rooms"), route())


def test_a_scenario_with_another_route_does_not_apply():
    assert not scenario_applies(scenario(OK_RESPONSE, route_id="other"), route())


def test_a_sequence_gives_its_entries_in_order():
    first, second = ResponseFields(status=429), ResponseFields(status=200)
    sequence = scenario(first, second)
    assert [scenario_entry(sequence, position) for position in range(2)] == [first, second]


def test_a_sequence_repeats_its_last_entry():
    last = ResponseFields(status=200)
    assert scenario_entry(scenario(ResponseFields(status=429), last), 7) is last


def test_a_route_alone_gives_its_own_response():
    response = ResponseFields(status=201, headers={"X-A": "1"}, body=Body(b"hi"), delay_ms=5)
    reply = reply_for(route(response=response), None)
    assert (reply.status, reply.headers, reply.body, reply.delay_ms) == (
        201,
        {"X-A": "1"},
        b"hi",
        5,
    )


def test_a_route_without_a_body_answers_empty():
    assert reply_for(route(), None).body == b""


def test_a_route_without_a_delay_answers_at_once():
    assert reply_for(route(), None).delay_ms == 0


def test_a_scenario_status_keeps_the_routes_body():
    with_body = route(response=ResponseFields(status=200, body=Body(b"hi")))
    reply = reply_for(with_body, ResponseFields(status=503))
    assert (reply.status, reply.body) == (503, b"hi")


def test_scenario_headers_replace_the_routes_whole():
    with_headers = route(response=ResponseFields(status=200, headers={"X-Route": "1"}))
    reply = reply_for(with_headers, ResponseFields(headers={"Retry-After": "2"}))
    assert reply.headers == {"Retry-After": "2"}


def test_a_scenario_with_empty_headers_clears_the_routes():
    with_headers = route(response=ResponseFields(status=200, headers={"X-Route": "1"}))
    assert reply_for(with_headers, ResponseFields(headers={})).headers == {}


def test_a_scenario_with_an_empty_body_clears_the_routes():
    with_body = route(response=ResponseFields(status=200, body=Body(b"hi")))
    assert reply_for(with_body, ResponseFields(body=Body(b""))).body == b""


def test_a_scenario_delay_keeps_the_routes_status():
    reply = reply_for(route(), ResponseFields(delay_ms=30))
    assert (reply.status, reply.delay_ms) == (200, 30)


def test_a_json_body_defaults_its_content_type():
    with_json = route(response=ResponseFields(status=200, body=JSON_BODY))
    assert reply_for(with_json, None).headers == {"Content-Type": "application/json"}


def test_an_authors_content_type_wins_in_any_case():
    headers = {"content-type": "text/plain"}
    with_json = route(response=ResponseFields(status=200, headers=headers, body=JSON_BODY))
    assert reply_for(with_json, None).headers == headers


def test_a_plain_string_body_gets_no_content_type():
    with_text = route(response=ResponseFields(status=200, body=Body(b"not json")))
    assert reply_for(with_text, None).headers == {}
