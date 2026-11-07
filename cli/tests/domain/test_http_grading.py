import json
from typing import Any

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Expected
from coding_study.domain.http_case import (
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    LogAssertion,
)
from coding_study.domain.http_grading import (
    MAX_DIFFERENCES,
    OVERFLOWED,
    Answer,
    HttpResponse,
    LoggedRequest,
    MockLog,
    answered_verdict,
    before_failure,
    log_failures,
    response_failures,
)
from coding_study.domain.judging import RunnableCase
from coding_study.domain.problem import ComparatorSpec, ComparatorType
from coding_study.domain.runs import Returned

EXACT = ComparatorSpec(ComparatorType.EXACT)
UNORDERED = ComparatorSpec(ComparatorType.UNORDERED)
NESTED = ComparatorSpec(ComparatorType.UNORDERED_NESTED)
ROOM_VENDOR = "room-vendor"
AVAILABILITY = "availability"
LONG_ENOUGH_TO_BE_CUT = 500
"""Reports cut a value at 200 characters, so this difference lies past the cut."""


def response(body: Any = None, status: int = 200) -> HttpResponse:
    return HttpResponse(status, {}, json.dumps(body).encode())


def text_response(text: str, status: int = 200) -> HttpResponse:
    return HttpResponse(status, {}, text.encode())


def with_headers(headers: dict[str, str]) -> HttpResponse:
    return HttpResponse(200, headers, b"")


def body_failures(
    expected: Any, actual: HttpResponse, spec: ComparatorSpec = EXACT
) -> tuple[str, ...]:
    return response_failures(actual, HttpExpected(200, Expected(expected)), spec)


def logged(received_ms: int, responded_ms: int | None, route: str = AVAILABILITY) -> LoggedRequest:
    return LoggedRequest(route, received_ms, responded_ms)


def http_input(expected: HttpExpected, log: tuple[LogAssertion, ...] = ()) -> HttpCaseInput:
    return HttpCaseInput({}, request=HttpRequest("GET", "/a"), expected=expected, log=log)


def runnable(http: HttpCaseInput) -> RunnableCase:
    return RunnableCase("h1", http, Expected({"status": http.expected.status}))


def test_a_matching_status_with_no_expected_body_passes():
    assert response_failures(text_response("anything"), HttpExpected(200), EXACT) == ()


def test_a_wrong_status_says_both():
    assert response_failures(response(status=503), HttpExpected(200), EXACT) == (
        "status: expected 200, got 503",
    )


def test_a_wrong_status_leaves_out_the_noise_of_the_error_body():
    expected = HttpExpected(200, Expected({"available": 12}))
    failures = response_failures(response({"error": "boom"}, status=500), expected, EXACT)
    assert failures == ("status: expected 200, got 500",)


def test_json_is_compared_parsed_so_key_order_cannot_fail():
    actual = HttpResponse(200, {}, b'{"b": 2,  "a": 1}')
    assert body_failures({"a": 1, "b": 2}, actual) == ()


def test_whitespace_in_json_cannot_fail():
    actual = HttpResponse(200, {}, b"  [1,\n 2]\n")
    assert body_failures([1, 2], actual) == ()


def test_an_integer_and_the_same_float_are_equal():
    assert body_failures({"n": 1}, response({"n": 1.0})) == ()


def test_true_is_not_one():
    assert body_failures({"n": 1}, response({"n": True})) == ("body.n: expected 1, got true",)


def test_a_field_the_case_does_not_expect_fails_and_is_named():
    failures = body_failures({"a": 1}, response({"a": 1, "extra": 2}))
    assert failures == ("body.extra: unexpected field, with value 2",)


def test_a_missing_field_fails_and_is_named():
    failures = body_failures({"a": 1, "b": {"c": 2}}, response({"a": 1}))
    assert failures == ('body.b: missing, expected {"c": 2}',)


