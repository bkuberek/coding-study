from typing import Any

from coding_study.adapters.http_grader.case_document import http_case_input
from coding_study.domain.cases import Expected
from coding_study.domain.http_case import HttpExpected, HttpRequest, LogAssertion, SameBody
from coding_study.domain.problem import ComparatorSpec, ComparatorType


def document(**fields: Any) -> dict[str, Any]:
    case = {
        "id": "h1",
        "level": 1,
        "request": {"method": "GET", "path": "/availability"},
        "expected": {"status": 200},
    }
    return case | fields


def request_of(**fields: Any) -> HttpRequest:
    request = http_case_input(document(request={"method": "POST", "path": "/bookings"} | fields))
    assert request.request is not None
    return request.request


def expected_of(case: dict[str, Any]) -> HttpExpected:
    expected = http_case_input(case).expected
    assert expected is not None
    return expected


def test_the_smallest_case_has_a_request_and_a_status():
    parsed = http_case_input(document())
    assert (parsed.request, parsed.expected) == (
        HttpRequest("GET", "/availability"),
        HttpExpected(200),
    )


def test_a_query_keeps_its_values_and_repeats():
    query = {"date": "2027-03-01", "room": ["oak", "elm"]}
    assert request_of(query=query).query == {"date": "2027-03-01", "room": ("oak", "elm")}


def test_headers_are_sent_as_written():
    assert request_of(headers={"X-Member": "m1"}).headers == {"X-Member": "m1"}


def test_a_json_field_is_encoded_and_says_so():
    request = request_of(json={"member": "m1"})
    assert (request.body, request.headers) == (
        b'{"member": "m1"}',
        {"Content-Type": "application/json"},
    )


def test_a_json_null_is_still_a_body():
    assert request_of(json=None).body == b"null"


def test_a_header_the_case_names_wins_over_the_json_default():
    request = request_of(json={}, headers={"content-type": "application/vnd.api+json"})
    assert request.headers == {"content-type": "application/vnd.api+json"}


def test_a_malformed_body_goes_out_byte_for_byte():
    request = request_of(body='{"member": ', headers={"Content-Type": "application/json"})
    assert request.body == b'{"member": '


def test_a_body_with_no_content_type_stays_without_one():
    assert request_of(body="plain").headers == {}


def test_an_expected_body_may_be_null():
    assert expected_of(document(expected={"status": 200, "body": None})).body == Expected(None)


def test_no_expected_body_means_any_body():
    assert expected_of(document()).body is None


def test_an_expected_first_byte_limit_is_kept():
    expected = expected_of(document(expected={"status": 200, "first_byte_ms_max": 500}))
    assert expected.first_byte_ms_max == 500


def test_no_first_byte_limit_means_any_time_will_do():
    assert expected_of(document()).first_byte_ms_max is None


def test_expected_headers_are_kept():
    expected = expected_of(document(expected={"status": 200, "headers": {"X-Trace": "1"}}))
    assert expected.headers == {"X-Trace": "1"}


def test_mocks_name_a_scenario_each():
    parsed = http_case_input(document(mocks={"room-vendor": "outage"}))
    assert parsed.mocks == {"room-vendor": "outage"}


def test_a_case_may_override_the_comparator():
    parsed = http_case_input(document(comparator={"type": "unordered"}))
    assert parsed.comparator == ComparatorSpec(ComparatorType.UNORDERED)


def test_a_case_may_set_a_float_tolerance():
    parsed = http_case_input(document(comparator={"type": "float", "tolerance": 0.01}))
    assert parsed.comparator == ComparatorSpec(ComparatorType.FLOAT, 0.01)


def test_a_log_assertion_needs_only_its_mock():
    parsed = http_case_input(document(log=[{"mock": "room-vendor", "max_count": 3}]))
    assert parsed.log == (LogAssertion("room-vendor", max_count=3),)


def test_a_log_assertion_reads_every_field():
    entry = {
        "mock": "room-vendor",
        "route": "availability",
        "count": 2,
        "min_count": 1,
        "max_count": 3,
        "min_gap_ms": 950,
    }
    parsed = http_case_input(document(log=[entry]))
    assert parsed.log == (LogAssertion("room-vendor", "availability", 2, 1, 3, 950),)


def test_a_log_assertion_reads_its_body_fields():
    entry = {
        "mock": "backup",
        "route": "chat",
        "count": 1,
        "body": {"stream": True},
        "body_max": {"max_tokens": 256},
        "body_same_as": {"mock": "primary", "route": "chat", "fields": ["messages"]},
        "body_prefix_stable": "messages",
    }
    (assertion,) = http_case_input(document(log=[entry])).log
    assert assertion == LogAssertion(
        "backup",
        "chat",
        count=1,
        body={"stream": True},
        body_max={"max_tokens": 256},
        body_same_as=SameBody("primary", "chat", ("messages",)),
        body_prefix_stable="messages",
    )


def test_a_same_body_reference_may_name_no_route():
    entry = {"mock": "backup", "count": 1, "body_same_as": {"mock": "primary", "fields": ["a.b"]}}
    (assertion,) = http_case_input(document(log=[entry])).log
    assert assertion.body_same_as == SameBody("primary", None, ("a.b",))


def test_before_requests_are_requests():
    before = [{"method": "POST", "path": "/seed"}]
    assert http_case_input(document(before=before)).before == (HttpRequest("POST", "/seed"),)


def test_a_case_is_not_fresh_unless_it_says_so():
    assert http_case_input(document()).fresh is False


def test_a_fresh_case_says_so():
    assert http_case_input(document(fresh=True)).fresh is True


def test_reports_show_the_request_as_written():
    request = {"method": "GET", "path": "/a", "query": {"date": "2027-03-01"}}
    assert http_case_input(document(request=request)).arguments == request


def test_reports_also_show_the_scenarios_a_case_set():
    parsed = http_case_input(document(mocks={"room-vendor": "outage"}))
    assert parsed.arguments == {
        "method": "GET",
        "path": "/availability",
        "mocks": {"room-vendor": "outage"},
    }
