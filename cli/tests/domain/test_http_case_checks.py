"""S23 for multi-step cases: what a step names must exist before it runs."""

from coding_study.domain.http_captures import capture_source
from coding_study.domain.http_case import (
    FormBody,
    HttpCaseInput,
    HttpExpected,
    HttpStep,
    LogAssertion,
    OutputCheck,
    OutputPattern,
    RequestTemplate,
)
from coding_study.domain.http_case_checks import step_issues

ORIGINS = frozenset({"http://app:8000", "http://idp:8080"})


def step(
    label: str,
    target: str = "/a",
    *,
    captures: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    body: FormBody | None = None,
) -> HttpStep:
    template = RequestTemplate("GET", target, headers=headers or {}, body=body)
    sources = {name: capture_source(text) for name, text in (captures or {}).items()}
    return HttpStep(label, template, HttpExpected(200), sources)


def issues(
    *steps: HttpStep,
    cleanup: tuple[HttpStep, ...] = (),
    log: tuple[LogAssertion, ...] = (),
) -> list[str]:
    http = HttpCaseInput({}, steps=steps, cleanup=cleanup, log=log)
    return list(step_issues(http, ORIGINS))


def test_a_value_captured_by_an_earlier_step_may_be_used():
    assert (
        issues(step("step 1", captures={"code": "status"}), step("step 2", "/a?c={{code}}")) == []
    )


def test_a_value_no_earlier_step_captures_is_refused():
    assert issues(step("step 1", "/a/{{code}}")) == [
        "step 1: {{code}} is captured by no earlier step"
    ]


def test_a_step_cannot_use_what_it_captures_itself():
    found = issues(step("step 1", "/{{code}}", captures={"code": "status"}))
    assert found == ["step 1: {{code}} is captured by no earlier step"]


def test_every_text_of_a_request_is_checked():
    template = step("step 1", headers={"Authorization": "Bearer {{token}}"})
    form = step("step 2", body=FormBody({"refresh_token": "{{refresh}}"}))
    assert issues(template, form) == [
        "step 1: {{token}} is captured by no earlier step",
        "step 2: {{refresh}} is captured by no earlier step",
    ]


def test_an_expected_text_is_checked_too():
    expecting = HttpStep(
        "step 1", RequestTemplate("GET", "/a"), HttpExpected(200, headers={"X": "{{x}}"})
    )
    assert issues(expecting) == ["step 1: {{x}} is captured by no earlier step"]


def test_a_cleanup_step_may_use_any_value_the_steps_capture():
    captured = step("step 1", captures={"key": "body.id"})
    assert issues(captured, cleanup=(step("cleanup 1", "/keys/{{key}}"),)) == []


def test_a_log_assertion_may_use_a_captured_value():
    captured = step("step 1", captures={"refresh": "body.refresh_token"})
    log = (LogAssertion("idp", count=1, form={"refresh_token": "{{refresh}}"}),)
    assert issues(captured, log=log) == []


def test_a_log_assertion_naming_an_uncaptured_value_is_refused():
    log = (LogAssertion("idp", count=1, headers={"Authorization": "{{token}}"}),)
    assert issues(step("step 1"), log=log) == ["log idp: {{token}} is captured by no step"]


def test_a_log_body_subset_naming_an_uncaptured_value_is_refused():
    log = (LogAssertion("llm", count=1, body={"user": ["{{user_id}}"]}),)
    assert issues(step("step 1"), log=log) == ["log llm: {{user_id}} is captured by no step"]


def test_a_url_to_a_declared_origin_is_allowed():
    assert issues(step("step 1", "http://idp:8080/realms/pp3/auth")) == []


def test_a_url_to_an_origin_the_problem_does_not_declare_is_refused():
    assert issues(step("step 1", "http://evil:80/steal")) == [
        "step 1: http://evil:80 is no origin the problem declares; "
        "it declares http://app:8000, http://idp:8080"
    ]


def test_a_url_that_is_a_capture_is_checked_when_it_is_sent():
    assert (
        issues(step("step 1", captures={"auth": "header.location"}), step("step 2", "{{auth}}"))
        == []
    )


def test_a_url_over_https_is_refused():
    assert issues(step("step 1", "https://idp:8443/a")) == [
        "step 1: https://idp:8443/a is no URL the grader can send: use http://<name>:<port>"
    ]


def test_a_brace_pair_that_opens_no_name_is_refused():
    assert issues(step("step 1", "/a/{{ code }}")) == ["step 1: {{ opens no {{name}} at {{ code }}"]


def checked_output(*absent: str | OutputPattern, steps: tuple[HttpStep, ...] = ()) -> list[str]:
    http = HttpCaseInput({}, steps=steps, app_output=OutputCheck(absent))
    return list(step_issues(http, ORIGINS))


def test_an_output_check_may_use_a_captured_value():
    assert checked_output("{{code}}", steps=(step("step 1", captures={"code": "status"}),)) == []


def test_an_output_check_naming_an_uncaptured_value_is_refused():
    assert checked_output("{{code}}") == ["app_output: {{code}} is captured by no step"]


def test_an_output_pattern_that_does_not_compile_is_refused():
    (issue,) = checked_output(OutputPattern("eyJ[("))
    assert issue.startswith("app_output: eyJ[( is no regular expression:")
