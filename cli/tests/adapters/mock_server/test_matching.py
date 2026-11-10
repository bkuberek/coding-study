from coding_study.adapters.mock_server.config import (
    Body,
    ResponseFields,
    Route,
    Scenario,
    StreamChunk,
    StreamCut,
    StreamCutKind,
)
from coding_study.adapters.mock_server.matching import (
    MockRequest,
    find_route,
    parse_target,
    reply_for,
    scenario_applies,
    scenario_entry,
)
from coding_study.adapters.mock_server.replies import Frame, Reply
from coding_study.adapters.mock_server.templates import RequestValues

JSON_BODY = Body(content=b'{"rooms":[]}', content_type="application/json")
OK_RESPONSE = ResponseFields(status=200)


def route(path: str = "/v1/rooms", **fields) -> Route:
    defaults = {"id": "rooms", "method": "GET", "query": {}, "response": OK_RESPONSE}
    return Route(path=path, **{**defaults, **fields})


def request(target: str = "/v1/rooms", method: str = "GET", body: bytes = b"") -> MockRequest:
    path, query = parse_target(target)
    return MockRequest(method=method, path=path, query=query, headers={}, body=body)


def posted(body: bytes) -> MockRequest:
    return request("/v1/chat", "POST", body)


def chat_route(**fields) -> Route:
    return route("/v1/chat", method="POST", **fields)


def scenario(*entries: ResponseFields, route_id: str | None = None) -> Scenario:
    return Scenario(name="any", route_id=route_id, entries=entries)


def answered(answering: Route, overrides: ResponseFields | None = None) -> Reply:
    return reply_for(answering, overrides, RequestValues(request(), 1))


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


def test_a_body_subset_matches_a_request_that_holds_its_fields():
    streaming = chat_route(match_body={"stream": True})
    assert find_route((streaming,), posted(b'{"model": "m", "stream": true}')) is streaming


def test_a_body_subset_does_not_match_another_value():
    streaming = chat_route(match_body={"stream": True})
    assert find_route((streaming,), posted(b'{"stream": false}')) is None


def test_a_body_subset_does_not_match_a_missing_field():
    assert find_route((chat_route(match_body={"stream": True}),), posted(b"{}")) is None


def test_a_body_subset_does_not_match_a_body_that_is_not_json():
    assert find_route((chat_route(match_body={"stream": True}),), posted(b"stream")) is None


def test_a_body_subset_does_not_match_an_empty_body():
    assert find_route((chat_route(match_body={"stream": True}),), posted(b"")) is None


def test_a_body_subset_falls_through_to_a_later_route():
    plain = chat_route(id="plain")
    routes = (chat_route(match_body={"stream": True}), plain)
    assert find_route(routes, posted(b'{"stream": false}')) is plain


def test_body_contains_matches_text_anywhere_in_the_body():
    refunds = chat_route(match_body_contains="refund")
    assert find_route((refunds,), posted(b'{"input": "desk pass refunds"}')) is refunds


def test_body_contains_does_not_match_a_body_without_the_text():
    refunds = chat_route(match_body_contains="refund")
    assert find_route((refunds,), posted(b'{"input": "opening hours"}')) is None


def test_a_body_match_needs_both_of_its_conditions():
    both = chat_route(match_body={"stream": True}, match_body_contains="refund")
    assert find_route((both,), posted(b'{"stream": true, "input": "hours"}')) is None


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
    reply = answered(route(response=response))
    assert (reply.status, reply.headers, reply.body, reply.delay_ms) == (
        201,
        {"X-A": "1"},
        b"hi",
        5,
    )


def test_a_route_without_a_body_answers_empty():
    assert answered(route()).body == b""


def test_a_route_without_a_delay_answers_at_once():
    assert answered(route()).delay_ms == 0


def test_a_scenario_status_keeps_the_routes_body():
    with_body = route(response=ResponseFields(status=200, body=Body(b"hi")))
    reply = answered(with_body, ResponseFields(status=503))
    assert (reply.status, reply.body) == (503, b"hi")


def test_scenario_headers_replace_the_routes_whole():
    with_headers = route(response=ResponseFields(status=200, headers={"X-Route": "1"}))
    reply = answered(with_headers, ResponseFields(headers={"Retry-After": "2"}))
    assert reply.headers == {"Retry-After": "2"}


def test_a_scenario_with_empty_headers_clears_the_routes():
    with_headers = route(response=ResponseFields(status=200, headers={"X-Route": "1"}))
    assert answered(with_headers, ResponseFields(headers={})).headers == {}


def test_a_scenario_with_an_empty_body_clears_the_routes():
    with_body = route(response=ResponseFields(status=200, body=Body(b"hi")))
    assert answered(with_body, ResponseFields(body=Body(b""))).body == b""


def test_a_scenario_delay_keeps_the_routes_status():
    reply = answered(route(), ResponseFields(delay_ms=30))
    assert (reply.status, reply.delay_ms) == (200, 30)


