"""The Problems view's search, filter row, columns, rows, Next panel and top bar in a real browser
(docs/specs/web-ui.md#problems-view), in each engine of `tests/browsers.py`. Each part opens a bare
workspace of its own over the catalog of the checkout; an attempt is a row of its progress database,
as `cstudy start` leaves one. Playwright and its engines are set up as `tests/browsers.py` says;
without them the test is skipped.
"""

import json
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.config import DEFAULT_PROGRESS_DB
from coding_study.domain.problem import Language
from coding_study.domain.taxonomy import PATTERNS
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 30_000
WINDOW = {"width": 1440, "height": 900}
LISTED = ".listing:not([aria-busy]) table.problems"
ROWS = f"{LISTED} tbody tr"
SLUGS = "table.problems tbody .slug"
SEARCH = "#filter-search"
COMMAND = ".command-text"
TWO_SUM = "two-sum"
TEXT = "two"


@contextmanager
def opened_page(engine: str, workspace: Path, problems: list[str]) -> Iterator[Any]:
    """The Problems view of a server on `workspace`, logged in, its table drawn."""
    with (
        running_server(workspace) as server,
        sync_api.sync_playwright() as playwright,
    ):
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport=WINDOW), problems)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(ROWS)
        yield page
        browser.close()


def bare_workspace(factory: pytest.TempPathFactory, name: str) -> Path:
    return Path(mark_workspace(factory.mktemp(name) / "workspace"))


def listed_slugs(workspace: Path, *flags: str) -> list[str]:
    """What `cstudy list --json` lists with these flags."""
    done = subprocess.run(
        [sys.executable, "-m", "coding_study", "list", *flags, "--json"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry["slug"] for entry in json.loads(done.stdout)["entries"]]


def start_an_attempt(workspace: Path, slug: str, language: Language = Language.PYTHON) -> int:
    store = SqliteProgressStore(workspace / DEFAULT_PROGRESS_DB)
    return store.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, datetime.now(UTC))).id


def slugs_shown(page: Any) -> list[str]:
    return page.locator(SLUGS).all_inner_texts()


def wait_for_rows(page: Any, count: int) -> None:
    sync_api.expect(page.locator(ROWS)).to_have_count(count)


# P1: search