def test_a_difference_is_named_by_its_path():
    expected = {"rooms": [{"room": "oak", "slots": ["09:00", "10:00"]}]}
    actual = response({"rooms": [{"room": "oak", "slots": ["09:00", "11:00"]}]})
    assert body_failures(expected, actual) == (
        'body.rooms[0].slots[1]: expected "10:00", got "11:00"',
    )


def test_a_wrong_length_says_both_lengths():
    assert body_failures([1, 2, 3], response([1, 2])) == ("body: expected 3 elements, got 2",)


def test_different_shapes_say_what_came_back():
    assert body_failures([1], response({"a": 1})) == ('body: expected [1], got {"a": 1}',)


def test_a_body_root_that_differs_names_the_body():
    assert body_failures(1, response(2)) == ("body: expected 1, got 2",)


def test_a_difference_past_the_report_cut_is_still_shown():
    rooms = [f"room-{index}" for index in range(LONG_ENOUGH_TO_BE_CUT)]
    changed = [*rooms[:-1], "moved"]
    assert body_failures(rooms, response(changed)) == (
        f'body[{LONG_ENOUGH_TO_BE_CUT - 1}]: expected "room-{LONG_ENOUGH_TO_BE_CUT - 1}", '
        'got "moved"',
    )


def test_a_long_string_shows_the_part_that_differs():
    same = "x" * LONG_ENOUGH_TO_BE_CUT
    failures = body_failures({"text": same + "WANTED"}, response({"text": same + "SENT"}))
    assert failures[0].endswith(
        'expected "...' + "x" * 40 + 'WANTED", got "...' + "x" * 40 + 'SENT"'
    )


def test_a_long_string_says_where_it_differs():
    same = "x" * LONG_ENOUGH_TO_BE_CUT
    failures = body_failures(same + "a", text_response(same + "b"))
    assert failures[0].startswith(f"body: differs at character {LONG_ENOUGH_TO_BE_CUT}:")


def test_differences_are_listed_up_to_a_limit():
    size = MAX_DIFFERENCES + 2
    failures = body_failures(list(range(size)), response([-1] * size))
    assert len(failures) == MAX_DIFFERENCES + 1


def test_differences_past_the_limit_are_mentioned():
    size = MAX_DIFFERENCES + 2
    failures = body_failures(list(range(size)), response([-1] * size))
    assert failures[-1] == "and more differences in the body"


def test_exactly_the_limit_mentions_nothing_more():
    failures = body_failures(list(range(MAX_DIFFERENCES)), response([-1] * MAX_DIFFERENCES))
    assert len(failures) == MAX_DIFFERENCES


def test_a_float_within_the_tolerance_passes():
    spec = ComparatorSpec(ComparatorType.FLOAT, 0.01)
    assert body_failures({"rate": 2.0}, response({"rate": 2.01}), spec) == ()


def test_a_float_past_the_tolerance_fails():
    spec = ComparatorSpec(ComparatorType.FLOAT, 0.01)
    failures = body_failures({"rate": 2.0}, response({"rate": 2.1}), spec)
    assert failures == ("body.rate: expected 2.0, got 2.1",)


def test_exact_has_no_tolerance():
    failures = body_failures({"rate": 2.0}, response({"rate": 2.0000001}))
    assert failures == ("body.rate: expected 2.0, got 2.0000001",)


def test_unordered_accepts_another_order():
    assert body_failures([1, 2, 3], response([3, 1, 2]), UNORDERED) == ()


def test_unordered_counts_repeats():
    assert body_failures([1, 1, 2], response([1, 2, 2]), UNORDERED) == (
        "body: missing element 1",
        "body: unexpected element 2",
    )


def test_unordered_names_what_is_missing_and_what_is_not_expected():
    failures = body_failures([{"room": "oak"}], response([{"room": "elm"}]), UNORDERED)
    assert failures == (
        'body: missing element {"room": "oak"}',
        'body: unexpected element {"room": "elm"}',
    )


def test_unordered_needs_an_array():
    assert body_failures([1], response({"a": 1}), UNORDERED) == (
        'body: expected an array, got {"a": 1}',
    )


