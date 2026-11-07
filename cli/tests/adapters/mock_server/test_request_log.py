import base64
from typing import Any

from coding_study.adapters.mock_server.matching import MockRequest
from coding_study.adapters.mock_server.request_log import (
    MAX_LOG_BYTES,
    MAX_LOG_ENTRIES,
    MAX_LOGGED_BODY_BYTES,
    Outcome,
    RequestLog,
)

SERVED = Outcome(route="rooms", scenario=None, status=200)
PATH = "/v1/rooms"
BODY_OF_A_FULL_ENTRY = b"a" * (MAX_LOGGED_BODY_BYTES - len(PATH))
ENTRIES_TO_FILL_THE_BYTE_LIMIT = MAX_LOG_BYTES // MAX_LOGGED_BODY_BYTES


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def request(body: bytes = b"", **fields) -> MockRequest:
    defaults = {"method": "POST", "path": "/v1/rooms", "query": {}, "headers": {}}
    return MockRequest(body=body, **{**defaults, **fields})


def new_log(clock: FakeClock | None = None) -> RequestLog:
    return RequestLog("room-vendor", clock or FakeClock())


def entries_of(log: RequestLog) -> list[dict[str, Any]]:
    entries = log.document()["entries"]
    assert isinstance(entries, list)
    return entries


def only_entry(log: RequestLog) -> dict[str, Any]:
    return entries_of(log)[0]


def test_an_entry_records_the_request_and_its_outcome():
    log = new_log()
    log.record(
        request(
            b'{"a": 1}',
            query={"date": ("2027-03-01",)},
            headers={"accept": "application/json"},
        ),
        Outcome(route="rooms", scenario="outage", status=503),
    )
    assert only_entry(log) == {
        "seq": 1,
        "mock": "room-vendor",
        "matched": True,
        "route": "rooms",
        "scenario": "outage",
        "method": "POST",
        "path": "/v1/rooms",
        "query": {"date": "2027-03-01"},
        "headers": {"accept": "application/json"},
        "body": '{"a": 1}',
        "status": 503,
        "received_ms": 0,
        "responded_ms": None,
    }


def test_a_request_without_a_route_is_not_matched():
    log = new_log()
    log.record(request(), Outcome(route=None, scenario=None, status=404))
    assert only_entry(log)["matched"] is False


def test_an_empty_body_is_null():
    log = new_log()
    log.record(request(), SERVED)
    assert only_entry(log)["body"] is None


def test_a_repeated_query_key_keeps_every_value():
    log = new_log()
    log.record(request(query={"tag": ("a", "b")}), SERVED)
    assert only_entry(log)["query"] == {"tag": ["a", "b"]}


def test_sequence_numbers_count_requests_from_one():
    log = new_log()
    log.record(request(), SERVED)
    log.record(request(), SERVED)
    assert [entry["seq"] for entry in entries_of(log)] == [1, 2]


def test_arrival_is_monotonic_milliseconds_since_the_log_began():
    clock = FakeClock()
    log = new_log(clock)
    clock.now += 1.25
    log.record(request(), SERVED)
    assert only_entry(log)["received_ms"] == 1250


def test_an_answered_request_gets_its_response_time():
    clock = FakeClock()
    log = new_log(clock)
    entry = log.record(request(), SERVED)
    clock.now += 0.04
    log.mark_responded(entry)
    assert only_entry(log)["responded_ms"] == 40


def test_a_request_still_being_answered_is_already_in_the_log():
    log = new_log()
    log.record(request(), SERVED)
    assert only_entry(log)["responded_ms"] is None


def test_a_body_at_the_limit_is_kept_whole():
    log = new_log()
    body = b"a" * MAX_LOGGED_BODY_BYTES
    log.record(request(body), SERVED)
    entry = only_entry(log)
    assert (entry["body"], "truncated" in entry) == (body.decode(), False)


def test_a_body_past_the_limit_keeps_its_start_and_says_so():
    log = new_log()
    log.record(request(b"a" * (MAX_LOGGED_BODY_BYTES + 1)), SERVED)
    entry = only_entry(log)
    assert (entry["body"], entry["truncated"]) == ("a" * MAX_LOGGED_BODY_BYTES, True)


def test_a_cut_through_a_character_keeps_the_text_before_it():
    log = new_log()
    body = b"a" * (MAX_LOGGED_BODY_BYTES - 1) + "é".encode()
    log.record(request(body), SERVED)
    entry = only_entry(log)
    assert (entry["body"], entry["truncated"]) == ("a" * (MAX_LOGGED_BODY_BYTES - 1), True)