@dataclass
class Search:
    all_rows: int = 0
    cli_slugs: list[str] = field(default_factory=list[str])
    narrowed: list[str] = field(default_factory=list[str])
    requests_while_typing: int = -1
    fragment: str = ""
    command: str = ""
    reloaded: list[str] = field(default_factory=list[str])
    reloaded_value: str = ""
    focused_by_slash: str = ""
    slash_typed_in_search: str = ""
    slash_elsewhere: str = ""
    focus_from_a_select: str = ""
    with_a_filter_fragment: str = ""
    nothing_found: str = ""
    after_clearing: int = 0
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def search(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Search:
    seen = Search()
    workspace = bare_workspace(tmp_path_factory, f"search-{engine}")
    seen.cli_slugs = listed_slugs(workspace, "--search", TEXT)
    with opened_page(engine, workspace, seen.problems) as page:
        seen.all_rows = page.locator(ROWS).count()
        _narrow(page, seen)
        _reload(page, seen)
        _slash(page, seen)
        _with_another_filter(page, seen)
        _nothing_found(page, seen)
    return seen


def _narrow(page: Any, seen: Search) -> None:
    asked: list[str] = []
    page.on("request", lambda request: asked.append(request.url))
    page.locator(SEARCH).press_sequentially(TEXT)
    wait_for_rows(page, len(seen.cli_slugs))
    seen.requests_while_typing = len([url for url in asked if "/api/v1/" in url])
    seen.narrowed = slugs_shown(page)
    seen.fragment = page.evaluate("location.hash")
    seen.command = page.locator(COMMAND).inner_text()


def _reload(page: Any, seen: Search) -> None:
    page.reload()
    page.wait_for_selector(ROWS)
    seen.reloaded = slugs_shown(page)
    seen.reloaded_value = page.locator(SEARCH).input_value()


def _slash(page: Any, seen: Search) -> None:
    page.locator(SEARCH).fill("")
    page.locator(COMMAND).click()
    page.keyboard.press("/")
    seen.focused_by_slash = page.evaluate("document.activeElement?.id")
    seen.slash_elsewhere = page.locator(SEARCH).input_value()
    page.keyboard.press("/")
    seen.slash_typed_in_search = page.locator(SEARCH).input_value()
    page.locator(SEARCH).fill("")
    page.focus("#filter-status")
    page.keyboard.press("/")
    seen.focus_from_a_select = page.evaluate("document.activeElement?.id")


def _with_another_filter(page: Any, seen: Search) -> None:
    page.locator(SEARCH).fill(TEXT)
    page.select_option("#filter-difficulty", "easy")
    page.wait_for_function(
        "text => document.querySelector('.command-text')?.textContent.includes(text)",
        arg="--difficulty easy",
    )
    page.wait_for_selector(ROWS)
    seen.with_a_filter_fragment = page.evaluate("location.hash")
    page.evaluate("location.hash = '#/'")
    page.wait_for_function("() => document.querySelector('#filter-search')?.value === ''")
    page.wait_for_selector(ROWS)


def _nothing_found(page: Any, seen: Search) -> None:
    page.locator(SEARCH).fill("zebra-that-is-nowhere")
    page.wait_for_selector(".listing .state-empty")
    seen.nothing_found = page.locator(".listing .state-empty").inner_text()
    page.locator(SEARCH).fill("")
    wait_for_rows(page, seen.all_rows)
    seen.after_clearing = page.locator(ROWS).count()


def test_a_search_narrows_the_rows_to_what_cstudy_list_search_lists(search):
    assert search.narrowed == search.cli_slugs


def test_a_search_leaves_some_of_the_rows_out(search):
    assert 0 < len(search.narrowed) < search.all_rows


def test_a_search_asks_the_server_nothing_while_it_narrows(search):
    assert search.requests_while_typing == 0


def test_the_route_keeps_the_search(search):
    assert search.fragment == f"#/?search={TEXT}"


def test_the_command_strip_says_the_search(search):
    assert search.command == f"cstudy list --search {TEXT}"


def test_a_reload_shows_the_same_rows(search):
    assert search.reloaded == search.narrowed


def test_a_reload_keeps_the_text_in_the_field(search):
    assert search.reloaded_value == TEXT


def test_the_slash_key_focuses_the_search(search):
    assert search.focused_by_slash == SEARCH.removeprefix("#")


def test_the_slash_key_that_focuses_the_search_types_nothing(search):
    assert search.slash_elsewhere == ""


def test_the_slash_key_types_a_slash_in_the_search_itself(search):
    assert search.slash_typed_in_search == "/"


def test_the_slash_key_leaves_a_select_alone(search):
    assert search.focus_from_a_select == "filter-status"


def test_another_filter_keeps_the_search(search):
    assert search.with_a_filter_fragment == f"#/?difficulty=easy&search={TEXT}"


def test_a_search_nothing_holds_says_so(search):
    assert "no problems match" in search.nothing_found


def test_emptying_the_search_brings_every_row_back(search):
    assert search.after_clearing == search.all_rows


def test_searching_logs_no_problem(search):
    assert search.problems == []


# P2: the filter row, its chips, the count and Clear


FILTER_ROW = "form.filters"
SUMMARY = ".filter-summary"
CHIPS = f"{SUMMARY} .filter-chip"
COUNT = f"{SUMMARY} .filter-count"
CLEAR = f"{SUMMARY} .clear"
MORE = ".filter-more"
MORE_SUMMARY = f"{MORE} > summary"
FIRST_RANK_KEYS = ("status", "difficulty", "domain", "lang")
MORE_KEYS = ("track", "kind", "role", "scope", "pattern", "content", "set")
DOMAIN, LANGUAGE, SCOPE = "backend", "typescript", "function"
PATTERN = "arrays-hashing"
FILTERED_ROUTE = f"#/?lang={LANGUAGE}&domain={DOMAIN}"
FILTERED_COMMAND = f"cstudy list --lang {LANGUAGE} --domain {DOMAIN}"
FOCUSED = "document.activeElement?.id"
COMMAND_IS = "expected => document.querySelector('.command-text')?.textContent === expected"
SUBPIXEL = 1.0
ROW_HEIGHT_PX = 40


@dataclass
class FilterRow:
    total: int = 0
    cli_slugs: list[str] = field(default_factory=list[str])
    searched: list[str] = field(default_factory=list[str])
    row_height: float = 0
    first_rank_visible: list[bool] = field(default_factory=list[bool])
    more_visible_when_closed: list[bool] = field(default_factory=list[bool])
    more_visible_when_open: list[bool] = field(default_factory=list[bool])
    pattern_tag: str = ""
    pattern_choices: list[str] = field(default_factory=list[str])
    summary_at_rest: bool = True
    summary_height_at_rest: float = -1
    clear_at_rest: bool = True
    chips: list[str] = field(default_factory=list[str])
    chip_words: str = ""
    count: str = ""
    rows: list[str] = field(default_factory=list[str])
    fragment: str = ""
    command: str = ""
    reloaded_chips: list[str] = field(default_factory=list[str])
    reloaded_rows: list[str] = field(default_factory=list[str])
    reloaded_choices: list[str] = field(default_factory=list[str])
    more_stays_open: bool = False
    focus_in_more: str = ""
    chip_of_more: list[str] = field(default_factory=list[str])
    closed_by_escape: bool = False
    focus_after_escape: str = ""
    closed_by_a_click_outside: bool = False
    chips_after_removing: list[str] = field(default_factory=list[str])
    fragment_after_removing: str = ""
    focus_after_removing: str = ""
    focus_after_removing_the_last: str = ""
    summary_after_clearing: bool = True
    fragment_after_clearing: str = ""
    rows_after_clearing: int = 0
    focus_after_clearing: str = ""
    search_alone_chips: int = -1
    search_alone_count: str = ""
    search_alone_clear: bool = False
    pattern_command: str = ""
    unknown_chip: list[str] = field(default_factory=list[str])
    unknown_choice: str = ""
    problems: list[str] = field(default_factory=list[str])
    problems_before_a_refusal: list[str] = field(default_factory=list[str])
    """`cstudy next` refuses a pattern outside the taxonomy, which a browser logs."""


@pytest.fixture(scope="module")
def filter_row(engine: str, tmp_path_factory: pytest.TempPathFactory) -> FilterRow:
    seen = FilterRow()
    workspace = bare_workspace(tmp_path_factory, f"filters-{engine}")
    seen.cli_slugs = listed_slugs(workspace, "--lang", LANGUAGE, "--domain", DOMAIN)
    seen.searched = listed_slugs(workspace, "--search", TEXT)
    with opened_page(engine, workspace, seen.problems) as page:
        seen.total = page.locator(ROWS).count()
        _read_the_row_at_rest(page, seen)
        _open_more(page, seen)
        _choose_filters(page, seen)
        _reload_the_filters(page, seen)
        _choose_in_more(page, seen)
        _close_more(page, seen)
        _remove_chips(page, seen)
        _clear(page, seen)
        _search_alone(page, seen)
        _pattern(page, seen)
    return seen


def _read_the_row_at_rest(page: Any, seen: FilterRow) -> None:
    seen.row_height = page.locator(FILTER_ROW).evaluate("e => e.getBoundingClientRect().height")
    seen.first_rank_visible = [page.locator(f"#filter-{key}").is_visible() for key in FIRST_RANK_KEYS]
    seen.more_visible_when_closed = [page.locator(f"#filter-{key}").is_visible() for key in MORE_KEYS]
    seen.summary_at_rest = page.locator(SUMMARY).is_visible()
    seen.summary_height_at_rest = page.locator(SUMMARY).evaluate(
        "e => e.getBoundingClientRect().height"
    )
    seen.clear_at_rest = page.locator(CLEAR).is_visible()


def _open_more(page: Any, seen: FilterRow) -> None:
    page.click(MORE_SUMMARY)
    seen.more_visible_when_open = [page.locator(f"#filter-{key}").is_visible() for key in MORE_KEYS]
    pattern = page.locator("#filter-pattern")
    seen.pattern_tag = pattern.evaluate("e => e.tagName")
    seen.pattern_choices = pattern.locator("option").evaluate_all(
        "options => options.map(option => option.value)"
    )
    page.click(MORE_SUMMARY)


def _choose(page: Any, key: str, value: str, command: str) -> None:
    page.select_option(f"#filter-{key}", value)
    page.wait_for_function(COMMAND_IS, arg=command)
    page.wait_for_selector(ROWS)


def _choose_filters(page: Any, seen: FilterRow) -> None:
    _choose(page, "lang", LANGUAGE, f"cstudy list --lang {LANGUAGE}")
    _choose(page, "domain", DOMAIN, FILTERED_COMMAND)
    page.wait_for_selector(f"{COUNT}:has-text('of')")
    seen.chips = page.locator(CHIPS).all_inner_texts()
    seen.chip_words = page.locator(CHIPS).first.get_attribute("aria-label") or ""
    seen.count = page.locator(COUNT).inner_text()
    seen.rows = slugs_shown(page)
    seen.fragment = page.evaluate("location.hash")
    seen.command = page.locator(COMMAND).inner_text()


def _reload_the_filters(page: Any, seen: FilterRow) -> None:
    page.reload()
    page.wait_for_selector(ROWS)
    seen.reloaded_chips = page.locator(CHIPS).all_inner_texts()
    seen.reloaded_rows = slugs_shown(page)
    seen.reloaded_choices = [
        page.locator(f"#filter-{key}").input_value() for key in ("lang", "domain")
    ]


def _choose_in_more(page: Any, seen: FilterRow) -> None:
    page.click(MORE_SUMMARY)
    _choose(page, "scope", SCOPE, f"{FILTERED_COMMAND} --scope {SCOPE}")
    seen.more_stays_open = page.locator("#filter-scope").is_visible()
    seen.focus_in_more = page.evaluate(FOCUSED)
    seen.chip_of_more = page.locator(CHIPS).all_inner_texts()


def _close_more(page: Any, seen: FilterRow) -> None:
    page.keyboard.press("Escape")
    seen.closed_by_escape = not page.locator("#filter-scope").is_visible()
    seen.focus_after_escape = page.evaluate("document.activeElement?.tagName")
    page.click(MORE_SUMMARY)
    page.locator(COMMAND).click()
    seen.closed_by_a_click_outside = not page.locator("#filter-scope").is_visible()


def _remove_chips(page: Any, seen: FilterRow) -> None:
    page.click(f"{CHIPS}:has-text('domain')")
    page.wait_for_function(COMMAND_IS, arg=f"cstudy list --lang {LANGUAGE} --scope {SCOPE}")
    page.wait_for_selector(ROWS)
    seen.chips_after_removing = page.locator(CHIPS).all_inner_texts()
    seen.fragment_after_removing = page.evaluate("location.hash")
    seen.focus_after_removing = page.evaluate(FOCUSED)
    page.click(f"{CHIPS}:has-text('scope')")
    page.wait_for_function(COMMAND_IS, arg=f"cstudy list --lang {LANGUAGE}")
    page.wait_for_selector(ROWS)
    page.click(CHIPS)
    page.wait_for_function(COMMAND_IS, arg="cstudy list")
    page.wait_for_selector(ROWS)
    seen.focus_after_removing_the_last = page.evaluate(FOCUSED)


def _clear(page: Any, seen: FilterRow) -> None:
    _choose(page, "lang", LANGUAGE, f"cstudy list --lang {LANGUAGE}")
    page.click(CLEAR)
    page.wait_for_function(COMMAND_IS, arg="cstudy list")
    wait_for_rows(page, seen.total)
    seen.summary_after_clearing = page.locator(SUMMARY).is_visible()
    seen.fragment_after_clearing = page.evaluate("location.hash")
    seen.rows_after_clearing = page.locator(ROWS).count()
    seen.focus_after_clearing = page.evaluate(FOCUSED)


def _search_alone(page: Any, seen: FilterRow) -> None:
    page.locator(SEARCH).fill(TEXT)
    wait_for_rows(page, len(seen.searched))
    seen.search_alone_chips = page.locator(CHIPS).count()
    seen.search_alone_count = page.locator(COUNT).inner_text()
    seen.search_alone_clear = page.locator(CLEAR).is_visible()
    page.click(CLEAR)
    wait_for_rows(page, seen.total)


def _pattern(page: Any, seen: FilterRow) -> None:
    page.click(MORE_SUMMARY)
    _choose(page, "pattern", PATTERN, f"cstudy list --pattern {PATTERN}")
    seen.pattern_command = page.locator(COMMAND).inner_text()
    seen.problems_before_a_refusal = [*seen.problems]
    page.evaluate("location.hash = '#/?pattern=not-a-pattern'")
    page.wait_for_selector(".listing .state-empty")
    seen.unknown_chip = page.locator(CHIPS).all_inner_texts()
    seen.unknown_choice = page.locator("#filter-pattern").input_value()


def test_the_filters_take_one_slim_row(filter_row):
    assert filter_row.row_height <= ROW_HEIGHT_PX


def test_the_row_shows_status_difficulty_domain_and_language(filter_row):
    assert all(filter_row.first_rank_visible)


def test_more_hides_the_rest_while_it_is_closed(filter_row):
    assert not any(filter_row.more_visible_when_closed)


def test_more_holds_the_rest_once_open(filter_row):
    assert all(filter_row.more_visible_when_open)


def test_the_pattern_filter_is_a_list(filter_row):
    assert filter_row.pattern_tag == "SELECT"


def test_the_pattern_filter_offers_the_taxonomy(filter_row):
    assert filter_row.pattern_choices == ["", *PATTERNS]


def test_with_nothing_active_the_chip_row_is_not_shown(filter_row):
    assert not filter_row.summary_at_rest


def test_with_nothing_active_the_chip_row_takes_no_space(filter_row):
    assert filter_row.summary_height_at_rest == 0


def test_with_nothing_active_there_is_no_clear(filter_row):
    assert not filter_row.clear_at_rest


def test_each_active_filter_shows_as_a_chip(filter_row):
    assert [" ".join(chip.split()) for chip in filter_row.chips] == [
        f"lang: {LANGUAGE} ×",
        f"domain: {DOMAIN} ×",
    ]


def test_a_chip_says_what_it_removes(filter_row):
    assert filter_row.chip_words == f"Remove the filter lang: {LANGUAGE}"


def test_the_count_says_how_many_of_the_whole_list_show(filter_row):
    assert filter_row.count == f"{len(filter_row.cli_slugs)} of {filter_row.total}"


def test_the_rows_are_those_of_cstudy_list_with_the_same_filters(filter_row):
    assert filter_row.rows == filter_row.cli_slugs


def test_the_route_keeps_the_filters(filter_row):
    assert filter_row.fragment == FILTERED_ROUTE


def test_the_command_strip_matches_the_filters(filter_row):
    assert filter_row.command == FILTERED_COMMAND


def test_a_reload_keeps_the_chips(filter_row):
    assert filter_row.reloaded_chips == filter_row.chips


def test_a_reload_keeps_the_rows(filter_row):
    assert filter_row.reloaded_rows == filter_row.cli_slugs


def test_a_reload_keeps_the_choices(filter_row):
    assert filter_row.reloaded_choices == [LANGUAGE, DOMAIN]


def test_more_stays_open_after_a_choice_in_it(filter_row):
    assert filter_row.more_stays_open


def test_a_choice_in_more_keeps_the_focus(filter_row):
    assert filter_row.focus_in_more == "filter-scope"


def test_a_filter_in_more_shows_as_a_chip_too(filter_row):
    assert any(f"scope: {SCOPE}" in chip for chip in filter_row.chip_of_more)


def test_escape_closes_more(filter_row):
    assert filter_row.closed_by_escape


def test_escape_gives_the_focus_back_to_more(filter_row):
    assert filter_row.focus_after_escape == "SUMMARY"


def test_a_click_outside_closes_more(filter_row):
    assert filter_row.closed_by_a_click_outside


def test_a_chip_removes_its_filter_from_the_route(filter_row):
    assert filter_row.fragment_after_removing == f"#/?lang={LANGUAGE}&scope={SCOPE}"


def test_a_chip_removes_itself(filter_row):
    assert not any("domain" in chip for chip in filter_row.chips_after_removing)


def test_removing_a_chip_moves_the_focus_to_another_chip(filter_row):
    assert filter_row.focus_after_removing == "chip-scope"


def test_removing_the_last_chip_moves_the_focus_to_the_search(filter_row):
    assert filter_row.focus_after_removing_the_last == "filter-search"


def test_clear_hides_the_chip_row(filter_row):
    assert not filter_row.summary_after_clearing


def test_clear_empties_the_route(filter_row):
    assert filter_row.fragment_after_clearing == "#/"


def test_clear_shows_every_row(filter_row):
    assert filter_row.rows_after_clearing == filter_row.total


def test_clear_moves_the_focus_to_the_search(filter_row):
    assert filter_row.focus_after_clearing == "filter-search"


def test_a_search_alone_has_no_chip(filter_row):
    assert filter_row.search_alone_chips == 0


def test_a_search_alone_shows_the_count(filter_row):
    assert filter_row.search_alone_count == f"{len(filter_row.searched)} of {filter_row.total}"


def test_a_search_alone_offers_clear(filter_row):
    assert filter_row.search_alone_clear


def test_the_pattern_list_names_its_flag_in_the_command_strip(filter_row):
    assert filter_row.pattern_command == f"cstudy list --pattern {PATTERN}"


def test_a_pattern_the_list_does_not_hold_stays_chosen(filter_row):
    assert filter_row.unknown_choice == "not-a-pattern"


def test_a_pattern_the_list_does_not_hold_shows_as_a_chip(filter_row):
    assert [" ".join(chip.split()) for chip in filter_row.unknown_chip] == ["pattern: not-a-pattern ×"]


def test_filtering_logs_no_problem(filter_row):
    assert filter_row.problems_before_a_refusal == []
