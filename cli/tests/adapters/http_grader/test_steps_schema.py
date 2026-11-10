"""Multi-step cases and flows in schemas/tests.json, beside today's single-request case."""

from typing import Any

import pytest

from coding_study.adapters.schema_validation import TESTS_SCHEMA_FILE, SchemaValidator
from tests.helpers import SCHEMAS_DIRECTORY

SOURCE = "tests.json"
LOGIN_FORM = "form.kc-form-login.action"


@pytest.fixture(scope="module")
def validator() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / TESTS_SCHEMA_FILE)


def authorize_flow() -> list[dict[str, Any]]:
    return [
        {
            "request": {"method": "GET", "path": "/login"},
            "expected": {"status": 302},
            "capture": {"auth": "header.location"},
        },
        {
            "request": {"method": "GET", "url": "{{auth}}", "jar": "browser"},
            "expected": {"status": 200},
            "capture": {"form": LOGIN_FORM, "csrf": "input.csrf.value"},
        },
        {
            "request": {
                "method": "POST",
                "url": "{{form}}",
                "form": {"username": "{{user}}", "password": "learner-pass"},
            },
            "expected": {"status": 302},
            "capture": {"code": "header.location.query.code", "status": "status"},
        },
    ]


def steps_case() -> dict[str, Any]:
    return {
        "id": "h30",
        "level": 2,
        "note": "a forged state is refused",
        "fresh": True,
        "mocks": {"idp": "alg_none"},
        "comparator": {"type": "exact"},
        "steps": [
            {"use": "authorize", "with": {"user": "learner"}},
            {
                "request": {
                    "method": "GET",
                    "path": "/callback",
                    "query": {"code": "{{code}}", "state": "forged"},
                    "follow_redirects": True,
                },
                "expected": {"status": "4xx"},
            },
            {
                "request": {"method": "GET", "url": "http://app:8000/me", "headers": {"X": "1"}},
                "expected": {"status": 401, "body": {"error": "{{code}}"}},
            },
        ],
        "cleanup": [{"request": {"method": "POST", "path": "/logout", "json": {"all": True}}}],
        "log": [
            {
                "mock": "idp",
                "route": "token",
                "count": 1,
                "form": {"code": "{{code}}"},
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            }
        ],
    }


def violations(validator: SchemaValidator, case: dict[str, Any], **document: Any) -> list[str]:
    tests = {"version": 1, "flows": {"authorize": authorize_flow()}, "cases": [case], **document}
    return [issue.location for issue in validator.violations(tests, SOURCE)]


def first_step(case: dict[str, Any]) -> dict[str, Any]:
    return case["steps"][1]


def test_a_multi_step_case_with_flows_is_valid(validator: SchemaValidator):
    assert violations(validator, steps_case()) == []


def test_a_document_may_have_no_flows(validator: SchemaValidator):
    case = steps_case()
    case["steps"] = case["steps"][1:]
    assert violations(validator, case, flows={}) == []


def test_a_single_request_case_may_expect_a_class_of_statuses(validator: SchemaValidator):
    case = {
        "id": "h1",
        "level": 1,
        "request": {"method": "GET", "path": "/a"},
        "expected": {"status": "5xx"},
    }
    assert violations(validator, case) == []


def test_a_step_may_carry_a_binary_body_in_base64(validator: SchemaValidator):
    assert violations(validator, with_request(method="PUT", body_base64="AAEC/w==")) == []


def with_steps_around(middle: dict[str, Any]) -> dict[str, Any]:
    """The case with `middle` between its first two steps."""
    case = steps_case()
    case["steps"].insert(1, middle)
    return case


def test_a_step_may_sleep_between_requests(validator: SchemaValidator):
    assert violations(validator, with_steps_around({"sleep_ms": 500})) == []


@pytest.mark.parametrize(
    ("label", "middle"),
    [
        ("no wait", {"sleep_ms": 0}),
        ("a wait past the cap", {"sleep_ms": 10_001}),
        ("a wait that is no integer", {"sleep_ms": 1.5}),
        ("a sleep with a request", {"sleep_ms": 1, "request": {"method": "GET", "path": "/"}}),
    ],
)
def test_a_sleep_step_is_refused_for(
    validator: SchemaValidator, label: str, middle: dict[str, Any]
):
    assert violations(validator, with_steps_around(middle)) != [], label


def test_a_case_of_sleeps_alone_is_refused(validator: SchemaValidator):
    assert violations(validator, refused_with(steps=[{"sleep_ms": 1}])) != []


