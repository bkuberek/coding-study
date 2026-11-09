"""A parallel case from its entry in tests.json (docs/specs/service-projects.md#parallel-cases)."""

import json
from typing import Any

from coding_study.adapters.http_grader.case_document import http_case_input
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.domain.cases import Expected
from coding_study.domain.http_case import HttpExpected, HttpRequest, HttpStep, ParallelBurst
from coding_study.domain.problem import ComparatorSpec, ComparatorType


def document(**fields: Any) -> dict[str, Any]:
    case = {
        "id": "h21",
        "level": 2,
        "parallel": {
            "count": 3,
            "request": {"method": "POST", "path": "/reservations", "json": {"order": "o{i}"}},
        },
        "expected_statuses": {"201": 1, "409": 2},
    }
    return case | fields


def burst_of(case: dict[str, Any]) -> ParallelBurst:
    parsed = http_case_input(case).parallel
    assert parsed is not None
    return parsed


def test_each_request_gets_its_index_from_0():
    bodies = [json.loads(request.body or b"") for request in burst_of(document()).requests]

    assert bodies == [{"order": "o0"}, {"order": "o1"}, {"order": "o2"}]


def test_the_index_fills_the_path_query_and_headers_too():
    request = {
        "method": "GET",
        "path": "/carts/c{i}",
        "query": {"member": "m{i}"},
        "headers": {"Idempotency-Key": "k{i}"},
    }
    case = document(parallel={"count": 2, "request": request})

    second = burst_of(case).requests[1]

    assert (second.path, second.query, second.headers) == (
        "/carts/c1",
        {"member": "m1"},
        {"Idempotency-Key": "k1"},
    )


def test_several_requests_take_turns_in_the_burst():
    first = {"method": "POST", "path": "/a", "json": {"order": "a{i}"}}
    second = {"method": "POST", "path": "/b", "json": {"order": "b{i}"}}
    case = document(parallel={"count": 3, "requests": [first, second]})

    sent = [(request.path, request.body) for request in burst_of(case).requests]

    assert sent == [
        ("/a", b'{"order": "a0"}'),
        ("/b", b'{"order": "b1"}'),
        ("/a", b'{"order": "a2"}'),
    ]


def test_a_status_is_a_number_and_a_class_stays_a_class():
    case = document(expected_statuses={"201": 1, "4xx": 2})

    assert burst_of(case).statuses == {201: 1, "4xx": 2}


def test_the_after_request_is_a_step_with_what_it_expects():
    after = {
        "request": {"method": "GET", "path": "/stock"},
        "expected": {"status": 200, "body": {"stock": 0}},
    }

    parsed = burst_of(document(after=after)).after

    assert parsed == HttpStep(
        "after GET /stock", HttpRequest("GET", "/stock"), HttpExpected(200, Expected({"stock": 0}))
    )


def test_a_case_runs_once_unless_it_repeats():
    assert (burst_of(document()).repeat, burst_of(document(repeat=3)).repeat) == (1, 3)


def test_before_requests_and_a_fresh_start_are_read_as_for_a_single_request():
    seed = {"method": "POST", "path": "/seed"}

    parsed = http_case_input(document(before=[seed], fresh=True))

    assert (parsed.before, parsed.fresh) == ((HttpRequest("POST", "/seed"),), True)


def test_a_parallel_case_expects_its_counts_and_its_after_answer_as_a_report_shows_them():
    after = {"request": {"method": "GET", "path": "/stock"}, "expected": {"status": 200}}
    document_ = {"version": 1, "cases": [document(after=after)]}

    case = cases_from_document(document_, ComparatorSpec(ComparatorType.EXACT), "tests.json")[0]

    assert case.expected == Expected({"statuses": {"201": 1, "409": 2}, "after": {"status": 200}})


def test_a_parallel_case_with_no_after_request_expects_its_counts():
    document_ = {"version": 1, "cases": [document()]}

    case = cases_from_document(document_, ComparatorSpec(ComparatorType.EXACT), "tests.json")[0]

    assert case.expected == Expected({"statuses": {"201": 1, "409": 2}})


def test_a_report_shows_the_burst_as_written():
    parsed = http_case_input(document())

    assert parsed.arguments == {"parallel": document()["parallel"]}
