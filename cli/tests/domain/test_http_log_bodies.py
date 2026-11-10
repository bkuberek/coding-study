"""Log assertions on what a request's JSON body carried
(docs/specs/service-projects.md#logged-bodies)."""

import json
from typing import Any

import pytest

from coding_study.domain.http_bodies import json_contains
from coding_study.domain.http_case import LogAssertion, SameBody
from coding_study.domain.http_grading import (
    CUT_JSON_BODY,
    OVERFLOWED,
    LoggedRequest,
    MockLog,
    log_failures,
)
from tests.json_subset_table import CONTAINED, NOT_CONTAINED

SYSTEM = {"role": "system", "content": "Answer briefly."}
ASK = {"role": "user", "content": "Which desks are free?"}
REPLY = {"role": "assistant", "content": "Oak and elm."}
FOLLOW_UP = {"role": "user", "content": "And tomorrow?"}


def sent(body: Any, *, route: str = "chat", truncated: bool = False) -> LoggedRequest:
    text = body if isinstance(body, str) else json.dumps(body)
    return LoggedRequest(route, 0, 1, {}, text, truncated)


def log_of(*bodies: Any) -> MockLog:
    return MockLog(tuple(sent(body) for body in bodies))


@pytest.mark.parametrize(("actual", "subset"), CONTAINED)
def test_a_value_contains_its_subset(actual: Any, subset: Any):
    assert json_contains(actual, subset)


@pytest.mark.parametrize(("actual", "subset"), NOT_CONTAINED)
def test_a_value_does_not_contain_what_differs(actual: Any, subset: Any):
    assert not json_contains(actual, subset)


def test_a_body_subset_counts_only_requests_that_hold_it():
    assertion = LogAssertion("llm", "chat", count=1, body={"stream": True})
    assert log_failures(assertion, log_of({"stream": True}, {"stream": False})) == ()


def test_a_body_subset_that_matches_no_request_names_what_it_looked_for():
    assertion = LogAssertion("llm", "chat", count=1, body={"stream": True})
    assert log_failures(assertion, log_of({"stream": False})) == (
        'llm chat with body {"stream": true}: expected 1 request, saw 0',
    )


def test_a_body_that_is_not_json_holds_no_subset():
    assertion = LogAssertion("llm", count=0, body={"stream": True})
    assert log_failures(assertion, log_of("stream=true")) == ()


def test_a_maximum_counts_requests_whose_field_is_at_most_it():
    assertion = LogAssertion("llm", "chat", count=1, body_max={"max_tokens": 256})
    assert log_failures(assertion, log_of({"max_tokens": 256}, {"max_tokens": 4096})) == ()


def test_a_maximum_that_no_request_keeps_names_it():
    assertion = LogAssertion("llm", "chat", count=1, body_max={"max_tokens": 256})
    assert log_failures(assertion, log_of({"max_tokens": 4096})) == (
        "llm chat with body max_tokens at most 256: expected 1 request, saw 0",
    )


def test_a_maximum_reads_a_dotted_path():
    assertion = LogAssertion("llm", count=1, body_max={"options.budget": 10})
    assert log_failures(assertion, log_of({"options": {"budget": 9.5}})) == ()


@pytest.mark.parametrize("body", [{}, {"max_tokens": True}, {"max_tokens": "10"}])
def test_a_maximum_counts_no_request_without_a_number_there(body: dict[str, Any]):
    assertion = LogAssertion("llm", count=0, body_max={"max_tokens": 256})
    assert log_failures(assertion, log_of(body)) == ()


PRIMARY = SameBody("llm", "chat", ("messages",))


def test_the_same_fields_as_another_request_count():
    assertion = LogAssertion("backup", "chat", count=1, body_same_as=PRIMARY)
    reference = log_of({"model": "a", "messages": [SYSTEM, ASK]})
    backup = log_of({"model": "b", "messages": [SYSTEM, ASK]})
    assert log_failures(assertion, backup, reference) == ()


def test_the_same_fields_compare_as_json_whatever_their_key_order():
    assertion = LogAssertion("backup", count=1, body_same_as=PRIMARY)
    reference = log_of({"messages": [{"role": "user", "content": "hi"}]})
    backup = log_of({"messages": [{"content": "hi", "role": "user"}]})
    assert log_failures(assertion, backup, reference) == ()


def test_other_fields_than_the_reference_requests_name_them():
    assertion = LogAssertion("backup", "chat", count=1, body_same_as=PRIMARY)
    reference = log_of({"messages": [SYSTEM, ASK]})
    assert log_failures(assertion, log_of({"messages": [ASK]}), reference) == (
        "backup chat with body messages the same as llm chat: expected 1 request, saw 0",
    )


