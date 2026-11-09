"""Judging the answers to requests sent at once (docs/specs/service-projects.md#parallel-cases)."""

import json

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Expected
from coding_study.domain.http_case import HttpCaseInput, HttpExpected, HttpRequest, ParallelBurst
from coding_study.domain.http_grading import Answer, HttpResponse
from coding_study.domain.http_parallel import BurstAnswer, burst_verdict, statuses_failures
from coding_study.domain.judging import RunnableCase
from coding_study.domain.runs import Returned

TEN_RESERVATIONS = (201, 409, 201, 409, 409, 201, 409, 409, 409, 409)
CASE = RunnableCase("h1", HttpCaseInput({}), None)


def test_the_right_count_of_each_status_passes_in_any_order():
    assert statuses_failures({201: 3, 409: 7}, TEN_RESERVATIONS) == ()


def test_too_many_successes_say_both_counts():
    oversold = (201,) * 5 + (409,) * 5

    assert statuses_failures({201: 3, 409: 7}, oversold) == (
        "10 requests at once: expected 3 to answer 201 and 7 to answer 409; "
        "5 answered 201 and 5 answered 409",
    )


def test_a_status_no_count_names_fails_and_is_shown():
    found = statuses_failures({201: 1, 409: 1}, (201, 500))

    assert found == (
        "2 requests at once: expected 1 to answer 201 and 1 to answer 409; "
        "1 answered 201 and 1 answered 500",
    )


def test_a_class_holds_every_status_of_its_hundred():
    assert statuses_failures({201: 1, "4xx": 2}, (409, 201, 422)) == ()


def test_an_exact_status_counts_before_its_class():
    assert statuses_failures({409: 1, "4xx": 1}, (409, 422)) == ()


def test_a_class_with_too_few_answers_fails():
    assert statuses_failures({"2xx": 2}, (200, 503)) != ()


def test_statuses_are_shown_in_order():
    found = statuses_failures({409: 1, 201: 1}, (409, 409))

    assert found[0].endswith("expected 1 to answer 201 and 1 to answer 409; 2 answered 409")


def burst(*statuses: int, after: Answer | None = None) -> BurstAnswer:
    return BurstAnswer(statuses, after, duration_ns=7)


def test_a_burst_with_no_failure_passes():
    assert burst_verdict(CASE, burst(201, 409), ()).status is CaseStatus.PASS


def test_a_burst_with_a_failure_fails_with_every_reason():
    verdict = burst_verdict(CASE, burst(201, 201), ("one", "two"))

    assert (verdict.status, verdict.mismatch and verdict.mismatch.detail) == (
        CaseStatus.FAIL,
        "one; two",
    )


def test_a_burst_shows_how_many_answered_each_status():
    verdict = burst_verdict(CASE, burst(409, 201, 409), ())

    assert verdict.outcome == Returned({"statuses": {"201": 1, "409": 2}}, 7)


def test_a_burst_shows_the_state_its_after_request_found():
    stock = HttpResponse(200, {}, json.dumps({"stock": -2}).encode(), 3)
    after = Answer(stock, HttpExpected(200, Expected({"stock": 0})))

    verdict = burst_verdict(CASE, burst(201, after=after), ())

    assert verdict.outcome == Returned(
        {"statuses": {"201": 1}, "after": {"status": 200, "body": {"stock": -2}}}, 7
    )


def test_a_parallel_case_runs_once_unless_it_repeats():
    single = HttpCaseInput({}, parallel=ParallelBurst((HttpRequest("POST", "/r"),) * 2, {201: 2}))

    assert (single.runs, HttpCaseInput({}).runs) == (1, 1)


def test_a_repeated_parallel_case_runs_that_many_times():
    burst_input = ParallelBurst((HttpRequest("POST", "/r"),) * 2, {201: 2}, repeat=3)

    assert HttpCaseInput({}, parallel=burst_input).runs == 3
