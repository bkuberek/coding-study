"""The Guides view's search and filters in a real browser (docs/specs/web-ui.md#guides-view), in
each engine of `tests/browsers.py`, over the catalog's real guides and paths: the paths in the
order of `cstudy learn`, from introductory to advanced, "Getting started" first; `/` focusing the
search; a search that narrows the guides and the paths as it is typed, asking the server nothing;
the level, path and status filters combining with it; the route's query keeping them through a
reload and back from a guide; a path's guides in its order; chips, the count and Clear; and an
empty result saying what it asked. The CSP holds and nothing is logged.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
import subprocess
import sys
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
FIRST_PATH = "getting-started"
PATH = "hashing"
TEXT = "hash"
LEVEL = "advanced"
NOWHERE = "zebra-that-is-nowhere"
REMOVE_MARK = "\N{MULTIPLICATION SIGN}"
"""What a chip ends with: the button removes its filter."""
SEARCH = ".guides #filter-search"
"""The Problems view's search has the same id, so the selector names the view."""
GUIDES_LINK = ".topbar nav a[data-view='guides']"
PATH_LINKS = ".path-cards .path-card h3 a"
GUIDE_LINKS = ".guide-list .guide-title"
CHIPS = ".filter-summary .filter-chip"
TALLY = ".filter-summary .filter-count"
NONE_TEXTS = ".guide-none:not([hidden])"
FOCUSED = "document.activeElement?.id"
SHOWN_SLUGS = """selector => [...document.querySelectorAll(selector)]
    .filter((link) => link.offsetParent !== null)
    .map((link) => decodeURIComponent(link.getAttribute("href").split("/").pop()))"""
"""The slugs of the guides or paths a selector's links name, of those the page shows."""


@dataclass
class Seen:
    path_order: list[str] = field(default_factory=list[str])
    first_card: str = ""
    focused_by_slash: str = ""
    slash_typed: str = ""
    requests_while_typing: int = -1
    searched_guides: list[str] = field(default_factory=list[str])
    searched_paths: list[str] = field(default_factory=list[str])
    searched_fragment: str = ""
    searched_tally: str = ""
    leveled_guides: list[str] = field(default_factory=list[str])
    leveled_fragment: str = ""
    leveled_chips: list[str] = field(default_factory=list[str])
    leveled_none: list[str] = field(default_factory=list[str])
    reloaded: tuple[str, str, list[str], list[str]] = ("", "", [], [])
    back_from_a_guide: tuple[str, str, list[str]] = ("", "", [])
    cleared: tuple[str, int, str, bool] = ("", -1, "", False)
    path_guides: list[str] = field(default_factory=list[str])
    path_paths: list[str] = field(default_factory=list[str])
    read_none: list[str] = field(default_factory=list[str])
    focus_after_a_chip: str = ""
    chips_after_a_chip: list[str] = field(default_factory=list[str])
    nowhere_none: list[str] = field(default_factory=list[str])
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"guides-search-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def learned(server: RunningServer) -> dict[str, Any]:
    """`cstudy learn --json` in the server's workspace, with the guide steps of the path."""
    listing = _learn(server, "--json")
    steps = _learn(server, "--path", PATH, "--json")["steps"]
    listing["path_guides"] = [step["slug"] for step in steps if step["kind"] == "guide"]
    return listing


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_context().new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.click(GUIDES_LINK)
        page.wait_for_selector(SEARCH)
        found.path_order = _shown(page, PATH_LINKS)
        found.first_card = page.inner_text(".path-card")
        _slash(page, found)
        _search(page, found)
        _level(page, found)
        _reload(page, found)
        _back_from_a_guide(page, found)
        _clear(page, found)
        _path_and_read(page, found)
        _nowhere(page, found)
        browser.close()
    return found


def _learn(server: RunningServer, *arguments: str) -> dict[str, Any]:
    command = [sys.executable, "-m", "coding_study", "learn", *arguments]
    result = subprocess.run(
        command, capture_output=True, text=True, env=server.environment, check=True
    )
    return json.loads(result.stdout)


