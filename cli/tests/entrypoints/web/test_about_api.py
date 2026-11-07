"""`GET /api/v1/about` and `GET /api/v1/about/licenses` (docs/specs/web-ui.md#about-view): the
document of `cstudy about`, from the same use case, over the test server's own version and its
built page directory."""

import pytest

from coding_study.adapters.installed_packages import NOTICE_FILE
from coding_study.domain.about import SPONSOR_LINKS, WEBSITE
from tests.web_server import (
    TEST_VERSION,
    WRITE_HEADERS,
    anonymous_client,
    session_client,
    web_app,
)

ABOUT = "/api/v1/about"
LICENSES = "/api/v1/about/licenses"
NOTICE = (
    "Third-party software in the cstudy web UI front end\n\n"
    + "-" * 78
    + "\nmarked 15.0.0 (MIT)\n"
    + "-" * 78
    + "\n\nThe marked license.\n"
)


@pytest.fixture
def app(tmp_path):
    return web_app(tmp_path)


@pytest.fixture
def noticed(tmp_path):
    app = web_app(tmp_path)
    (tmp_path / "static" / NOTICE_FILE).write_text(NOTICE)
    return app


def read(app, path: str):
    with session_client(app) as client:
        return client.get(path)


def test_about_answers(app):
    assert read(app, ABOUT).status_code == 200


def test_about_names_the_servers_version(app):
    assert read(app, ABOUT).json()["version"] == TEST_VERSION


def test_about_names_the_license(app):
    assert read(app, ABOUT).json()["license"] == "MIT"


def test_about_links_to_the_website(app):
    assert read(app, ABOUT).json()["website"] == {"label": "Website", "url": WEBSITE}


def test_about_lists_the_project_links(app):
    labels = [link["label"] for link in read(app, ABOUT).json()["links"]]
    assert labels == ["Source", "Issues"]


def test_about_offers_the_sponsor_links(app):
    sponsor = read(app, ABOUT).json()["sponsor"]
    assert [link["url"] for link in sponsor] == [link.url for link in SPONSOR_LINKS]


def test_about_lists_the_python_packages_as_the_command_does(app):
    sections = {section["title"]: section for section in read(app, ABOUT).json()["credits"]}
    names = [credit["name"] for credit in sections["Python packages"]["credits"]]
    assert {"rich", "starlette"} <= set(names)


def test_a_credit_has_a_name_a_version_and_a_license(app):
    credit = read(app, ABOUT).json()["credits"][0]["credits"][0]
    assert set(credit) == {"name", "version", "license"}


def test_about_credits_the_web_page_packages_the_build_noticed(noticed):
    sections = {section["title"]: section for section in read(noticed, ABOUT).json()["credits"]}
    assert sections["Web page"]["credits"] == [
        {"name": "marked", "version": "15.0.0", "license": "MIT"}
    ]


def test_about_leaves_the_web_page_out_when_the_build_wrote_no_notice(app):
    titles = [section["title"] for section in read(app, ABOUT).json()["credits"]]
    assert "Web page" not in titles


def test_the_licenses_hold_cstudys_own_text(app):
    assert "Permission is hereby granted" in read(app, LICENSES).json()["text"]


def test_the_licenses_hold_the_notice_whole(noticed):
    assert "The marked license." in read(noticed, LICENSES).json()["text"]


def test_about_needs_the_session(app):
    with anonymous_client(app) as client:
        assert client.get(ABOUT).status_code == 401


def test_the_licenses_need_the_session(app):
    with anonymous_client(app) as client:
        assert client.get(LICENSES).status_code == 401


def test_about_answers_a_get_only(app):
    with session_client(app) as client:
        assert client.post(ABOUT, headers=WRITE_HEADERS).status_code == 405
