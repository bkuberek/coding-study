import pytest

from coding_study.domain.http_case import HttpRequest
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.http_origins import (
    app_origin,
    declared_origins,
    host_header,
    reach_origin,
    split_url,
)
from coding_study.domain.http_redirects import redirected

POST_FORM = HttpRequest(
    "POST",
    "/login-actions/authenticate",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    body=b"username=learner",
    origin="http://idp:8080",
    jar="main",
    follow_redirects=True,
)
SENT_TO = "http://idp:8080/login-actions/authenticate"


def redirect(status: int, location: str) -> HttpResponse:
    return HttpResponse(status, {"location": location}, b"")


@pytest.mark.parametrize("status", [301, 302, 303])
def test_a_redirect_becomes_a_get_with_no_body_and_no_headers(status: int):
    following = redirected(POST_FORM, redirect(status, "http://app:8000/callback?code=c"), SENT_TO)
    assert following == HttpRequest(
        "GET", "/callback?code=c", origin="http://app:8000", jar="main", follow_redirects=True
    )


@pytest.mark.parametrize("status", [307, 308])
def test_a_307_or_308_repeats_the_request_at_the_new_place(status: int):
    following = redirected(POST_FORM, redirect(status, "/other"), SENT_TO)
    assert following is not None
    assert (following.method, following.target, following.body, following.origin) == (
        "POST",
        "/other",
        b"username=learner",
        "http://idp:8080",
    )


def test_a_relative_location_is_read_against_where_the_request_went():
    following = redirected(POST_FORM, redirect(302, "../account"), SENT_TO)
    assert following is not None
    assert (following.origin, following.path) == ("http://idp:8080", "/account")


def test_an_answer_that_is_no_redirect_gives_no_next_request():
    assert redirected(POST_FORM, HttpResponse(200, {"location": "/x"}, b""), SENT_TO) is None


def test_a_redirect_with_no_location_gives_no_next_request():
    assert redirected(POST_FORM, HttpResponse(302, {}, b""), SENT_TO) is None


def test_a_redirect_to_https_gives_no_next_request():
    assert redirected(POST_FORM, redirect(302, "https://bank:443/"), SENT_TO) is None


def test_a_url_splits_into_its_origin_and_its_path_with_the_query():
    assert split_url("http://IdP:8080/realms/a?b=1#frag") == ("http://idp:8080", "/realms/a?b=1")


def test_a_url_with_no_path_has_the_root_path():
    assert split_url("http://app:8000") == ("http://app:8000", "/")


@pytest.mark.parametrize("url", ["https://idp:8443/a", "/relative", "http://:80/", "http://a:x/"])
def test_a_url_the_grader_cannot_send_splits_into_nothing(url: str):
    assert split_url(url) is None


def test_the_host_header_is_the_name_and_port():
    assert host_header("http://idp:8080") == "idp:8080"


def test_the_problem_declares_the_app_and_each_origin_the_grader_reaches():
    assert declared_origins(8000, ("idp:8080", "db:5432")) == {
        app_origin(8000),
        "http://idp:8080",
        "http://db:5432",
    }


def test_with_nothing_to_reach_the_app_is_the_only_declared_origin():
    assert declared_origins(8000, ()) == {app_origin(8000)}


def test_a_reached_origin_is_the_grader_reach_entry_over_http():
    assert reach_origin("idp:8080") == "http://idp:8080"