def _shown(page: Any, selector: str) -> list[str]:
    return page.evaluate(SHOWN_SLUGS, selector)


def _chips(page: Any) -> list[str]:
    """Each chip's text, its whitespace collapsed: the mark is an item of the button's flex box,
    which the text reads on a line of its own."""
    return [" ".join(chip.split()) for chip in page.locator(CHIPS).all_inner_texts()]


def _wait_for_count(page: Any, selector: str, count: int) -> None:
    page.wait_for_function(
        f"count => ({SHOWN_SLUGS})({json.dumps(selector)}).length === count", arg=count
    )


def _slash(page: Any, found: Seen) -> None:
    page.click(".guides-intro")
    page.keyboard.press("/")
    found.focused_by_slash = page.evaluate(FOCUSED)
    found.slash_typed = page.locator(SEARCH).input_value()


def _search(page: Any, found: Seen) -> None:
    asked: list[str] = []
    page.on("request", lambda request: asked.append(request.url))
    page.locator(SEARCH).press_sequentially(TEXT)
    page.wait_for_function("text => location.hash.includes(text)", arg=f"search={TEXT}")
    page.wait_for_selector(".filter-summary:not([hidden])")
    found.requests_while_typing = len([url for url in asked if "/api/v1/" in url])
    found.searched_guides = _shown(page, GUIDE_LINKS)
    found.searched_paths = _shown(page, PATH_LINKS)
    found.searched_fragment = page.evaluate("location.hash")
    found.searched_tally = page.inner_text(TALLY)


def _level(page: Any, found: Seen) -> None:
    page.select_option("#filter-level", LEVEL)
    page.wait_for_selector(CHIPS)
    found.leveled_guides = _shown(page, GUIDE_LINKS)
    found.leveled_fragment = page.evaluate("location.hash")
    found.leveled_chips = _chips(page)
    found.leveled_none = page.locator(NONE_TEXTS).all_inner_texts()


def _reload(page: Any, found: Seen) -> None:
    page.reload()
    page.wait_for_selector(CHIPS)
    found.reloaded = (
        page.locator(SEARCH).input_value(),
        page.locator("#filter-level").input_value(),
        _chips(page),
        _shown(page, GUIDE_LINKS),
    )


def _back_from_a_guide(page: Any, found: Seen) -> None:
    page.click(f"{GUIDE_LINKS} >> nth=0")
    page.wait_for_selector(".guide-head h1")
    page.go_back()
    page.wait_for_selector(CHIPS)
    found.back_from_a_guide = (
        page.locator(SEARCH).input_value(),
        page.locator("#filter-level").input_value(),
        _shown(page, GUIDE_LINKS),
    )


def _clear(page: Any, found: Seen) -> None:
    page.click(".filter-summary .clear")
    page.wait_for_selector(".filter-summary", state="hidden")
    found.cleared = (
        page.evaluate(FOCUSED),
        len(_shown(page, GUIDE_LINKS)),
        page.evaluate("location.hash"),
        page.locator("#filter-level").input_value() == "",
    )


def _path_and_read(page: Any, found: Seen) -> None:
    page.select_option("#filter-path", PATH)
    page.wait_for_selector(CHIPS)
    found.path_guides = _shown(page, GUIDE_LINKS)
    found.path_paths = _shown(page, PATH_LINKS)
    page.select_option("#filter-status", "read")
    _wait_for_count(page, GUIDE_LINKS, 0)
    found.read_none = page.locator(NONE_TEXTS).all_inner_texts()
    page.click("#chip-status")
    _wait_for_count(page, GUIDE_LINKS, len(found.path_guides))
    found.focus_after_a_chip = page.evaluate(FOCUSED)
    found.chips_after_a_chip = _chips(page)
    page.click(".filter-summary .clear")
    page.wait_for_selector(".filter-summary", state="hidden")