def test_unordered_nested_accepts_inner_arrays_in_another_order():
    assert body_failures([[1, 2], [3]], response([[3], [2, 1]]), NESTED) == ()


def test_unordered_nested_names_an_inner_array_that_differs():
    assert body_failures([[1, 2]], response([[1, 3]]), NESTED) == (
        "body: missing element [1, 2]",
        "body: unexpected element [1, 3]",
    )


def test_expected_json_with_text_back_says_it_did_not_parse():
    failures = body_failures({"a": 1}, text_response('{"rooms": ['))
    assert failures[0].startswith("body: expected JSON, and this does not parse")


def test_not_a_number_is_not_json():
    failures = body_failures({"a": 1}, text_response('{"a": NaN}'))
    assert failures[0].startswith("body: expected JSON, and this does not parse")


def test_expected_json_with_an_empty_body_says_it_is_empty():
    assert body_failures({"a": 1}, text_response("")) == ("body: expected JSON, got an empty body",)


def test_a_json_null_is_compared_as_a_value():
    assert body_failures(None, text_response("null")) == ()


def test_a_string_body_is_exact_text():
    assert body_failures("hello", text_response("hello")) == ()


def test_a_string_body_is_not_json_decoded():
    assert body_failures("hello", text_response('"hello"')) == (
        'body: expected "hello", got "\\"hello\\""',
    )


def test_a_body_that_is_not_utf8_is_shown_rather_than_raising():
    failures = body_failures("hello", HttpResponse(200, {}, b"\xff\xfe"))
    assert failures[0].startswith("body: expected")


def test_a_listed_header_must_match():
    expected = HttpExpected(200, headers={"X-Trace": "1"})
    failures = response_failures(with_headers({"x-trace": "2"}), expected, EXACT)
    assert failures == ('header X-Trace: expected "1", got "2"',)


def test_a_header_name_matches_in_any_case():
    expected = HttpExpected(200, headers={"X-TRACE": "1"})
    assert response_failures(with_headers({"x-trace": "1"}), expected, EXACT) == ()


def test_a_missing_header_says_so():
    expected = HttpExpected(200, headers={"X-Trace": "1"})
    assert response_failures(response(), expected, EXACT) == (
        'header X-Trace: expected "1", and it is missing',
    )


def test_a_charset_cannot_fail_a_listed_content_type():
    expected = HttpExpected(200, headers={"Content-Type": "application/json"})
    actual = with_headers({"content-type": "application/json; charset=utf-8"})
    assert response_failures(actual, expected, EXACT) == ()


def test_a_content_type_is_compared_in_any_case():
    expected = HttpExpected(200, headers={"Content-Type": "application/json"})
    actual = with_headers({"content-type": "Application/JSON"})
    assert response_failures(actual, expected, EXACT) == ()


def test_another_content_type_fails():
    expected = HttpExpected(200, headers={"Content-Type": "application/json"})
    actual = with_headers({"content-type": "text/plain"})
    assert response_failures(actual, expected, EXACT) == (
        'header Content-Type: expected "application/json", got "text/plain"',
    )


def test_a_content_type_with_its_own_parameter_is_compared_whole():
    expected = HttpExpected(200, headers={"Content-Type": "text/plain; charset=utf-8"})
    actual = with_headers({"content-type": "text/plain"})
    assert response_failures(actual, expected, EXACT) != ()


def test_a_count_that_differs_uses_the_specs_wording():
    log = MockLog(tuple(logged(index, index) for index in range(5)))
    assertion = LogAssertion(ROOM_VENDOR, AVAILABILITY, count=2)
    assert log_failures(assertion, log) == ("room-vendor availability: expected 2 requests, saw 5",)


def test_one_request_is_singular():
    assertion = LogAssertion(ROOM_VENDOR, AVAILABILITY, count=1)
    assert log_failures(assertion, MockLog()) == (
        "room-vendor availability: expected 1 request, saw 0",
    )


def test_a_matching_count_passes():
    log = MockLog((logged(0, 1), logged(2, 3)))
    assert log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, count=2), log) == ()


