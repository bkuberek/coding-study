"""The Docs view in a real browser (docs/specs/user-docs.md#docs-view), in each engine of
`tests/browsers.py`, over the user docs of the checkout: the top bar's Docs entry and `Alt+8`; the
pages by section; a search that `/` focuses, keeps in the route and answers with no request; a
result that opens its page at its heading, scrolled clear of the top bar with the focus on it;
the login landing on a page's heading, as `cstudy docs <topic> --open` and a deep link do; a link
between pages; and the page's colours in the dark theme. The CSP holds, nothing is fetched from
another site, and nothing is logged.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
DOCS_LINK = ".topbar nav a[data-view='docs']"
SEARCH = "#docs-search"
QUERY = "accept-license"
FOUND_HEADING = "set-up-and-repair-with---fix"
"""The heading of user-docs/doctor.md that names `--accept-license`."""
LANDING = "/docs/web-ui/keyboard"
FOCUSED = "() => document.activeElement?.id ?? ''"
FOCUSED_ON = "id => document.activeElement?.id === id"
CLEAR_OF_THE_BAR = """id => {
  const heading = document.getElementById(id).getBoundingClientRect();
  const bar = document.querySelector(".topbar").getBoundingClientRect();
  return heading.top >= bar.bottom - 1 && heading.top < window.innerHeight;
}"""
INK = "() => getComputedStyle(document.querySelector('.doc-head h1')).color"
INK_CHANGED = "light => getComputedStyle(document.querySelector('.doc-head h1')).color !== light"


@dataclass
class Seen:
    nav_href: str = ""
    nav_current: str | None = None
    sections: list[str] = field(default_factory=list[str])
    pages: int = 0
    by_key: str = ""
    search_focused: bool = False
    search_hash: str = ""
    results: list[str] = field(default_factory=list[str])
    count: str = ""
    requests_while_typing: list[str] = field(default_factory=list[str])
    result_hash: str = ""
    result_heading: str = ""
    result_focused: str = ""
    result_clear: bool = False
    landed_hash: str = ""
    landed_title: str = ""
    landed_focused: str = ""
    landed_clear: bool = False
    linked_hash: str = ""
    linked_title: str = ""
    linked_focused: str = ""
    inks: tuple[str, str] = ("", "")
    other_sites: list[str] = field(default_factory=list[str])
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"docs-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_context(color_scheme="light").new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _open_the_list(page, found)
        _search(page, found, requests)
        _open_a_result(page, found)
        _land_on_a_heading(page, found, server)
        _follow_a_link(page, found)
        _read_the_dark_theme(page, found)
        found.other_sites = [url for url in requests if not url.startswith(server.address)]
        browser.close()
    return found


def _open_the_list(page: Any, found: Seen) -> None:
    page.click(DOCS_LINK)
    page.wait_for_selector(".doc-section")
    found.nav_href = page.get_attribute(DOCS_LINK, "href") or ""
    found.nav_current = page.get_attribute(DOCS_LINK, "aria-current")
    found.sections = page.eval_on_selector_all(
        ".doc-section h2", "headings => headings.map(heading => heading.textContent)"
    )
    found.pages = page.locator(".doc-list a").count()
    page.goto(page.url.split("#")[0] + "#/progress")
    page.wait_for_function("location.hash === '#/progress'")
    page.keyboard.press("Alt+8")
    page.wait_for_selector(".doc-section")
    found.by_key = page.evaluate("location.hash")


def _search(page: Any, found: Seen, requests: list[str]) -> None:
    page.locator("main h1").click()
    page.keyboard.press("/")
    found.search_focused = page.evaluate(FOCUSED) == SEARCH[1:]
    before = len(requests)
    page.keyboard.type(QUERY)
    page.wait_for_selector(".doc-result")
    found.requests_while_typing = [url for url in requests[before:] if "/api/" in url]
    found.search_hash = page.evaluate("location.hash")
    found.results = page.eval_on_selector_all(
        ".doc-result a", "links => links.map(link => link.getAttribute('href'))"
    )
    found.count = page.inner_text("#docs-count")


def _open_a_result(page: Any, found: Seen) -> None:
    page.click(f".doc-result a[href='#/docs/doctor/{FOUND_HEADING}']")
    page.wait_for_function(FOCUSED_ON, arg=f"doc-{FOUND_HEADING}")
    found.result_hash = page.evaluate("location.hash")
    found.result_heading = page.inner_text(f"#doc-{FOUND_HEADING}")
    found.result_focused = page.evaluate(FOCUSED)
    found.result_clear = page.evaluate(CLEAR_OF_THE_BAR, f"doc-{FOUND_HEADING}")


def _land_on_a_heading(page: Any, found: Seen, server: RunningServer) -> None:
    """As `cstudy docs <topic> --open` does, with a heading: the login names the view."""
    page.goto(f"{server.login_url}&view={LANDING}")
    page.wait_for_function(FOCUSED_ON, arg="doc-keyboard")
    found.landed_hash = page.evaluate("location.hash")
    found.landed_title = page.inner_text("main h1")
    found.landed_focused = page.evaluate(FOCUSED)
    found.landed_clear = page.evaluate(CLEAR_OF_THE_BAR, "doc-keyboard")


def _follow_a_link(page: Any, found: Seen) -> None:
    page.click(".doc-body a[href='#/docs/editor/keys-and-mouse']")
    page.wait_for_function(FOCUSED_ON, arg="doc-keys-and-mouse")
    found.linked_hash = page.evaluate("location.hash")
    found.linked_title = page.inner_text("main h1")
    found.linked_focused = page.evaluate(FOCUSED)


def _read_the_dark_theme(page: Any, found: Seen) -> None:
    light = page.evaluate(INK)
    page.emulate_media(color_scheme="dark")
    page.wait_for_function(INK_CHANGED, arg=light)
    found.inks = (light, page.evaluate(INK))
    page.emulate_media(color_scheme="light")


def test_the_top_bar_and_alt_8_open_the_docs(seen: Seen):
    assert (seen.nav_href, seen.nav_current, seen.by_key) == ("#/docs", "page", "#/docs")


def test_the_list_shows_the_pages_by_section(seen: Seen):
    assert (seen.sections, seen.pages) == (
        ["Start here", "Practise", "The web UI", "Settings and help"],
        13,
    )


def test_slash_focuses_the_search_which_is_kept_in_the_route_and_asks_the_server_nothing(
    seen: Seen,
):
    assert (seen.search_focused, seen.search_hash, seen.requests_while_typing) == (
        True,
        f"#/docs?search={QUERY}",
        [],
    )


def test_the_search_finds_the_sections_that_name_the_words(seen: Seen):
    assert (
        f"#/docs/doctor/{FOUND_HEADING}" in seen.results,
        "match" in seen.count,
    ) == (True, True)


def test_a_result_opens_its_page_at_its_heading_with_the_focus(seen: Seen):
    assert (seen.result_hash, seen.result_heading, seen.result_clear) == (
        f"#/docs/doctor/{FOUND_HEADING}",
        "Set up and repair with --fix",
        True,
    )


def test_the_login_lands_on_the_heading_it_names(seen: Seen):
    assert (seen.landed_hash, seen.landed_title, seen.landed_focused, seen.landed_clear) == (
        f"#{LANDING}",
        "Practise in your browser",
        "doc-keyboard",
        True,
    )


def test_a_link_between_pages_opens_the_other_page_at_its_heading(seen: Seen):
    assert (seen.linked_hash, seen.linked_title, seen.linked_focused) == (
        "#/docs/editor/keys-and-mouse",
        "The editor and code intelligence",
        "doc-keys-and-mouse",
    )


def test_the_dark_theme_changes_the_pages_colours(seen: Seen):
    light, dark = seen.inks
    assert (light != "", light != dark) == (True, True)


def test_nothing_comes_from_another_site_and_nothing_is_logged(seen: Seen):
    assert (seen.other_sites, seen.logged) == ([], [])
