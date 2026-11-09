"""The grader's run of a multi-step case, against a stack and clients in memory."""

import time

from coding_study.application.http_grading import HttpGradingRun, run_http_grading
from coding_study.application.http_grading_ports import AppExit
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case, Expected
from coding_study.domain.config import Config
from coding_study.domain.http_captures import capture_source
from coding_study.domain.http_case import (
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    HttpStep,
    LogAssertion,
    OutputCheck,
    OutputPattern,
    RequestTemplate,
)
from coding_study.domain.http_grading import (
    ExchangeFailed,
    ExchangeFailure,
    HttpResponse,
    LoggedRequest,
    MockLog,
)
from coding_study.domain.judging import CaseVerdict, Judgement
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Problem
from coding_study.domain.runs import Returned
from tests.application.http_grading_fakes import Rig
from tests.project_builders import project_meta

IDP = "http://idp:8080"
MILLISECONDS_NS = 1_000_000
REDIRECT_TO_IDP = HttpResponse(302, {"location": f"{IDP}/auth?state=s1"}, b"")


def step(
    label: str,
    target: str,
    expected: HttpExpected | None = None,
    **captures: str,
) -> HttpStep:
    sources = {name: capture_source(source) for name, source in captures.items()}
    return HttpStep(label, RequestTemplate("GET", target), expected, sources)


def steps_case(
    *steps: HttpStep,
    case_id: str = "h1",
    cleanup: tuple[HttpStep, ...] = (),
    log: tuple[LogAssertion, ...] = (),
) -> Case:
    http = HttpCaseInput({}, steps=steps, cleanup=cleanup, log=log)
    return Case(case_id, http, None, level=1)


def grade(rig: Rig, *cases: Case) -> Judgement:
    problem = Problem(project_meta(comparator=ComparatorSpec(ComparatorType.EXACT)), cases)
    return run_http_grading(HttpGradingRun(problem, 1, Config()), rig.stack, rig.open_clients)


def verdict_of(rig: Rig, *cases: Case) -> CaseVerdict:
    return grade(rig, *cases).verdicts[0]


def reason(verdict: CaseVerdict) -> str | None:
    return verdict.mismatch.detail if verdict.mismatch else None


def sent_targets(rig: Rig) -> list[str]:
    return [f"{request.origin or ''}{request.target}" for request in rig.app.sent]


def login_case(cleanup: tuple[HttpStep, ...] = ()) -> Case:
    return steps_case(
        step("step 1 GET /login", "/login", HttpExpected(302), auth="header.location"),
        step("step 2 GET {{auth}}", "{{auth}}", HttpExpected(200)),
        cleanup=cleanup,
    )


def published_idp() -> Rig:
    rig = Rig()
    rig.stack.origins = {IDP: "http://127.0.0.1:9100"}
    rig.app.answers["/login"] = REDIRECT_TO_IDP
    return rig


def test_a_captured_value_fills_a_later_steps_url():
    rig = published_idp()
    assert verdict_of(rig, login_case()).status is CaseStatus.PASS
    assert sent_targets(rig) == ["/login", f"{IDP}/auth?state=s1"]


def test_each_case_starts_with_no_cookies():
    rig = published_idp()
    grade(rig, login_case(), steps_case(step("step 1 GET /a", "/a"), case_id="h2"))
    assert rig.app.cookie_clears == 2


def test_a_step_that_fails_ends_the_case_and_names_itself():
    rig = published_idp()
    rig.app.answers[f"{IDP}/auth?state=s1"] = HttpResponse(500, {}, b"")
    case = steps_case(
        step("step 1 GET /login", "/login", HttpExpected(302), auth="header.location"),
        step("step 2 GET {{auth}}", "{{auth}}", HttpExpected(200)),
        step("step 3 GET /me", "/me", HttpExpected(200)),
    )
    verdict = verdict_of(rig, case)
    assert (verdict.status, reason(verdict), sent_targets(rig)[-1]) == (
        CaseStatus.FAIL,
        "step 2 GET {{auth}}: status: expected 200, got 500",
        f"{IDP}/auth?state=s1",
    )


