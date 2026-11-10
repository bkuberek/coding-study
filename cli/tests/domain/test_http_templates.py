import json

import pytest

from coding_study.domain.cases import Expected
from coding_study.domain.http_case import (
    FormBody,
    HttpExpected,
    JsonBody,
    LogAssertion,
    RequestTemplate,
    SameBody,
    TextBody,
)
from coding_study.domain.http_templates import (
    MissingValueError,
    UnreachableUrlError,
    bound,
    filled,
    malformed_placeholder,
    placeholder_names,
    rendered_assertion,
    rendered_expected,
    rendered_request,
)

VALUES = {"code": "c-1", "token": "t/2", "auth": "http://idp:8080/realms/pp3/auth?state=s1"}


def test_a_name_is_filled_with_its_value_as_it_is():
    assert filled("/items/{{token}}", VALUES) == "/items/t/2"


def test_a_name_with_no_value_raises():
    with pytest.raises(MissingValueError) as raised:
        filled("{{missing}}", VALUES)
    assert raised.value.name == "missing"


def test_text_around_and_between_names_stays():
    assert filled("a {{code}} b {{code}} c", VALUES) == "a c-1 b c-1 c"


def test_braces_that_name_nothing_stay_as_they_are():
    assert filled("{{ code }} {x}", VALUES) == "{{ code }} {x}"


def test_names_are_listed_in_order():
    assert placeholder_names("{{a}}/{{b_2}}/{{a}}") == ("a", "b_2", "a")


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("{{code}} and {{token}}", None),
        ("plain", None),
        ("{{ code }}", "{{ code }}"),
        ("{{code}} then {{a.b}}", "{{a.b}}"),
        ("{{unclosed", "{{unclosed"),
    ],
)
def test_a_brace_pair_that_opens_no_name_is_found(text: str, found: str | None):
    assert malformed_placeholder(text) == found


def test_binding_fills_only_the_names_it_gives():
    assert bound("{{user}} {{code}}", {"user": "learner"}) == "learner {{code}}"


def test_binding_never_fills_a_value_twice():
    assert bound("{{a}}", {"a": "{{b}}", "b": "no"}) == "{{b}}"


def test_a_path_alone_goes_to_the_app():
    request = rendered_request(RequestTemplate("GET", "/items/{{code}}"), VALUES)
    assert (request.origin, request.path, request.jar) == (None, "/items/c-1", "main")


def test_an_absolute_url_names_its_origin_and_keeps_its_query():
    request = rendered_request(RequestTemplate("GET", "{{auth}}"), VALUES)
    assert (request.origin, request.target) == ("http://idp:8080", "/realms/pp3/auth?state=s1")


def test_a_query_adds_to_the_query_of_a_url():
    template = RequestTemplate("GET", "{{auth}}", query={"code": "{{code}}"})
    assert rendered_request(template, VALUES).target == "/realms/pp3/auth?state=s1&code=c-1"


def test_a_url_with_no_port_gets_the_default_one():
    request = rendered_request(RequestTemplate("GET", "http://IdP/a"), VALUES)
    assert request.origin == "http://idp:80"


def test_a_url_over_https_cannot_be_sent():
    with pytest.raises(UnreachableUrlError):
        rendered_request(RequestTemplate("GET", "https://idp:8443/a"), VALUES)


def test_a_form_is_encoded_with_its_content_type():
    template = RequestTemplate("POST", "/token", body=FormBody({"code": "{{code}}", "x": "a b"}))
    request = rendered_request(template, VALUES)
    assert (request.body, request.headers) == (
        b"code=c-1&x=a+b",
        {"Content-Type": "application/x-www-form-urlencoded"},
    )


def test_a_json_body_fills_its_strings_and_keeps_its_shape():
    template = RequestTemplate("POST", "/a", body=JsonBody({"code": "{{code}}", "n": [1, None]}))
    request = rendered_request(template, VALUES)
    assert json.loads(request.body or b"") == {"code": "c-1", "n": [1, None]}


def test_a_content_type_the_step_names_wins():
    template = RequestTemplate(
        "POST", "/a", headers={"content-type": "text/plain"}, body=JsonBody(1)
    )
    assert rendered_request(template, VALUES).headers == {"content-type": "text/plain"}


def test_a_text_body_goes_with_no_content_type():
    request = rendered_request(RequestTemplate("POST", "/a", body=TextBody("{{token}}")), VALUES)
    assert (request.body, request.headers) == (b"t/2", {})


def test_headers_and_the_jar_and_redirects_carry_over():
    template = RequestTemplate(
        "GET",
        "/me",
        headers={"Authorization": "Bearer {{token}}"},
        jar="second",
        follow_redirects=True,
    )
    request = rendered_request(template, VALUES)
    assert (request.headers, request.jar, request.follow_redirects) == (
        {"Authorization": "Bearer t/2"},
        "second",
        True,
    )


def test_an_expected_body_and_headers_are_filled():
    expected = HttpExpected(200, Expected({"code": "{{code}}"}), {"X-Code": "{{code}}"})
    assert rendered_expected(expected, VALUES) == HttpExpected(
        200, Expected({"code": "c-1"}), {"X-Code": "c-1"}
    )


def test_a_log_assertion_is_filled():
    assertion = LogAssertion("idp", "token", count=1, form={"code": "{{code}}"})
    assert rendered_assertion(assertion, VALUES).form == {"code": "c-1"}


def test_a_log_assertions_body_subset_is_filled():
    assertion = LogAssertion("llm", count=1, body={"user": {"code": "{{code}}"}, "n": 1})
    assert rendered_assertion(assertion, VALUES).body == {"user": {"code": "c-1"}, "n": 1}


def test_a_log_assertion_keeps_its_other_body_fields():
    same = SameBody("llm", "chat", ("messages",))
    assertion = LogAssertion(
        "backup", count=1, body_max={"max_tokens": 9}, body_same_as=same, body_prefix_stable="m"
    )
    assert rendered_assertion(assertion, VALUES) == assertion