def test_a_reference_with_no_request_says_so():
    assertion = LogAssertion("backup", count=1, body_same_as=PRIMARY)
    assert log_failures(assertion, log_of({"messages": []}), MockLog()) == (
        "backup with body messages the same as llm chat: "
        "llm chat logged no request to compare with",
    )


def test_a_reference_is_its_routes_first_request():
    assertion = LogAssertion("backup", count=1, body_same_as=PRIMARY)
    reference = MockLog(
        (sent({"messages": [ASK]}, route="other"), sent({"messages": [SYSTEM]}), sent({}))
    )
    assert log_failures(assertion, log_of({"messages": [SYSTEM]}), reference) == ()


def test_a_history_that_only_grows_is_prefix_stable():
    assertion = LogAssertion("llm", "chat", body_prefix_stable="messages")
    history = log_of(
        {"messages": [SYSTEM, ASK]},
        {"messages": [SYSTEM, ASK, REPLY, FOLLOW_UP]},
        {"messages": [SYSTEM, ASK, REPLY, FOLLOW_UP, REPLY]},
    )
    assert log_failures(assertion, history) == ()


def test_a_history_rewritten_in_place_is_not_prefix_stable():
    assertion = LogAssertion("llm", "chat", body_prefix_stable="messages")
    rewritten = {"role": "system", "content": "Answer briefly. Today is Tuesday."}
    history = log_of({"messages": [SYSTEM, ASK]}, {"messages": [rewritten, ASK, REPLY]})
    assert log_failures(assertion, history) == (
        "llm chat: body messages of request 2 does not start with request 1's: element 0 differs",
    )


def test_a_shorter_history_is_not_prefix_stable():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    history = log_of({"messages": [SYSTEM, ASK]}, {"messages": [SYSTEM]})
    assert log_failures(assertion, history) == (
        "llm: body messages of request 2 does not start with request 1's: it has fewer elements",
    )


def test_a_text_that_only_grows_is_prefix_stable():
    assertion = LogAssertion("llm", body_prefix_stable="system")
    assert (
        log_failures(assertion, log_of({"system": "Be brief."}, {"system": "Be brief. Ok."})) == ()
    )


def test_a_text_changed_at_its_start_is_not_prefix_stable():
    assertion = LogAssertion("llm", body_prefix_stable="system")
    history = log_of({"system": "Now 10:00. Be brief."}, {"system": "Now 10:01. Be brief."})
    assert log_failures(assertion, history) == (
        "llm: body system of request 2 does not start with request 1's: it differs at character 8",
    )


def test_a_request_without_the_field_breaks_the_prefix():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    assert log_failures(assertion, log_of({"messages": [ASK]}, {})) == (
        "llm: body messages of request 2 is missing",
    )


def test_a_field_that_is_neither_a_text_nor_a_list_breaks_the_prefix():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    assert log_failures(assertion, log_of({"messages": 1}, {"messages": 1})) == (
        "llm: body messages of request 1 is neither a text nor a list",
    )


def test_one_request_is_prefix_stable():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    assert log_failures(assertion, log_of({"messages": [ASK]})) == ()


def test_prefix_stability_covers_only_the_requests_that_count():
    assertion = LogAssertion("llm", "chat", body={"stream": True}, body_prefix_stable="messages")
    history = log_of(
        {"stream": True, "messages": [ASK]},
        {"stream": False, "messages": [REPLY]},
        {"stream": True, "messages": [ASK, REPLY]},
    )
    assert log_failures(assertion, history) == ()


def test_a_body_assertion_over_a_body_cut_at_the_logs_limit_cannot_be_judged():
    assertion = LogAssertion("llm", "chat", min_count=1, body={"stream": True})
    log = MockLog((sent('{"stream": true, "messages": [', truncated=True),))
    assert log_failures(assertion, log) == (
        f'llm chat with body {{"stream": true}}: {CUT_JSON_BODY}',
    )


def test_prefix_stability_over_a_body_cut_at_the_logs_limit_cannot_be_judged():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    log = MockLog((sent('{"messages": [', truncated=True),))
    assert log_failures(assertion, log) == (f"llm: {CUT_JSON_BODY}",)


def test_prefix_stability_over_an_overflowed_log_cannot_be_judged():
    assertion = LogAssertion("llm", body_prefix_stable="messages")
    assert log_failures(assertion, MockLog((), dropped=2)) == (f"llm: {OVERFLOWED}",)