def test_a_failed_case_shows_the_answer_of_the_step_that_failed():
    rig = published_idp()
    rig.app.answers[f"{IDP}/auth?state=s1"] = HttpResponse(500, {}, b"down")
    assert verdict_of(rig, login_case()).outcome == Returned({"status": 500, "body": "down"}, 0)


def test_a_missing_capture_ends_the_case_before_its_value_is_used():
    rig = Rig()
    verdict = verdict_of(rig, login_case())
    assert (reason(verdict), sent_targets(rig)) == (
        "step 1 GET /login: status: expected 302, got 200",
        ["/login"],
    )


def test_a_step_to_an_origin_the_stack_does_not_publish_fails_and_sends_nothing():
    rig = Rig()
    rig.app.answers["/login"] = REDIRECT_TO_IDP
    verdict = verdict_of(rig, login_case())
    assert (verdict.status, reason(verdict), len(rig.app.sent)) == (
        CaseStatus.FAIL,
        f"step 2 GET {{{{auth}}}}: the stack lets the grader reach no {IDP}",
        1,
    )


def test_the_steps_share_the_cases_limit():
    rig = published_idp()
    rig.app.answers["/login"] = HttpResponse(
        302, {"location": f"{IDP}/auth"}, b"", duration_ns=100 * MILLISECONDS_NS
    )
    login = login_case()
    grade(rig, Case(login.id, login.input, None, level=1, hang_guard_ms=250))
    assert rig.app.limits == [250, 150]


def test_a_log_assertion_uses_a_captured_value():
    rig = published_idp()
    logged = LoggedRequest("token", 0, 1, {}, "code=s1")
    rig.control.logs["idp"] = MockLog((logged,))
    rig.stack.mocks = ("idp",)
    case = steps_case(
        step("step 1 GET /login", "/login", HttpExpected(302), state="header.location.query.state"),
        log=(LogAssertion("idp", "token", count=1, form={"code": "{{state}}"}),),
    )
    assert verdict_of(rig, case).status is CaseStatus.PASS


def test_a_wrong_last_step_and_a_wrong_log_are_both_reported():
    rig = Rig()
    case = steps_case(
        step("step 1 GET /a", "/a", HttpExpected(201)),
        log=(LogAssertion("room-vendor", count=1),),
    )
    assert reason(verdict_of(rig, case)) == (
        "step 1 GET /a: status: expected 201, got 200; room-vendor: expected 1 request, saw 0"
    )


def test_cleanup_runs_after_a_case_that_failed():
    rig = published_idp()
    rig.app.answers[f"{IDP}/auth?state=s1"] = HttpResponse(500, {}, b"")
    grade(rig, login_case(cleanup=(step("cleanup 1 GET /undo", "/undo"),)))
    assert sent_targets(rig)[-1] == "/undo"


def test_a_cleanup_step_that_fails_fails_a_case_that_passed():
    rig = published_idp()
    rig.app.answers["/undo"] = HttpResponse(404, {}, b"")
    cleanup = (step("cleanup 1 GET /undo", "/undo", HttpExpected(204)),)
    verdict = verdict_of(rig, login_case(cleanup=cleanup))
    assert (verdict.status, reason(verdict)) == (
        CaseStatus.FAIL,
        "cleanup 1 GET /undo: status: expected 204, got 404",
    )


def test_a_cleanup_step_naming_a_value_never_captured_is_passed_over():
    rig = Rig()
    cleanup = (step("cleanup 1 GET /keys/{{key}}", "/keys/{{key}}"), step("cleanup 2", "/undo"))
    grade(rig, steps_case(step("step 1 GET /a", "/a", HttpExpected(500)), cleanup=cleanup))
    assert sent_targets(rig) == ["/a", "/undo"]


