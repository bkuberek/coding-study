"""A parallel case through the HTTP grader, on a fake stack
(docs/specs/service-projects.md#parallel-cases)."""

import json
from typing import Any

from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected
from coding_study.domain.config import Config
from coding_study.domain.http_case import (
    BEFORE_EXPECTED,
    ExpectedStatus,
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    HttpStep,
    ParallelBurst,
)
from coding_study.domain.http_grading import ExchangeFailed, ExchangeFailure, HttpResponse
from coding_study.domain.judging import CaseVerdict
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from coding_study.domain.runs import TimedOut
from tests.application.http_grading_fakes import Rig, Sent
from tests.project_builders import project_meta

RESERVE = HttpRequest("POST", "/reservations")
STOCK = HttpRequest("GET", "/stock")
LIMIT_MS = 1_000
MILLISECOND_NS = 1_000_000
CREATED = HttpResponse(201, {}, b"{}", 10 * MILLISECOND_NS)
CONFLICT = HttpResponse(409, {}, b"{}", 30 * MILLISECOND_NS)
EMPTY_STOCK = HttpResponse(200, {}, json.dumps({"stock": 0}).encode())
OVERSOLD = HttpResponse(200, {}, json.dumps({"stock": -1}).encode())
AFTER = HttpStep("after GET /stock", STOCK, HttpExpected(200, Expected({"stock": 0})))


def parallel_case(statuses: dict[ExpectedStatus, int] | None = None, **fields: Any) -> Case:
    """Three requests for the last two items, then the stock, unless `fields` say otherwise."""
    burst = ParallelBurst(
        requests=(RESERVE,) * 3,
        statuses=statuses or {201: 2, 409: 1},
        after=fields.pop("after", AFTER),
        repeat=fields.pop("repeat", 1),
    )
    return Case(
        "h1", HttpCaseInput({}, parallel=burst, **fields), None, level=1, hang_guard_ms=LIMIT_MS
    )


def grade(rig: Rig, case: Case) -> CaseVerdict:
    meta = project_meta(comparator=ComparatorSpec(ComparatorType.EXACT))
    run = HttpGradingRun(Problem(meta, (case,)), 1, Config())
    return run_http_grading(run, rig.stack, rig.open_clients).verdicts[0]


def rig_answering(*bursts: tuple[Sent, ...], stock: HttpResponse = EMPTY_STOCK) -> Rig:
    rig = Rig()
    rig.app.bursts.extend(bursts)
    rig.app.answers[STOCK.target] = stock
    return rig


def reason_of(verdict: CaseVerdict) -> str | None:
    return verdict.mismatch.detail if verdict.mismatch else None


def test_a_parallel_case_sends_its_before_requests_then_the_burst_then_its_after_request():
    rig = rig_answering((CREATED, CREATED, CONFLICT))
    seed = HttpRequest("POST", "/seed")

    grade(rig, parallel_case(before=(seed,)))

    assert rig.journal == ["mocks reset", "send POST /seed", "send 3 at once", "send GET /stock"]


def test_the_right_counts_and_state_pass():
    rig = rig_answering((CREATED, CONFLICT, CREATED))

    assert grade(rig, parallel_case()).status is CaseStatus.PASS


def test_an_oversold_burst_fails_on_its_counts_and_on_the_state_it_left():
    rig = rig_answering((CREATED, CREATED, CREATED), stock=OVERSOLD)

    verdict = grade(rig, parallel_case())

    assert reason_of(verdict) == (
        "3 requests at once: expected 2 to answer 201 and 1 to answer 409; 3 answered 201; "
        "after GET /stock: body.stock: expected 0, got -1"
    )


def test_a_case_with_no_after_request_judges_its_counts_alone():
    rig = rig_answering((CREATED, CONFLICT, CREATED))

    grade(rig, parallel_case(after=None))

    assert rig.journal == ["mocks reset", "send 3 at once"]


def test_the_burst_gets_what_the_before_requests_left_of_the_limit():
    rig = rig_answering((CREATED, CONFLICT, CREATED))
    seed = HttpRequest("POST", "/seed")
    rig.app.answers[seed.target] = HttpResponse(200, {}, b"", 100 * MILLISECOND_NS)

    grade(rig, parallel_case(before=(seed,)))

    assert rig.app.limits[1] == LIMIT_MS - 100


def test_a_burst_spends_its_slowest_answer_once_since_they_ran_together():
    rig = rig_answering((CREATED, CONFLICT, CREATED))

    grade(rig, parallel_case())

    assert rig.app.limits == [LIMIT_MS, LIMIT_MS - 30]


def test_a_before_request_that_fails_stops_the_case_before_the_burst():
    rig = rig_answering()
    seed = HttpRequest("POST", "/seed")
    rig.app.answers[seed.target] = HttpResponse(500, {}, b"")

    verdict = grade(rig, parallel_case(before=(seed,)))

    assert (verdict.status, "send 3 at once" in rig.journal) == (CaseStatus.FAIL, False)


def test_a_before_request_that_fails_names_itself():
    rig = rig_answering()
    seed = HttpRequest("POST", "/seed")
    rig.app.answers[seed.target] = HttpResponse(500, {}, b"")

    reason = reason_of(grade(rig, parallel_case(before=(seed,))))

    assert reason == "before[0] POST /seed: expected a 2xx status, got 500"


def test_a_request_of_the_burst_past_the_limit_times_the_case_out():
    timed_out = ExchangeFailed(ExchangeFailure.TIMED_OUT, "no whole answer", LIMIT_MS)
    rig = rig_answering((CREATED, timed_out, CONFLICT))

    verdict = grade(rig, parallel_case())

    assert (verdict.status, verdict.outcome) == (CaseStatus.TIMEOUT, TimedOut(LIMIT_MS))


def test_a_repeated_case_runs_each_time_from_a_reset():
    rig = rig_answering(*[(CREATED, CREATED, CONFLICT)] * 3)

    grade(rig, parallel_case(repeat=3, fresh=True, after=None))

    assert (
        rig.journal
        == ["mocks reset", "restart app with fresh data", "mocks reset", "send 3 at once"] * 3
    )


def test_a_repeated_case_passes_when_every_run_does():
    rig = rig_answering(*[(CREATED, CREATED, CONFLICT)] * 3)

    verdict = grade(rig, parallel_case(repeat=3, fresh=True))

    assert verdict.status is CaseStatus.PASS


def test_a_failing_run_ends_the_case_and_says_which_run_it_was():
    oversold = (CREATED, CREATED, CREATED)
    rig = rig_answering((CREATED, CREATED, CONFLICT), oversold, (CREATED, CREATED, CONFLICT))

    verdict = grade(rig, parallel_case(repeat=3, fresh=True, after=None))

    assert (reason_of(verdict), rig.journal.count("send 3 at once")) == (
        "run 2 of 3: 3 requests at once: expected 2 to answer 201 and 1 to answer 409; "
        "3 answered 201",
        2,
    )


def test_a_single_run_names_no_run():
    rig = rig_answering((CREATED, CREATED, CREATED))

    reason = reason_of(grade(rig, parallel_case(after=None)))

    assert reason == (
        "3 requests at once: expected 2 to answer 201 and 1 to answer 409; 3 answered 201"
    )


def test_before_requests_must_answer_2xx_as_a_single_requests_do():
    assert HttpCaseInput({}, before=(STOCK,)).before_steps() == (
        HttpStep("before[0] GET /stock", STOCK, BEFORE_EXPECTED),
    )