def test_a_body_that_is_not_text_is_kept_as_base64():
    log = new_log()
    log.record(request(b"\xff\x00"), SERVED)
    entry = only_entry(log)
    assert (entry["body"], entry["body_base64"]) == (None, base64.b64encode(b"\xff\x00").decode())


def test_a_log_below_its_limits_is_not_truncated():
    log = new_log()
    log.record(request(), SERVED)
    document = log.document()
    assert (document["truncated"], document["dropped"]) == (False, 0)


def test_a_log_at_its_entry_limit_keeps_the_first_entries_and_says_so():
    log = new_log()
    for _ in range(MAX_LOG_ENTRIES + 2):
        log.record(request(), SERVED)
    document = log.document()
    entries = entries_of(log)
    assert (len(entries), entries[-1]["seq"], document["truncated"], document["dropped"]) == (
        MAX_LOG_ENTRIES,
        MAX_LOG_ENTRIES,
        True,
        2,
    )


def test_a_log_exactly_at_its_byte_limit_keeps_the_last_entry():
    log = new_log()
    for _ in range(ENTRIES_TO_FILL_THE_BYTE_LIMIT):
        log.record(request(BODY_OF_A_FULL_ENTRY, path=PATH), SERVED)
    assert log.document()["dropped"] == 0


def test_a_log_past_its_byte_limit_stops_keeping_entries_and_says_so():
    log = new_log()
    for _ in range(ENTRIES_TO_FILL_THE_BYTE_LIMIT + 1):
        log.record(request(BODY_OF_A_FULL_ENTRY, path=PATH), SERVED)
    document = log.document()
    assert (document["truncated"], document["dropped"]) == (True, 1)


def test_large_headers_count_toward_the_byte_limit():
    log = new_log()
    large = {"x-large": "a" * MAX_LOGGED_BODY_BYTES}
    for _ in range(MAX_LOG_BYTES // MAX_LOGGED_BODY_BYTES + 1):
        log.record(request(headers=large), SERVED)
    assert log.document()["truncated"] is True


def test_a_dropped_request_has_no_entry_to_mark():
    log = new_log()
    for _ in range(MAX_LOG_ENTRIES):
        log.record(request(), SERVED)
    assert log.record(request(), SERVED) is None


def test_marking_a_dropped_request_is_harmless():
    log = new_log()
    log.mark_responded(None)
    assert log.document()["entries"] == []


def test_clearing_empties_the_log_and_its_marker():
    log = new_log()
    for _ in range(MAX_LOG_ENTRIES + 1):
        log.record(request(), SERVED)
    log.clear()
    document = log.document()
    assert (document["entries"], document["truncated"], document["dropped"]) == ([], False, 0)


def test_clearing_restarts_sequence_numbers():
    log = new_log()
    log.record(request(), SERVED)
    log.clear()
    log.record(request(), SERVED)
    assert only_entry(log)["seq"] == 1


def test_clearing_restarts_the_times():
    clock = FakeClock()
    log = new_log(clock)
    clock.now += 5
    log.clear()
    clock.now += 0.5
    log.record(request(), SERVED)
    assert only_entry(log)["received_ms"] == 500


def test_clearing_frees_the_byte_budget():
    log = new_log()
    body = b"a" * MAX_LOGGED_BODY_BYTES
    for _ in range(MAX_LOG_BYTES // MAX_LOGGED_BODY_BYTES + 1):
        log.record(request(body), SERVED)
    log.clear()
    log.record(request(), SERVED)
    assert log.document()["truncated"] is False


def test_the_document_names_its_mock_server():
    assert new_log().document()["mock"] == "room-vendor"


def test_an_answer_after_clearing_leaves_the_new_log_alone():
    clock = FakeClock()
    log = new_log(clock)
    earlier = log.record(request(), SERVED)
    log.clear()
    log.record(request(), SERVED)
    log.mark_responded(earlier)
    assert only_entry(log)["responded_ms"] is None


def test_a_query_counts_toward_the_byte_limit():
    """A request line holds up to 64 KiB, so 1,000 of them pass the container's limit alone."""
    log = new_log()
    query = {"q": ("a" * MAX_LOGGED_BODY_BYTES,)}

    for _ in range(MAX_LOG_ENTRIES):
        log.record(request(query=query), SERVED)

    assert len(entries_of(log)) <= ENTRIES_TO_FILL_THE_BYTE_LIMIT


def test_a_repeated_query_key_counts_each_value():
    log = new_log()
    query = {"q": ("a" * MAX_LOGGED_BODY_BYTES, "b" * MAX_LOGGED_BODY_BYTES)}

    for _ in range(MAX_LOG_ENTRIES):
        log.record(request(query=query), SERVED)

    assert len(entries_of(log)) <= ENTRIES_TO_FILL_THE_BYTE_LIMIT // 2