def test_cleanup_gets_the_cases_limit_afresh():
    rig = published_idp()
    rig.app.answers["/login"] = HttpResponse(
        302, {"location": f"{IDP}/auth"}, b"", duration_ns=100 * MILLISECONDS_NS
    )
    login = login_case(cleanup=(step("cleanup 1", "/undo"),))
    grade(rig, Case(login.id, login.input, None, level=1, hang_guard_ms=250))
    assert rig.app.limits[-1] == 250


def test_a_cleanup_step_that_gets_no_answer_says_so():
    rig = published_idp()
    rig.app.answers["/undo"] = ExchangeFailed(ExchangeFailure.REFUSED, "GET /undo: refused")
    verdict = verdict_of(rig, login_case(cleanup=(step("cleanup 1 GET /undo", "/undo"),)))
    assert reason(verdict) == "cleanup 1 GET /undo: GET /undo: refused"


def test_no_cleanup_runs_once_the_app_has_died():
    rig = published_idp()
    rig.stack.exit = AppExit(1, "boom")
    rig.app.answers["/login"] = ExchangeFailed(ExchangeFailure.DROPPED, "dropped")
    grade(rig, login_case(cleanup=(step("cleanup 1", "/undo"),)))
    assert sent_targets(rig) == ["/login"]


def test_a_single_request_case_is_one_step_with_no_name():
    rig = Rig()
    http = HttpCaseInput({}, request=HttpRequest("GET", "/a"), expected=HttpExpected(201))
    verdict = verdict_of(rig, Case("h1", http, Expected({"status": 201}), level=1))
    assert reason(verdict) == "status: expected 201, got 200"


JWT = OutputPattern(r"eyJ[A-Za-z0-9_-]+\.eyJ")


def output_case(*absent: str | OutputPattern, last: HttpExpected | None = None) -> Case:
    http = HttpCaseInput(
        {},
        steps=(
            step(
                "step 1 GET /login", "/login", HttpExpected(302), code="header.location.query.code"
            ),
            step("step 2 GET /me", "/me", last),
        ),
        cleanup=(step("cleanup 1", "/undo"),),
        app_output=OutputCheck(absent),
    )
    return Case("h1", http, None, level=1)


def output_rig(printed: str) -> Rig:
    rig = Rig()
    rig.app.answers["/login"] = HttpResponse(302, {"location": "/callback?code=c-9"}, b"")
    rig.stack.output = printed
    return rig


def test_output_holding_nothing_forbidden_leaves_the_case_passing():
    rig = output_rig("GET /me 200\n")
    assert verdict_of(rig, output_case(JWT, "{{code}}")).status is CaseStatus.PASS


def test_output_holding_a_captured_value_fails_the_case():
    rig = output_rig("exchanging c-9\n")
    verdict = verdict_of(rig, output_case("{{code}}"))
    assert (verdict.status, reason(verdict)) == (
        CaseStatus.FAIL,
        'app output: printed "c-9", which it must not',
    )


def test_the_output_is_read_after_the_cleanup_from_before_the_case_began():
    rig = output_rig("")
    before = time.time()
    grade(rig, output_case(JWT))
    assert (rig.journal[-1], rig.stack.output_since[0] >= before - 1) == ("read app output", True)
    assert rig.stack.output_since[0] <= time.time()


def test_output_is_reported_with_a_wrong_answer():
    rig = output_rig("eyJhbGc.eyJzdWI.sig")
    verdict = verdict_of(rig, output_case(JWT, last=HttpExpected(201)))
    assert reason(verdict) == (
        "step 2 GET /me: status: expected 201, got 200; "
        'app output: printed "eyJhbGc.eyJ", which matches eyJ[A-Za-z0-9_-]+\\.eyJ'
    )


def test_a_case_with_no_output_check_reads_no_output():
    rig = output_rig("anything")
    grade(rig, login_case())
    assert rig.stack.output_since == []


def test_a_case_that_timed_out_reads_no_output():
    rig = output_rig("eyJa.eyJb.c")
    rig.app.answers["/me"] = ExchangeFailed(ExchangeFailure.TIMED_OUT, "no answer")
    assert verdict_of(rig, output_case(JWT)).status is CaseStatus.TIMEOUT
    assert rig.stack.output_since == []