def _nowhere(page: Any, found: Seen) -> None:
    page.locator(SEARCH).fill(NOWHERE)
    _wait_for_count(page, GUIDE_LINKS, 0)
    found.nowhere_none = page.locator(NONE_TEXTS).all_inner_texts()


def _matching(entries: list[dict[str, Any]], text: str) -> list[str]:
    return [
        entry["slug"]
        for entry in entries
        if any(text in entry[key].lower() for key in ("title", "summary", "slug"))
    ]


def _title(learned: dict[str, Any], slug: str) -> str:
    return next(path["title"] for path in learned["paths"] if path["slug"] == slug)


def test_the_paths_show_in_the_order_of_cstudy_learn_getting_started_first(
    seen: Seen, learned: dict[str, Any]
):
    assert (seen.path_order, seen.path_order[0], "level: intro" in seen.first_card) == (
        [path["slug"] for path in learned["paths"]],
        FIRST_PATH,
        True,
    )


def test_slash_focuses_the_search_and_types_nothing(seen: Seen):
    assert (seen.focused_by_slash, seen.slash_typed) == ("filter-search", "")


def test_a_search_narrows_the_guides_and_paths_as_it_is_typed(seen: Seen, learned: dict[str, Any]):
    guides = _matching(learned["guides"], TEXT)
    paths = _matching(learned["paths"], TEXT)
    assert (seen.searched_guides, seen.searched_paths, seen.searched_tally) == (
        guides,
        paths,
        f"{len(guides)} of {len(learned['guides'])} guides"
        f" · {len(paths)} of {len(learned['paths'])} paths",
    )


def test_typing_asks_the_server_nothing_and_the_route_keeps_the_search(seen: Seen):
    assert (seen.requests_while_typing, seen.searched_fragment) == (0, f"#/guides?search={TEXT}")


def test_the_level_combines_with_the_search(seen: Seen, learned: dict[str, Any]):
    at_level = {guide["slug"] for guide in learned["guides"] if guide["level"] == LEVEL}
    expected = [slug for slug in _matching(learned["guides"], TEXT) if slug in at_level]
    assert (
        len(expected) >= 1,
        seen.leveled_guides,
        seen.leveled_fragment,
        seen.leveled_chips,
        seen.leveled_none,
    ) == (
        True,
        expected,
        f"#/guides?level={LEVEL}&search={TEXT}",
        [f"level: {LEVEL} {REMOVE_MARK}"],
        [f'no paths match "{TEXT}", level: {LEVEL}'],
    )


def test_a_reload_keeps_the_search_and_the_filters(seen: Seen):
    assert seen.reloaded == (TEXT, LEVEL, [f"level: {LEVEL} {REMOVE_MARK}"], seen.leveled_guides)


def test_back_from_a_guide_keeps_the_search_and_the_filters(seen: Seen):
    assert seen.back_from_a_guide == (TEXT, LEVEL, seen.leveled_guides)


def test_clear_shows_everything_and_gives_the_focus_to_the_search(
    seen: Seen, learned: dict[str, Any]
):
    assert seen.cleared == ("filter-search", len(learned["guides"]), "#/guides", True)


def test_a_path_shows_its_guides_in_its_order(seen: Seen, learned: dict[str, Any]):
    assert (seen.path_guides, seen.path_paths) == (learned["path_guides"], [PATH])


def test_an_empty_result_says_what_it_asked(seen: Seen, learned: dict[str, Any]):
    asked = f"path: {_title(learned, PATH)}, status: read"
    assert (seen.read_none, seen.nowhere_none) == (
        [f"no paths match {asked}", f"no guides match {asked}"],
        [f'no paths match "{NOWHERE}"', f'no guides match "{NOWHERE}"'],
    )


def test_removing_a_chip_moves_the_focus_to_its_neighbour(seen: Seen, learned: dict[str, Any]):
    assert (seen.focus_after_a_chip, seen.chips_after_a_chip) == (
        "chip-path",
        [f"path: {_title(learned, PATH)} {REMOVE_MARK}"],
    )


def test_nothing_is_logged(seen: Seen):
    assert seen.logged == []
