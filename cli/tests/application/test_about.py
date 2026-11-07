"""What `cstudy about` and the About view show (docs/specs/cli.md#cstudy-about): the version, the
license, the links and the credits, from one use case."""

import re
from collections.abc import Mapping

import pytest
import yaml

from coding_study.application.about import read_about, read_license_texts
from coding_study.domain.about import (
    AUTHOR_NAME,
    LICENSE_NAME,
    SPONSOR_LINKS,
    WEBSITE,
    Credit,
    web_ui_credits,
)
from coding_study.domain.code_intelligence import LANGUAGE_SERVERS
from coding_study.entrypoints.web import STATIC_DIRECTORY
from tests.helpers import REPOSITORY_ROOT

NOTICE = """Third-party software in the cstudy web UI front end

The JavaScript files beside this notice bundle the packages below, each under the license
that follows it.

------------------------------------------------------------------------------
@codemirror/view 6.41.1 (MIT)
------------------------------------------------------------------------------

MIT License

------------------------------------------------------------------------------
marked 15.0.0 (MIT)
------------------------------------------------------------------------------

Copyright (c) the authors
"""
RICH = Credit("rich", "15.0.0", "MIT")
STARLETTE = Credit("starlette", "1.10.0", "BSD-3-Clause")
OWN_LICENSE = "MIT License\n\nCopyright (c) the author\n"


class FakePackages:
    """The installed packages as `cstudy about` reads them, in memory."""

    def __init__(self, notice: str | None = NOTICE) -> None:
        self.notice = notice

    def python_packages(self) -> tuple[Credit, ...]:
        return (RICH, STARLETTE)

    def python_license_texts(self) -> Mapping[str, str]:
        return {"rich": "Rich licence text\n"}

    def own_license_text(self) -> str:
        return OWN_LICENSE

    def web_ui_notice(self) -> str | None:
        return self.notice


def sections(notice: str | None = NOTICE):
    return {section.title: section for section in read_about("1.2.3", FakePackages(notice)).credits}


def test_about_names_the_author():
    assert read_about("1.2.3", FakePackages()).author.name == AUTHOR_NAME == "Bastian Kuberek"


def test_the_author_is_credited_as_the_creator():
    assert read_about("1.2.3", FakePackages()).author.credit == "Created by Bastian Kuberek"


def test_the_author_link_reads_bkuberek_com():
    assert read_about("1.2.3", FakePackages()).author.link.label == "bkuberek.com"


def test_the_author_link_carries_static_utm_tags_only():
    url = read_about("1.2.3", FakePackages()).author.link.url
    assert url == "https://bkuberek.com/?utm_source=cstudy&utm_medium=app&utm_campaign=about"


def test_the_author_link_carries_nothing_of_the_version():
    assert "1.2.3" not in read_about("1.2.3", FakePackages()).author.link.url


def test_about_names_the_version_it_is_given():
    assert read_about("1.2.3", FakePackages()).version == "1.2.3"


def test_about_names_the_license():
    assert read_about("1.2.3", FakePackages()).license == LICENSE_NAME == "MIT"


def test_about_links_to_the_website():
    assert read_about("1.2.3", FakePackages()).website.url == WEBSITE == "https://coding-study.com"


def test_about_links_to_the_source_and_the_issues():
    urls = [link.url for link in read_about("1.2.3", FakePackages()).links]
    assert urls == [
        "https://github.com/bkuberek/coding-study",
        "https://github.com/bkuberek/coding-study/issues",
    ]


def funding_links() -> list[str]:
    funding = yaml.safe_load((REPOSITORY_ROOT / ".github" / "FUNDING.yml").read_text())
    return [
        *(f"https://github.com/sponsors/{name}" for name in funding["github"]),
        f"https://ko-fi.com/{funding['ko_fi']}",
    ]


def test_the_sponsor_links_are_the_ones_in_funding_yml():
    assert [link.url for link in SPONSOR_LINKS] == funding_links()


def test_about_offers_the_sponsor_links():
    assert read_about("1.2.3", FakePackages()).sponsor == SPONSOR_LINKS


def test_every_link_is_https():
    about = read_about("1.2.3", FakePackages())
    links = (about.author.link, about.website, *about.links, *about.sponsor)
    assert all(link.url.startswith("https://") for link in links)


def test_the_python_packages_are_credited_with_their_versions_and_licenses():
    assert sections()["Python packages"].credits == (RICH, STARLETTE)


def test_the_web_page_packages_are_read_from_the_bundle_notice():
    assert sections()["Web page"].credits == (
        Credit("@codemirror/view", "6.41.1", "MIT"),
        Credit("marked", "15.0.0", "MIT"),
    )


def test_a_missing_bundle_notice_leaves_the_web_page_out():
    assert "Web page" not in sections(notice=None)


def test_the_language_servers_are_named_with_the_versions_cstudy_pins():
    named = [(credit.name, credit.version) for credit in sections()["Language servers"].credits]
    assert named == [(server.name, server.version) for server in LANGUAGE_SERVERS]


def test_the_toolchains_are_named():
    names = [credit.name for credit in sections()["Toolchains"].credits]
    assert {"uv", "Node.js", "Go"} <= set(names)


def test_the_sections_come_in_a_fixed_order():
    assert list(sections()) == ["Python packages", "Web page", "Language servers", "Toolchains"]


def test_a_notice_without_packages_credits_nothing():
    assert web_ui_credits("Third-party software\n") == ()


def test_the_license_texts_start_with_cstudys_own():
    heading = read_license_texts(FakePackages()).splitlines()[1]
    assert heading == f"cstudy ({LICENSE_NAME})"


def test_the_license_texts_hold_cstudys_license():
    assert OWN_LICENSE.strip() in read_license_texts(FakePackages())


def test_the_license_texts_hold_a_python_package_text_under_its_name():
    texts = read_license_texts(FakePackages())
    assert "rich 15.0.0 (MIT)\n" in texts
    assert "Rich licence text" in texts


def test_a_python_package_without_a_text_says_so():
    texts = read_license_texts(FakePackages())
    assert "starlette 1.10.0 (BSD-3-Clause)" in texts
    assert "ships no license text" in texts


def test_the_license_texts_hold_the_bundle_notice_whole():
    assert NOTICE.strip() in read_license_texts(FakePackages())


def test_the_license_texts_leave_the_bundle_out_when_it_is_missing():
    assert "Third-party software" not in read_license_texts(FakePackages(notice=None))


def test_the_built_bundle_notice_names_packages_with_versions_and_licenses():
    credits = web_ui_credits((STATIC_DIRECTORY / "THIRD_PARTY_LICENSES.txt").read_text())
    assert credits
    assert all(re.fullmatch(r"\d+\.\d+\.\d+\S*", credit.version) for credit in credits)
    assert all(credit.license for credit in credits)


@pytest.mark.parametrize("heading", ["marked 15.0.0 MIT", "marked (MIT)", "(MIT)"])
def test_a_heading_that_is_not_a_package_line_is_not_a_credit(heading):
    rule = "-" * 78
    assert web_ui_credits(f"{rule}\n{heading}\n{rule}\n\ntext\n") == ()
