import json
from typing import Any

import pytest

from coding_study.domain.http_captures import (
    Captured,
    CaptureSyntaxError,
    capture_source,
    captured,
)
from coding_study.domain.http_case import CaptureKind, CaptureSource
from coding_study.domain.http_grading import HttpResponse

LOGIN_PAGE = b"""<html><body>
<form id="other" action="/nope"></form>
<form id="kc-form-login" method="post"
      action="http://idp:8080/realms/pp3/login-actions/authenticate?session_code=s&amp;tab_id=t">
  <input type="hidden" name="csrf" value="tok&lt;1&gt;">
  <input name="remember" disabled>
</form></body></html>"""


def found(text: str, response: HttpResponse) -> Captured:
    return captured(capture_source(text), response)


def json_answer(document: Any) -> HttpResponse:
    return HttpResponse(200, {}, json.dumps(document).encode())


def html_answer() -> HttpResponse:
    return HttpResponse(200, {"content-type": "text/html"}, LOGIN_PAGE)


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("status", CaptureSource(CaptureKind.STATUS)),
        ("header.Location", CaptureSource(CaptureKind.HEADER, ("Location",))),
        (
            "header.location.query.code",
            CaptureSource(CaptureKind.HEADER, ("location", "query", "code")),
        ),
        ("body.tokens.0.id", CaptureSource(CaptureKind.BODY, ("tokens", "0", "id"))),
        ("form.kc-form-login.action", CaptureSource(CaptureKind.FORM, ("kc-form-login", "action"))),
        ("input.csrf.value", CaptureSource(CaptureKind.INPUT, ("csrf", "value"))),
    ],
)
def test_a_source_names_a_place_in_an_answer(text: str, source: CaptureSource):
    assert (capture_source(text), source.written) == (source, text)


@pytest.mark.parametrize(
    "text",
    ["cookie.x", "status.code", "header", "header.location.path", "body", "form.login", "body..a"],
)
def test_a_source_that_names_no_place_is_refused(text: str):
    with pytest.raises(CaptureSyntaxError):
        capture_source(text)


def test_the_status_is_captured_as_text():
    assert found("status", HttpResponse(302, {}, b"")) == Captured("302")


def test_a_header_is_found_by_its_name_in_any_case():
    answer = HttpResponse(302, {"location": "/next"}, b"")
    assert found("header.Location", answer) == Captured("/next")


def test_a_missing_header_says_so():
    assert found("header.location", json_answer({})) == Captured(None, "no header location")


def test_a_query_parameter_of_a_location_is_found():
    answer = HttpResponse(302, {"location": "http://app:8000/callback?state=s&code=c%2F1"}, b"")
    assert found("header.location.query.code", answer) == Captured("c/1")


def test_a_missing_query_parameter_says_so():
    answer = HttpResponse(302, {"location": "/callback?state=s"}, b"")
    assert found("header.location.query.code", answer).missing == (
        "header location has no query parameter code"
    )


def test_a_json_field_is_found_by_its_dotted_path_through_lists():
    answer = json_answer({"tokens": [{"id": "a"}, {"id": "b"}]})
    assert found("body.tokens.1.id", answer) == Captured("b")


def test_a_json_number_is_captured_as_its_json_text():
    assert found("body.expires_in", json_answer({"expires_in": 300})) == Captured("300")


def test_a_missing_json_field_names_where_the_path_ends():
    assert found("body.tokens.5.id", json_answer({"tokens": []})).missing == (
        "the body has no body.tokens.5"
    )


def test_a_body_that_is_not_json_says_so():
    assert found("body.a", HttpResponse(200, {}, b"<html>")).missing == "the body is not JSON"


def test_a_form_attribute_is_found_by_the_forms_id_and_unescaped():
    assert found("form.kc-form-login.action", html_answer()) == Captured(
        "http://idp:8080/realms/pp3/login-actions/authenticate?session_code=s&tab_id=t"
    )


def test_an_input_attribute_is_found_by_the_inputs_name_and_unescaped():
    assert found("input.csrf.value", html_answer()) == Captured("tok<1>")


def test_a_missing_form_says_so():
    assert found("form.register.action", html_answer()).missing == (
        'the body has no <form id="register">'
    )


def test_an_attribute_with_no_value_counts_as_missing():
    assert found("input.remember.disabled", html_answer()).missing == (
        '<input name="remember"> has no attribute disabled'
    )