def test_a_count_covers_only_its_route():
    log = MockLog((logged(0, 1), logged(2, 3, route="slots")))
    assert log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, count=1), log) == ()


def test_without_a_route_a_count_covers_the_whole_mock_server():
    log = MockLog((logged(0, 1), LoggedRequest(None, 2, 3)))
    assert log_failures(LogAssertion(ROOM_VENDOR, count=1), log) == (
        "room-vendor: expected 1 request, saw 2",
    )


def test_requests_the_log_dropped_still_count_for_the_whole_mock_server():
    log = MockLog((logged(0, 1),), dropped=4)
    assert log_failures(LogAssertion(ROOM_VENDOR, max_count=3), log) == (
        "room-vendor: expected at most 3 requests, saw 5",
    )


def test_a_dropped_request_is_no_request_of_a_route():
    """`dropped` counts every route, so adding it to one route's count made zero calls pass."""
    failures = log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, count=1), MockLog(dropped=1))

    assert failures == (f"room-vendor availability: {OVERFLOWED}",)


def test_a_route_cannot_be_counted_on_an_overflowed_log():
    log = MockLog((logged(0, 1),), dropped=4)
    failures = log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, min_count=1), log)

    assert failures == (f"room-vendor availability: {OVERFLOWED}",)


def test_a_gap_cannot_be_judged_on_an_overflowed_log():
    """What overflowed is what came last: a retry too soon may be just what the log did not keep."""
    log = MockLog((logged(0, 1), logged(1000, 1001)), dropped=1)
    failures = log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=950), log)

    assert failures == (f"room-vendor: {OVERFLOWED}",)


def test_a_route_with_a_gap_on_an_overflowed_log_says_so_once():
    log = MockLog((logged(0, 1),), dropped=1)
    failures = log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, count=1, min_gap_ms=950), log)

    assert failures == (f"room-vendor availability: {OVERFLOWED}",)


def test_a_count_of_the_whole_mock_server_can_pass_on_an_overflowed_log():
    log = MockLog((logged(0, 1),), dropped=4)

    assert log_failures(LogAssertion(ROOM_VENDOR, count=5), log) == ()


def test_too_few_for_a_minimum_fails():
    assert log_failures(LogAssertion(ROOM_VENDOR, min_count=1), MockLog()) == (
        "room-vendor: expected at least 1 request, saw 0",
    )


def test_exactly_the_minimum_passes():
    assert log_failures(LogAssertion(ROOM_VENDOR, min_count=1), MockLog((logged(0, 1),))) == ()


def test_exactly_the_maximum_passes():
    assert log_failures(LogAssertion(ROOM_VENDOR, max_count=1), MockLog((logged(0, 1),))) == ()


def test_a_gap_is_measured_from_the_response_to_the_next_request():
    log = MockLog((logged(0, 100), logged(1049, 1050)))
    assert log_failures(LogAssertion(ROOM_VENDOR, AVAILABILITY, min_gap_ms=950), log) == (
        "room-vendor availability: expected at least 950 ms from response 1 to request 2, "
        "saw 949 ms",
    )


def test_exactly_the_minimum_gap_passes():
    log = MockLog((logged(0, 100), logged(1050, 1051)))
    assert log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=950), log) == ()


def test_a_later_gap_is_checked_too():
    log = MockLog((logged(0, 1), logged(100, 101), logged(102, 103)))
    assert log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=50), log) == (
        "room-vendor: expected at least 50 ms from response 2 to request 3, saw 1 ms",
    )


def test_a_request_during_the_previous_one_has_no_gap_at_all():
    log = MockLog((logged(0, None), logged(1, 2)))
    assert log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=950), log) == (
        "room-vendor: expected at least 950 ms from response 1 to request 2, "
        "but request 2 came before response 1",
    )


def test_a_request_still_in_flight_at_the_end_breaks_no_gap():
    log = MockLog((logged(0, 10), logged(1000, None)))
    assert log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=950), log) == ()


