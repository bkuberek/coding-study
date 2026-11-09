from coding_study.domain.http_captures import capture_source
from coding_study.domain.http_case import HttpExpected, HttpStep, RequestTemplate
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.http_steps import JudgedStep, StepAnswer, judged_step, step_failure
from coding_study.domain.problem import ComparatorSpec, ComparatorType

EXACT = ComparatorSpec(ComparatorType.EXACT)
REDIRECT = HttpResponse(302, {"location": "/callback?code=c1"}, b"")


def login_step(**captures: str) -> HttpStep:
    sources = {name: capture_source(source) for name, source in captures.items()}
    return HttpStep(
        "step 1 GET /login", RequestTemplate("GET", "/login"), HttpExpected(302), sources
    )


def judged(step: HttpStep, response: HttpResponse) -> JudgedStep:
    return judged_step(step, StepAnswer(response, step.expected, EXACT))


def test_a_right_answer_gives_its_captures():
    step = login_step(code="header.location.query.code", status="status")
    assert judged(step, REDIRECT) == JudgedStep((), {"code": "c1", "status": "302"})


def test_a_wrong_answer_names_the_step_and_captures_nothing():
    step = login_step(code="header.location.query.code")
    assert judged(step, HttpResponse(200, {}, b"")) == JudgedStep(
        ("step 1 GET /login: status: expected 302, got 200",)
    )


def test_a_missing_capture_fails_the_step_and_keeps_no_value():
    step = login_step(code="header.location.query.code", state="header.location.query.state")
    assert judged(step, REDIRECT) == JudgedStep(
        (
            "step 1 GET /login: capture state from header.location.query.state: "
            "header location has no query parameter state",
        )
    )


def test_a_step_with_no_expectation_takes_any_answer():
    step = HttpStep("cleanup 1 DELETE /k", RequestTemplate("DELETE", "/k"))
    assert judged(step, HttpResponse(500, {}, b"")) == JudgedStep(())


def test_the_request_of_a_single_request_case_needs_no_name():
    step = HttpStep("", RequestTemplate("GET", "/a"), HttpExpected(200))
    assert judged(step, HttpResponse(404, {}, b"")).failures == ("status: expected 200, got 404",)


def test_a_failure_with_no_answer_names_the_step():
    assert step_failure(login_step(), "{{x}} was never captured") == (
        "step 1 GET /login: {{x}} was never captured"
    )
