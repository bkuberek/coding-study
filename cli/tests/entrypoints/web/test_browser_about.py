"""The About view in a real browser (docs/specs/web-ui.md#about-view), in each engine of
`tests/browsers.py`: the status bar's `cstudy x.y.z` is a link to `#/about`, which has its own
route, survives a reload and is not in the top bar; the view shows the version, the license, the
website, the project links and the credits, with the full license texts fetched only once their
section opens; its links to other sites open safely; the Sponsor links are plain links to the
targets of `.github/FUNDING.yml`; nothing is requested from another site, the CSP holds, and no
label of the view is in capitals.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.about import SPONSOR_LINKS, WEBSITE
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
READY = "table.problems tbody tr"
VERSION_LINK = ".statusbar a.segment.version"
TOP_BAR_LINKS = "header.topbar nav a"
FACTS = ".about-facts"
EXTERNAL_LINKS = "main a[href^='http']"
SPONSOR_LINKS_SELECTOR = ".about-sponsor a"
LICENSES_SUMMARY = ".about-licenses summary"
LICENSE_TEXT = ".about-licenses pre"
LICENSES_PATH = "/api/v1/about/licenses"
UPPERCASE_PROBE = """() => [...document.querySelectorAll("main *, .statusbar .mode")]
  .filter((element) => getComputedStyle(element).textTransform === "uppercase")
  .map((element) => element.tagName.toLowerCase() + "." + element.className)"""
LABELS = "main h1, main h2, main h3, main dt, main thead th, main summary, .statusbar .mode"
ALL_CAPS_PROBE = """() => [...document.querySelectorAll(LABELS)]
  .map((element) => element.textContent.trim())
  .filter((text) => text.length > 1 && text === text.toUpperCase() && /[A-Z]/.test(text))"""


@dataclass
class Seen:
    version_text: str = ""
    version_href: str = ""
    top_bar_hrefs: list[str] = field(default_factory=list[str])
    current_on_problems: str | None = ""
    hash_after_click: str = ""
    current_on_about: str | None = None
    hash_after_reload: str = ""
    heading: str = ""
    command: str = ""
    mode: str = ""
    facts: dict[str, str] = field(default_factory=dict[str, str])
    website_href: str = ""
    external: list[dict[str, str | None]] = field(default_factory=list[dict[str, str | None]])
    section_titles: list[str] = field(default_factory=list[str])
    python_packages: list[str] = field(default_factory=list[str])
    sponsor_hrefs: list[str] = field(default_factory=list[str])
    sponsor_is_last: bool = False
    requests_before_open: list[str] = field(default_factory=list[str])
    requests_to_other_sites: list[str] = field(default_factory=list[str])
    license_requests_before_open: int = -1
    license_requests_after_open: int = -1
    license_text: str = ""
    uppercase: list[str] = field(default_factory=list[str])
    all_caps: list[str] = field(default_factory=list[str])
    brand_hash: str = ""
    current_after_leaving: str | None = ""
    focusable: bool = False
    missing_title: str = ""
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"about-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_context().new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(server.login_url)
        page.wait_for_selector(READY)
        _read_the_status_bar(page, found)
        page.click(VERSION_LINK)
        page.wait_for_selector(FACTS)
        _read_the_view(page, found, server)
        found.requests_before_open = list(requests)
        _read_the_licenses(page, found, requests)
        found.requests_to_other_sites = [
            url for url in requests if not url.startswith(server.address)
        ]
        _read_a_reload(page, found)
        _read_leaving(page, found)
        _read_a_fragment_the_view_does_not_have(page, found)
        browser.close()
    return found


def _read_the_status_bar(page: Any, found: Seen) -> None:
    found.version_text = page.inner_text(VERSION_LINK)
    found.version_href = page.get_attribute(VERSION_LINK, "href") or ""
    found.top_bar_hrefs = page.eval_on_selector_all(
        TOP_BAR_LINKS, "links => links.map(link => link.getAttribute('href'))"
    )
    found.current_on_problems = page.get_attribute(VERSION_LINK, "aria-current")
    page.focus(VERSION_LINK)
    found.focusable = page.evaluate("document.activeElement.matches('.segment.version')")


def _read_the_view(page: Any, found: Seen, server: RunningServer) -> None:
    found.hash_after_click = page.evaluate("location.hash")
    found.current_on_about = page.get_attribute(VERSION_LINK, "aria-current")
    found.heading = page.inner_text("main h1")
    found.command = page.inner_text(".command-text")
    found.mode = page.inner_text(".statusbar .mode")
    names = page.eval_on_selector_all(f"{FACTS} dt", "items => items.map(item => item.textContent)")
    values = page.eval_on_selector_all(
        f"{FACTS} dd", "items => items.map(item => item.textContent)"
    )
    found.facts = dict(zip(names, values, strict=True))
    found.website_href = page.get_attribute(f"{FACTS} a", "href") or ""
    found.external = page.eval_on_selector_all(
        EXTERNAL_LINKS,
        """links => links.map(link => (
            {href: link.href, target: link.target, rel: link.getAttribute('rel')}
        ))""",
    )
    found.section_titles = page.eval_on_selector_all(
        ".credit-section h3", "titles => titles.map(title => title.textContent)"
    )
    found.python_packages = page.eval_on_selector_all(
        ".credit-section:first-of-type .credit-name", "cells => cells.map(cell => cell.textContent)"
    )
    found.sponsor_hrefs = page.eval_on_selector_all(
        SPONSOR_LINKS_SELECTOR, "links => links.map(link => link.href)"
    )
    found.sponsor_is_last = page.evaluate(
        "document.querySelector('.about-body').lastElementChild.classList.contains('about-sponsor')"
    )
    found.uppercase = page.evaluate(UPPERCASE_PROBE)
    found.all_caps = page.evaluate(ALL_CAPS_PROBE.replace("LABELS", repr(LABELS)))


def _licenses_requested(requests: list[str]) -> int:
    return sum(url.endswith(LICENSES_PATH) for url in requests)


def _read_the_licenses(page: Any, found: Seen, requests: list[str]) -> None:
    found.license_requests_before_open = _licenses_requested(requests)
    page.click(LICENSES_SUMMARY)
    page.wait_for_selector(LICENSE_TEXT)
    found.license_text = page.inner_text(LICENSE_TEXT)
    found.license_requests_after_open = _licenses_requested(requests)


def _read_a_reload(page: Any, found: Seen) -> None:
    page.reload()
    page.wait_for_selector(FACTS)
    found.hash_after_reload = page.evaluate("location.hash")


def _read_leaving(page: Any, found: Seen) -> None:
    page.click("a.brand")
    page.wait_for_selector(READY)
    found.brand_hash = page.evaluate("location.hash")
    found.current_after_leaving = page.get_attribute(VERSION_LINK, "aria-current")


def _read_a_fragment_the_view_does_not_have(page: Any, found: Seen) -> None:
    page.evaluate("location.hash = '#/about/credits'")
    page.wait_for_selector("section.notice h1")
    found.missing_title = page.inner_text("section.notice h1")


def test_the_status_bar_version_is_a_link_to_the_about_view(seen):
    assert (seen.version_text, seen.version_href) == (
        f"cstudy {metadata.version('coding-study')}",
        "#/about",
    )


def test_the_version_link_can_take_the_focus(seen):
    assert seen.focusable


def test_the_top_bar_does_not_list_the_about_view(seen):
    assert seen.top_bar_hrefs
    assert not any("about" in href for href in seen.top_bar_hrefs)


def test_the_version_link_is_not_marked_as_current_on_another_view(seen):
    assert seen.current_on_problems is None


def test_clicking_the_version_opens_the_view_at_its_own_route(seen):
    assert seen.hash_after_click == "#/about"


def test_the_version_link_is_marked_as_current_on_the_view(seen):
    assert seen.current_on_about == "page"


def test_the_route_survives_a_reload(seen):
    assert seen.hash_after_reload == "#/about"


def test_the_view_is_headed_about(seen):
    assert seen.heading == "about"


def test_the_command_strip_names_cstudy_about(seen):
    assert seen.command == "cstudy about"


def test_the_status_bar_names_the_view(seen):
    assert seen.mode == "about"


def test_the_view_shows_the_version_and_the_license(seen):
    assert (seen.facts["version"], seen.facts["license"]) == (
        metadata.version("coding-study"),
        "MIT",
    )


def test_the_view_links_to_the_website(seen):
    assert seen.website_href.rstrip("/") == WEBSITE
    assert seen.facts["website"] == "coding-study.com"


def test_the_view_links_to_the_source_and_the_issues(seen):
    assert (seen.facts["source"], seen.facts["issues"]) == (
        "github.com/bkuberek/coding-study",
        "github.com/bkuberek/coding-study/issues",
    )


def test_the_credits_have_a_section_for_what_cstudy_uses(seen):
    assert seen.section_titles[:1] == ["Python packages"]
    assert {"Web page", "Language servers", "Toolchains"} <= set(seen.section_titles)


def test_the_credits_list_the_python_packages(seen):
    assert {"rich", "starlette"} <= set(seen.python_packages)


def test_every_link_to_another_site_opens_in_a_new_tab_safely(seen):
    assert seen.external
    assert all(
        link["target"] == "_blank" and link["rel"] == "noopener noreferrer"
        for link in seen.external
    )


def test_the_sponsor_links_are_the_targets_of_funding_yml(seen):
    assert seen.sponsor_hrefs == [link.url for link in SPONSOR_LINKS]


def test_the_sponsor_line_comes_last(seen):
    assert seen.sponsor_is_last


def test_nothing_is_requested_from_another_site(seen):
    assert seen.requests_to_other_sites == []


def test_the_license_texts_are_not_requested_before_their_section_opens(seen):
    assert seen.license_requests_before_open == 0


def test_the_license_texts_are_requested_once_when_it_opens(seen):
    assert seen.license_requests_after_open == 1


def test_the_license_texts_hold_cstudys_license(seen):
    assert "Permission is hereby granted" in seen.license_text


def test_no_text_of_the_view_is_set_in_capitals_by_the_stylesheet(seen):
    assert seen.uppercase == []


def test_no_label_of_the_view_is_written_in_capitals(seen):
    assert seen.all_caps == []


def test_leaving_the_view_goes_to_the_page_asked_for(seen):
    assert seen.brand_hash in ("#/", "")


def test_the_version_link_is_not_current_once_the_view_is_left(seen):
    assert seen.current_after_leaving is None


def test_a_longer_fragment_is_no_view(seen):
    assert seen.missing_title == "no such view"


def test_the_page_logs_no_error_and_no_csp_violation(seen):
    assert seen.logged == []
