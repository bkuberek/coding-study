"""A multi-step case from tests.json, with its flows written out."""

from typing import Any

import pytest

from coding_study.adapters.http_grader.case_document import CaseDocumentError, http_case_input
from coding_study.adapters.problem_documents import cases_from_document
from coding_study.domain.cases import Expected
from coding_study.domain.errors import ContentError
from coding_study.domain.http_case import (
    CaptureKind,
    CaptureSource,
    FormBody,
    HttpExpected,
    HttpStep,
    JsonBody,
    LogAssertion,
    RequestTemplate,
)
from coding_study.domain.problem import ComparatorSpec, ComparatorType

LOGIN = {
    "request": {
        "method": "POST",
        "url": "{{form}}",
        "form": {"username": "{{user}}", "password": "pass"},
    },
    "expected": {"status": 302},
    "capture": {"code": "header.location.query.code"},
}
FLOWS: dict[str, list[dict[str, Any]]] = {
    "page": [
        {
            "request": {"method": "GET", "path": "/login"},
            "capture": {"form": "form.kc-form-login.action"},
        }
    ],
    "login": [{"use": "page"}, LOGIN],
}


def case_with(*steps: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {"id": "h1", "level": 1, "steps": list(steps), **fields}


def me_step() -> dict[str, Any]:
    return {
        "request": {"method": "GET", "path": "/me", "jar": "second", "follow_redirects": True},
        "expected": {"status": "4xx", "body": {"code": "{{code}}"}},
    }


def test_a_step_is_read_as_a_template_with_what_it_expects_and_captures():
    (step,) = http_case_input(case_with(LOGIN)).steps
    assert step == HttpStep(
        "step 1 POST {{form}}",
        RequestTemplate(
            "POST", "{{form}}", body=FormBody({"username": "{{user}}", "password": "pass"})
        ),
        HttpExpected(302),
        {"code": CaptureSource(CaptureKind.HEADER, ("location", "query", "code"))},
    )


def test_a_step_keeps_its_jar_its_redirects_and_a_status_class():
    (step,) = http_case_input(case_with(me_step())).steps
    assert (step.request, step.expected) == (
        RequestTemplate("GET", "/me", jar="second", follow_redirects=True),
        HttpExpected("4xx", Expected({"code": "{{code}}"})),
    )


def test_a_json_body_stays_json_until_it_is_sent():
    step = {"request": {"method": "POST", "path": "/a", "json": {"n": "{{n}}"}}}
    assert http_case_input(case_with(step)).steps[0].request == RequestTemplate(
        "POST", "/a", body=JsonBody({"n": "{{n}}"})
    )


def test_a_flow_is_written_out_with_what_with_gives_and_labels_that_say_where():
    steps = http_case_input(case_with({"use": "login", "with": {"user": "learner"}}), FLOWS).steps
    assert [(step.label, step.request.body) for step in steps] == [
        ("step 1, login step 1, page step 1 GET /login", None),
        (
            "step 1, login step 2 POST {{form}}",
            FormBody({"username": "learner", "password": "pass"}),
        ),
    ]


def test_a_name_that_with_does_not_give_stays_for_a_capture():
    steps = http_case_input(case_with({"use": "login"}), FLOWS).steps
    assert steps[1].request == RequestTemplate(
        "POST", "{{form}}", body=FormBody({"username": "{{user}}", "password": "pass"})
    )


def test_cleanup_steps_are_read_and_labelled_apart():
    cleanup = [{"request": {"method": "DELETE", "path": "/keys/{{key}}"}}]
    http = http_case_input(case_with(me_step(), cleanup=cleanup))
    assert [step.label for step in http.cleanup] == ["cleanup 1 DELETE /keys/{{key}}"]


def test_a_multi_step_case_keeps_its_scenarios_log_and_comparator():
    log = [{"mock": "idp", "route": "token", "count": 1, "form": {"code": "{{code}}"}}]
    document = case_with(
        me_step(), mocks={"idp": "alg_none"}, log=log, comparator={"type": "unordered"}, fresh=True
    )
    http = http_case_input(document)
    assert (http.mocks, http.log, http.comparator, http.fresh) == (
        {"idp": "alg_none"},
        (LogAssertion("idp", "token", count=1, form={"code": "{{code}}"}),),
        ComparatorSpec(ComparatorType.UNORDERED),
        True,
    )


def test_a_multi_step_cases_input_shows_its_steps_as_written():
    document = case_with({"use": "login"}, mocks={"idp": "alg_none"})
    assert http_case_input(document, FLOWS).arguments == {
        "steps": [{"use": "login"}],
        "mocks": {"idp": "alg_none"},
    }


def test_a_flow_tests_json_lacks_is_refused_with_the_step():
    with pytest.raises(CaseDocumentError, match="step 2: no flow named logout"):
        http_case_input(case_with(me_step(), {"use": "logout"}), FLOWS)


def test_a_flow_that_uses_itself_is_refused():
    looping = {"again": [{"use": "again"}]}
    with pytest.raises(CaseDocumentError, match="the flow again uses itself"):
        http_case_input(case_with({"use": "again"}), looping)


def test_a_capture_that_names_no_place_is_refused():
    step = {"request": {"method": "GET", "path": "/a"}, "capture": {"x": "cookie.session"}}
    with pytest.raises(CaseDocumentError, match=r"step 1: capture cookie\.session"):
        http_case_input(case_with(step))


def test_the_loader_reads_flows_and_multi_step_cases_with_no_expected():
    document = {"version": 1, "flows": FLOWS, "cases": [case_with({"use": "login"})]}
    (case,) = cases_from_document(document, ComparatorSpec(ComparatorType.EXACT), "tests.json")
    assert (case.expected, len(case.input.steps)) == (None, 2)  # type: ignore[union-attr]


def test_the_loader_names_the_case_of_a_flow_it_lacks():
    document = {"version": 1, "cases": [case_with({"use": "login"})]}
    with pytest.raises(ContentError) as raised:
        cases_from_document(document, ComparatorSpec(ComparatorType.EXACT), "tests.json")
    (issue,) = raised.value.issues
    assert (issue.location, issue.message) == ("cases[0]", "step 1: no flow named login")