def test_clock_rounding_never_shows_a_negative_gap():
    log = MockLog((logged(0, 11), logged(10, 12)))
    assert log_failures(LogAssertion(ROOM_VENDOR, min_gap_ms=5), log) == (
        "room-vendor: expected at least 5 ms from response 1 to request 2, saw 0 ms",
    )


def test_one_assertion_reports_each_thing_it_found():
    log = MockLog((logged(0, 1), logged(2, 3), logged(4, 5)))
    assert len(log_failures(LogAssertion(ROOM_VENDOR, count=2, min_gap_ms=950), log)) == 2


def test_an_answer_that_matches_passes():
    http = http_input(HttpExpected(200, Expected({"a": 1})))
    verdict = answered_verdict(runnable(http), http, Answer(response({"a": 1}), EXACT, {}))
    assert verdict.status is CaseStatus.PASS


def test_an_answer_shows_the_status_and_the_parsed_body():
    http = http_input(HttpExpected(200))
    answer = HttpResponse(200, {}, b'{"b": 1}', duration_ns=7)
    verdict = answered_verdict(runnable(http), http, Answer(answer, EXACT, {}))
    assert verdict.outcome == Returned({"status": 200, "body": {"b": 1}}, 7)


def test_an_answer_that_is_not_json_shows_its_text():
    http = http_input(HttpExpected(200))
    verdict = answered_verdict(runnable(http), http, Answer(text_response("hi"), EXACT, {}))
    assert verdict.outcome == Returned({"status": 200, "body": "hi"}, 0)


def test_a_string_expectation_shows_the_text_even_if_it_parses():
    http = http_input(HttpExpected(200, Expected("1")))
    verdict = answered_verdict(runnable(http), http, Answer(text_response("1"), EXACT, {}))
    assert verdict.outcome == Returned({"status": 200, "body": "1"}, 0)


def test_an_answer_shows_only_the_headers_the_case_lists():
    http = http_input(HttpExpected(200, headers={"X-Trace": "1"}))
    answer = HttpResponse(200, {"x-trace": "1", "x-other": "2"}, b"")
    verdict = answered_verdict(runnable(http), http, Answer(answer, EXACT, {}))
    assert verdict.outcome == Returned(
        {"status": 200, "body": "", "headers": {"X-Trace": "1"}},
        0,
    )


def test_a_wrong_answer_fails_with_its_difference():
    http = http_input(HttpExpected(200, Expected({"a": 1})))
    verdict = answered_verdict(runnable(http), http, Answer(response({"a": 2}), EXACT, {}))
    assert (verdict.status, verdict.mismatch and verdict.mismatch.detail) == (
        CaseStatus.FAIL,
        "body.a: expected 1, got 2",
    )


def test_a_right_body_with_a_wrong_log_fails_on_the_log():
    assertion = LogAssertion(ROOM_VENDOR, AVAILABILITY, count=2)
    http = http_input(HttpExpected(200), (assertion,))
    answer = Answer(response(), EXACT, {ROOM_VENDOR: MockLog()})
    verdict = answered_verdict(runnable(http), http, answer)
    assert (verdict.status, verdict.mismatch and verdict.mismatch.detail) == (
        CaseStatus.FAIL,
        "room-vendor availability: expected 2 requests, saw 0",
    )


def test_a_wrong_status_and_a_wrong_log_are_both_reported():
    http = http_input(HttpExpected(200), (LogAssertion(ROOM_VENDOR, count=1),))
    answer = Answer(response(status=500), EXACT, {ROOM_VENDOR: MockLog()})
    verdict = answered_verdict(runnable(http), http, answer)
    assert verdict.mismatch is not None
    assert verdict.mismatch.detail == (
        "status: expected 200, got 500; room-vendor: expected 1 request, saw 0"
    )


def test_a_before_request_answering_2xx_is_no_failure():
    assert before_failure(0, HttpRequest("POST", "/seed"), response(status=201)) is None


def test_a_before_request_answering_otherwise_names_itself():
    failure = before_failure(1, HttpRequest("POST", "/seed"), response(status=500))
    assert failure == "before[1] POST /seed: expected a 2xx status, got 500"
