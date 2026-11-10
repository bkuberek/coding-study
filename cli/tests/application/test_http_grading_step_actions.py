"""The steps of a multi-step case that send nothing, a sleep and a change to a backing service,
against a stack and clients in memory."""

import time

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case
from coding_study.domain.http_case import (
    CaseStep,
    HttpCaseInput,
    HttpExpected,
    ServiceStep,
    SleepStep,
)
from coding_study.domain.http_grading import ExchangeFailed, ExchangeFailure, HttpResponse
from coding_study.domain.sandbox import ServiceAction, ServiceChange
from tests.application.http_grading_fakes import Rig
from tests.application.test_http_grading_steps import (
    MILLISECONDS_NS,
    grade,
    reason,
    sent_targets,
    step,
    steps_case,
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


def store(action: ServiceAction, number: int = 2) -> ServiceStep:
    return ServiceStep(f"step {number} {action} store", ServiceChange("store", action))


def sent_and_changed(rig: Rig) -> list[str]:
    """What the case sent and what it did to a backing service, in order."""
    return [entry for entry in rig.journal if entry.startswith(("send", *ServiceAction))]


def test_a_service_step_changes_the_service_between_requests():
    rig = Rig()
    grade(rig, limited_case(GET_A, store(ServiceAction.PAUSE), GET_B))
    assert sent_and_changed(rig)[:3] == ["send GET /a", "pause store", "send GET /b"]


def test_a_service_left_paused_is_unpaused_after_the_case():
    rig = Rig()
    grade(rig, limited_case(GET_A, store(ServiceAction.PAUSE), GET_B))
    assert sent_and_changed(rig)[-1] == "unpause store"


def test_a_service_left_stopped_is_started_after_a_case_that_failed():
    rig = Rig()
    failing = step("step 2 GET /a", "/a", HttpExpected(201))
    verdict = verdict_of(rig, limited_case(store(ServiceAction.STOP, 1), failing))
    assert (verdict.status, sent_and_changed(rig)[-1]) == (CaseStatus.FAIL, "start store")


def test_a_service_is_put_back_before_the_cleanup_steps():
    rig = Rig()
    case = steps_case(GET_A, store(ServiceAction.STOP), cleanup=(step("cleanup 1", "/undo"),))
    grade(rig, case)
    assert sent_and_changed(rig)[-2:] == ["start store", "send GET /undo"]


def test_a_service_is_put_back_before_an_app_that_hung_restarts():
    rig = Rig()
    rig.app.answers["/b"] = ExchangeFailed(ExchangeFailure.TIMED_OUT, "GET /b: no answer")
    grade(rig, limited_case(store(ServiceAction.PAUSE, 1), GET_B))
    assert rig.journal[-2:] == ["unpause store", "restart app"]


def test_a_service_the_case_put_back_itself_is_left_alone():
    rig = Rig()
    case = limited_case(store(ServiceAction.PAUSE, 1), GET_A, store(ServiceAction.UNPAUSE, 3))
    grade(rig, case)
    assert sent_and_changed(rig) == ["pause store", "send GET /a", "unpause store"]


def test_a_service_that_cannot_be_changed_is_an_error_that_ends_the_run():
    rig = Rig()
    rig.stack.service_problem = "could not pause store"
    case = limited_case(GET_A, store(ServiceAction.PAUSE), GET_B)
    judgement = grade(rig, case, steps_case(GET_A, case_id="h2"))
    assert [verdict.status for verdict in judgement.verdicts] == [
        CaseStatus.ERROR,
        CaseStatus.NOT_RUN,
    ]