def test_a_cleanup_step_may_not_sleep(validator: SchemaValidator):
    assert violations(validator, refused_with(cleanup=[{"sleep_ms": 1}])) != []


def refused_with(**fields: Any) -> dict[str, Any]:
    return steps_case() | fields


def given(fields: dict[str, Any]) -> dict[str, Any]:
    """The fields, with each one set to None left out."""
    return {name: value for name, value in fields.items() if value is not None}


def with_step(**fields: Any) -> dict[str, Any]:
    case = steps_case()
    case["steps"][1] = given(first_step(case) | fields)
    return case


def with_request(**fields: Any) -> dict[str, Any]:
    case = steps_case()
    first_step(case)["request"] = given({"method": "GET", "path": "/a"} | fields)
    return case


@pytest.mark.parametrize(
    ("label", "case"),
    [
        ("both request and steps", refused_with(request={"method": "GET", "path": "/"})),
        ("before with steps", refused_with(before=[{"method": "GET", "path": "/"}])),
        ("expected beside steps", refused_with(expected={"status": 200})),
        ("no steps", refused_with(steps=[])),
        ("cleanup without steps", {"id": "h1", "level": 1, "cleanup": []}),
        ("a step with neither request nor use", with_step(request=None)),
        ("both use and request", with_step(use="authorize")),
        ("with without use", refused_with(steps=[{"with": {"a": "b"}}])),
        ("a with value that is not text", refused_with(steps=[{"use": "a", "with": {"a": 1}}])),
        ("both path and url", with_request(url="http://app:8000/a")),
        ("an https url", with_request(path=None, url="https://idp:8443/a")),
        ("a relative url", with_request(path=None, url="idp/a")),
        ("both form and json", with_request(form={"a": "b"}, json={})),
        ("both body and body_base64", with_request(body="", body_base64="AA==")),
        ("both form and body_base64", with_request(form={}, body_base64="AA==")),
        ("a body_base64 that is no base64", with_request(body_base64="AAA")),
        ("a form value that is not text", with_request(form={"a": 1})),
        ("a jar that is no name", with_request(jar="two words")),
        ("an unknown capture", with_step(capture={"a": "cookie.x"})),
        ("a capture of a whole header path", with_step(capture={"a": "header.location.path"})),
        ("a capture of a form with no attribute", with_step(capture={"a": "form.login"})),
        ("a capture name that is no name", with_step(capture={"a-b": "status"})),
        ("a status class out of range", with_step(expected={"status": "6xx"})),
        ("a status that is a word", with_step(expected={"status": "ok"})),
        (
            "a log form value that is not text",
            refused_with(log=[{"mock": "m", "count": 1, "form": {"a": 1}}]),
        ),
    ],
)
def test_a_multi_step_case_is_refused_for(
    validator: SchemaValidator, label: str, case: dict[str, Any]
):
    assert violations(validator, case) != [], label


def test_a_flow_needs_steps(validator: SchemaValidator):
    assert violations(validator, steps_case(), flows={"authorize": []}) != []


def test_a_flow_name_is_a_name(validator: SchemaValidator):
    assert violations(validator, steps_case(), flows={"two words": authorize_flow()}) != []


APP_OUTPUT = {"absent": ["{{code}}", {"regex": "eyJ[A-Za-z0-9_-]+\\.eyJ"}]}


def test_a_case_may_forbid_what_the_app_prints(validator: SchemaValidator):
    assert violations(validator, steps_case() | {"app_output": APP_OUTPUT}) == []


def test_a_single_request_case_may_forbid_what_the_app_prints(validator: SchemaValidator):
    case = {
        "id": "h1",
        "level": 1,
        "request": {"method": "GET", "path": "/a"},
        "expected": {"status": 200},
        "app_output": {"absent": ["secret"]},
    }
    assert violations(validator, case) == []


@pytest.mark.parametrize(
    ("label", "app_output"),
    [
        ("nothing absent", {"absent": []}),
        ("an unknown field", {"absent": ["a"], "present": ["b"]}),
        ("a pattern with another field", {"absent": [{"regex": "a", "flags": "i"}]}),
        ("an empty text", {"absent": [""]}),
    ],
)
def test_an_output_check_is_refused_for(
    validator: SchemaValidator, label: str, app_output: dict[str, Any]
):
    assert violations(validator, steps_case() | {"app_output": app_output}) != [], label


def test_an_output_check_needs_an_http_case(validator: SchemaValidator):
    case = {"id": "h1", "input": {"a": 1}, "expected": 1, "app_output": {"absent": ["a"]}}
    assert violations(validator, case) != []
