"""The steps of a multi-step case that send nothing: a sleep, against a stack and clients in
memory."""

import time

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case
from coding_study.domain.http_case import CaseStep, HttpCaseInput, HttpExpected, SleepStep
from coding_study.domain.http_grading import HttpResponse
from tests.application.http_grading_fakes import Rig
from tests.application.test_http_grading_steps import (
    MILLISECONDS_NS,
    grade,
    reason,
    sent_targets,
    step,
    verdict_of,
)

LIMIT_MS = 250
GET_A = step("step 1 GET /a", "/a")
GET_B = step("step 3 GET /b", "/b")


def limited_case(*steps: CaseStep, limit_ms: int = LIMIT_MS) -> Case:
    return Case("h1", HttpCaseInput({}, steps=steps), None, level=1, hang_guard_ms=limit_ms)


def test_a_sleep_waits_before_the_next_step():
    started = time.monotonic()
    grade(Rig(), limited_case(GET_A, SleepStep("step 2 sleep 20 ms", 20), GET_B))
    assert time.monotonic() - started >= 0.02


def test_a_sleep_counts_toward_the_cases_limit():
    rig = Rig()
    grade(rig, limited_case(GET_A, SleepStep("step 2 sleep 20 ms", 20), GET_B))
    assert rig.app.limits == [LIMIT_MS, LIMIT_MS - 20]


def test_a_sleep_past_what_is_left_of_the_limit_times_the_case_out():
    rig = Rig()
    rig.app.answers["/a"] = HttpResponse(200, {}, b"", duration_ns=40 * MILLISECONDS_NS)
    case = limited_case(GET_A, SleepStep("step 2 sleep 20 ms", 20), GET_B, limit_ms=50)
    verdict = verdict_of(rig, case)
    assert (verdict.status, sent_targets(rig)) == (CaseStatus.TIMEOUT, ["/a"])


def test_a_case_that_ends_with_a_sleep_judges_its_last_answer():
    failing = step("step 1 GET /a", "/a", HttpExpected(201))
    verdict = verdict_of(Rig(), limited_case(failing, SleepStep("step 2 sleep 1 ms", 1)))
    assert reason(verdict) == "step 1 GET /a: status: expected 201, got 200"