def test_a_json_body_defaults_its_content_type():
    with_json = route(response=ResponseFields(status=200, body=JSON_BODY))
    assert answered(with_json).headers == {"Content-Type": "application/json"}


def test_an_authors_content_type_wins_in_any_case():
    headers = {"content-type": "text/plain"}
    with_json = route(response=ResponseFields(status=200, headers=headers, body=JSON_BODY))
    assert answered(with_json).headers == headers


def echoing(template: object) -> Route:
    body = Body(b"unused", "application/json", template=template)
    return chat_route(response=ResponseFields(status=200, body=body))


def test_a_json_body_fills_in_the_requests_values():
    request_values = RequestValues(posted(b'{"model": "chat-small"}'), 1)
    reply = reply_for(echoing({"model": "{{request.body.model}}"}), None, request_values)
    assert reply.body == b'{"model":"chat-small"}'


def test_a_text_body_fills_in_the_requests_values():
    request_values = RequestValues(posted(b"{}"), 4)
    reply = reply_for(echoing("call {{seq}}"), None, request_values)
    assert reply.body == b"call 4"


def test_a_scenarios_body_fills_in_the_requests_values_too():
    request_values = RequestValues(posted(b"{}"), 2)
    override = ResponseFields(body=Body(b"unused", template="retry {{seq}}"))
    assert reply_for(chat_route(), override, request_values).body == b"retry 2"


DESK = StreamChunk(data='{"t": "Desk"}', event="delta", after_ms=20)
DONE = StreamChunk(data="[DONE]")


def streaming(*chunks: StreamChunk, headers: dict[str, str] | None = None) -> Route:
    response = ResponseFields(status=200, headers=headers, stream=chunks or (DESK, DONE))
    return chat_route(response=response)


def test_a_stream_sends_each_chunk_as_an_event():
    assert answered(streaming()).stream == (
        Frame(b'event: delta\ndata: {"t": "Desk"}\n\n', 20),
        Frame(b"data: [DONE]\n\n", 0),
    )


def only_frame(reply: Reply) -> bytes:
    assert reply.stream is not None
    (frame,) = reply.stream
    return frame.content


def test_a_chunk_of_several_lines_sends_a_data_line_each():
    assert only_frame(answered(streaming(StreamChunk(data="a\nb")))) == b"data: a\ndata: b\n\n"


def test_a_raw_chunk_is_sent_as_written():
    assert only_frame(answered(streaming(StreamChunk(raw='data: {"t": ')))) == b'data: {"t": '


def test_a_chunk_fills_in_the_requests_values():
    chunk = StreamChunk(data="{{json(request.body.model)}}")
    request_values = RequestValues(posted(b'{"model": "chat-small"}'), 1)
    reply = reply_for(streaming(chunk), None, request_values)
    assert only_frame(reply) == b'data: "chat-small"\n\n'


def test_a_stream_defaults_its_content_type():
    assert answered(streaming()).headers == {"Content-Type": "text/event-stream"}


def test_an_authors_content_type_wins_over_a_streams():
    headers = {"content-type": "text/plain"}
    assert answered(streaming(headers=headers)).headers == headers


def test_a_stream_sends_no_body():
    assert answered(streaming()).body == b""


def test_a_drop_keeps_the_chunks_before_it():
    override = ResponseFields(cut=StreamCut(StreamCutKind.DROP, 1))
    assert [frame.after_ms for frame in answered(streaming(), override).stream or ()] == [20]


def test_a_drop_closes_without_holding_the_connection():
    override = ResponseFields(cut=StreamCut(StreamCutKind.DROP, 1))
    assert not answered(streaming(), override).holds_open


def test_a_stall_keeps_the_chunks_before_it_and_holds_the_connection():
    reply = answered(streaming(), ResponseFields(cut=StreamCut(StreamCutKind.STALL, 0)))
    assert (reply.stream, reply.holds_open) == ((), True)


def test_a_cut_on_an_answer_with_no_stream_changes_nothing():
    reply = answered(chat_route(), ResponseFields(cut=StreamCut(StreamCutKind.STALL, 0)))
    assert (reply.stream, reply.holds_open) == (None, False)


def test_a_scenario_status_keeps_the_routes_stream():
    assert answered(streaming(), ResponseFields(status=500)).stream is not None


def test_a_scenario_body_replaces_the_routes_stream():
    reply = answered(streaming(), ResponseFields(status=429, body=Body(b"slow down")))
    assert (reply.stream, reply.body) == (None, b"slow down")


def test_a_scenario_stream_replaces_the_routes_body():
    with_body = chat_route(response=ResponseFields(status=200, body=Body(b"whole")))
    reply = answered(with_body, ResponseFields(stream=(DONE,)))
    assert (reply.body, len(reply.stream or ())) == (b"", 1)


def test_a_plain_string_body_gets_no_content_type():
    with_text = route(response=ResponseFields(status=200, body=Body(b"not json")))
    assert answered(with_text).headers == {}
