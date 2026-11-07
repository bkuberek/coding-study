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
ROW_HEIGHT_PX = 40
REMOVE_MARK = "\N{MULTIPLICATION SIGN}"
NO_VALUE = "\N{EN DASH}"


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
    seen.first_rank_visible = [
        page.locator(f"#filter-{key}").is_visible() for key in FIRST_RANK_KEYS
    ]
    seen.more_visible_when_closed = [
        page.locator(f"#filter-{key}").is_visible() for key in MORE_KEYS
    ]
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
        f"lang: {LANGUAGE} {REMOVE_MARK}",
        f"domain: {DOMAIN} {REMOVE_MARK}",
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
    assert [" ".join(chip.split()) for chip in filter_row.unknown_chip] == [
        f"pattern: not-a-pattern {REMOVE_MARK}"
    ]


def test_filtering_logs_no_problem(filter_row):
    assert filter_row.problems_before_a_refusal == []


# P3: the columns menu


COLUMNS_MENU = ".columns-menu"
COLUMNS_SUMMARY = f"{COLUMNS_MENU} > summary"
HEADERS = "table.problems thead th"
DEFAULT_HEADERS = ["id", "problem", "difficulty", "pattern", "status", "due", "languages"]
OPTIONAL_COLUMNS = ["kind", "scope", "domain", "role", "sets"]
PREFERENCES_FILE = ".cs/serve/preferences.json"
NARROW = {"width": 390, "height": 844}
PAGE_FITS = "document.documentElement.scrollWidth <= window.innerWidth"


@dataclass
class Columns:
    defaults: list[str] = field(default_factory=list[str])
    offered: list[str] = field(default_factory=list[str])
    locked: list[str] = field(default_factory=list[str])
    added: list[str] = field(default_factory=list[str])
    domain_cell: str = ""
    role_cell: str = ""
    kind_cell: str = ""
    menu_open_after_a_choice: bool = False
    focus_after_a_choice: str = ""
    stored_after_adding: list[str] = field(default_factory=list[str])
    reloaded: list[str] = field(default_factory=list[str])
    reloaded_ticks: dict[str, bool] = field(default_factory=dict[str, bool])
    without_a_column: list[str] = field(default_factory=list[str])
    controls_by_default: int = -1
    controls_with_sets: int = 0
    after_reset: list[str] = field(default_factory=list[str])
    stored_after_reset: list[str] = field(default_factory=list[str])
    narrow_headers: list[str] = field(default_factory=list[str])
    narrow_page_fits: bool = False
    narrow_box_scrolls: bool = False
    narrow_last_column_reachable: bool = False
    narrow_menu_fits: bool = False
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def columns(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Columns:
    seen = Columns()
    workspace = bare_workspace(tmp_path_factory, f"columns-{engine}")
    with opened_page(engine, workspace, seen.problems) as page:
        seen.defaults = _headers(page)
        seen.controls_by_default = page.locator(".set-control").count()
        _read_the_menu(page, seen)
        _add_columns(page, workspace, seen)
        _reload_the_columns(page, seen)
        _hide_a_column(page, seen)
        _narrow_window(page, seen)
        _reset_the_columns(page, workspace, seen)
    return seen


def _headers(page: Any) -> list[str]:
    return page.locator(HEADERS).all_text_contents()


def _stored_columns(workspace: Path) -> list[str]:
    return json.loads((workspace / PREFERENCES_FILE).read_text())["problem_columns"]


def _read_the_menu(page: Any, seen: Columns) -> None:
    page.click(COLUMNS_SUMMARY)
    boxes = page.locator(f"{COLUMNS_MENU} input[type=checkbox]")
    seen.offered = boxes.evaluate_all("found => found.map(box => box.value)")
    seen.locked = boxes.evaluate_all(
        "found => found.filter(box => box.disabled).map(box => box.value)"
    )


def _cell(page: Any, column: str) -> str:
    return page.locator(
        f"{ROWS}:has(a[href='#/problems/{TWO_SUM}']) td[data-column={column}]"
    ).inner_text()


def _tick(page: Any, column: str) -> None:
    page.check(f"#column-{column}")
    page.wait_for_selector(f"{HEADERS}:has-text('{column}')")


def _add_columns(page: Any, workspace: Path, seen: Columns) -> None:
    for column in ("kind", "domain", "role", "sets"):
        _tick(page, column)
    seen.added = _headers(page)
    seen.domain_cell = _cell(page, "domain")
    seen.role_cell = _cell(page, "role")
    seen.kind_cell = _cell(page, "kind")
    seen.controls_with_sets = page.locator(".set-control").count()
    seen.menu_open_after_a_choice = page.locator("#column-kind").is_visible()
    seen.focus_after_a_choice = page.evaluate(FOCUSED)
    seen.stored_after_adding = _stored_columns(workspace)


def _reload_the_columns(page: Any, seen: Columns) -> None:
    page.reload()
    page.wait_for_selector(ROWS)
    seen.reloaded = _headers(page)
    seen.reloaded_ticks = {
        column: page.locator(f"#column-{column}").is_checked()
        for column in ("kind", "domain", "scope", "id")
    }


def _hide_a_column(page: Any, seen: Columns) -> None:
    page.click(COLUMNS_SUMMARY)
    page.uncheck("#column-id")
    page.wait_for_function(
        "() => ![...document.querySelectorAll('table.problems thead th')]"
        ".some((cell) => cell.textContent === 'id')"
    )
    seen.without_a_column = _headers(page)
    page.keyboard.press("Escape")


def _narrow_window(page: Any, seen: Columns) -> None:
    page.set_viewport_size(NARROW)
    page.wait_for_selector(ROWS)
    seen.narrow_headers = _headers(page)
    seen.narrow_page_fits = page.evaluate(PAGE_FITS)
    box = page.locator(".listing")
    seen.narrow_box_scrolls = box.evaluate("e => e.scrollWidth > e.clientWidth")
    page.locator(f"{ROWS} .set-control").first.scroll_into_view_if_needed()
    seen.narrow_last_column_reachable = page.locator(f"{ROWS} .set-control").first.is_visible()
    page.click(COLUMNS_SUMMARY)
    seen.narrow_menu_fits = page.evaluate(PAGE_FITS)
    page.keyboard.press("Escape")
    page.set_viewport_size(WINDOW)


def _reset_the_columns(page: Any, workspace: Path, seen: Columns) -> None:
    page.click(COLUMNS_SUMMARY)
    page.click(f"{COLUMNS_MENU} button:has-text('Reset to defaults')")
    page.wait_for_function(
        "count => document.querySelectorAll('table.problems thead th').length === count",
        arg=len(DEFAULT_HEADERS),
    )
    seen.after_reset = _headers(page)
    seen.stored_after_reset = _stored_columns(workspace)


def test_the_table_shows_the_default_columns(columns):
    assert columns.defaults == DEFAULT_HEADERS


def test_the_menu_offers_every_column(columns):
    assert set(columns.offered) == {*DEFAULT_HEADERS, *OPTIONAL_COLUMNS}


def test_problem_and_status_cannot_be_hidden(columns):
    assert set(columns.locked) == {"problem", "status"}


def test_a_ticked_column_shows_in_the_table(columns):
    assert {"kind", "domain", "role", "sets"} <= set(columns.added)


def test_the_columns_keep_their_order_whatever_was_ticked_first(columns):
    assert columns.added.index("kind") < columns.added.index("domain") < columns.added.index("role")


def test_the_domain_column_names_the_domains(columns):
    assert "algorithms" in columns.domain_cell


def test_the_role_column_names_the_roles(columns):
    assert columns.role_cell not in ("", NO_VALUE)


def test_the_kind_column_names_the_kind(columns):
    assert columns.kind_cell == "function"


def test_the_add_to_set_control_is_a_column_that_is_off_by_default(columns):
    assert columns.controls_by_default == 0


def test_the_add_to_set_control_stays_reachable_through_the_menu(columns):
    assert columns.controls_with_sets > 0


def test_the_menu_stays_open_while_columns_are_ticked(columns):
    assert columns.menu_open_after_a_choice


def test_a_tick_keeps_the_focus(columns):
    assert columns.focus_after_a_choice == "column-sets"


def test_the_choice_is_stored_in_the_preferences_file(columns):
    assert {"kind", "domain", "role", "sets"} <= set(columns.stored_after_adding)


def test_the_columns_survive_a_reload(columns):
    assert columns.reloaded == columns.added


def test_the_menu_reads_the_stored_columns_after_a_reload(columns):
    assert columns.reloaded_ticks == {"kind": True, "domain": True, "scope": False, "id": True}


def test_an_unticked_column_leaves_the_table(columns):
    assert "id" not in columns.without_a_column


def test_reset_shows_the_default_columns(columns):
    assert columns.after_reset == DEFAULT_HEADERS


def test_reset_stores_the_default_columns(columns):
    assert columns.stored_after_reset == DEFAULT_HEADERS


def test_a_narrow_window_keeps_every_chosen_column(columns):
    assert columns.narrow_headers == columns.without_a_column


def test_a_narrow_window_does_not_scroll_sideways(columns):
    assert columns.narrow_page_fits


def test_a_narrow_window_scrolls_the_table_in_its_box(columns):
    assert columns.narrow_box_scrolls


def test_a_narrow_window_reaches_the_last_column(columns):
    assert columns.narrow_last_column_reachable


def test_a_narrow_window_fits_the_open_menu(columns):
    assert columns.narrow_menu_fits


def test_choosing_columns_logs_no_problem(columns):
    assert columns.problems == []


# P4: the rows


LINK = "a.problem-link"
PROBLEM_HASH = f"#/problems/{TWO_SUM}"
ROW = f"{ROWS}:has({LINK}[href='{PROBLEM_HASH}'])"
TITLE = "Two Sum"
OTHER_SLUG = "valid-anagram"
BACK_HOME = "location.hash = '#/'"
LINK_STYLE = """link => {
  const style = getComputedStyle(link);
  return { color: style.color, underline: style.textDecorationLine };
}"""
ACCENT = "getComputedStyle(document.documentElement).getPropertyValue('--accent')"
AS_RGB = """value => {
  const probe = document.createElement("span");
  probe.style.color = value;
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
}"""
CELL_BOTTOMS = (
    """row => [...row.querySelectorAll("td")].map((cell) => cell.getBoundingClientRect().bottom)"""
)
BACKGROUND = "row => getComputedStyle(row).backgroundColor"


@dataclass
class Rows:
    headers: list[str] = field(default_factory=list[str])
    title_text: str = ""
    link_href: str = ""
    slug_text: str = ""
    slug_is_quieter: bool = False
    slug_is_smaller: bool = False
    accent: str = ""
    link_style: dict[str, str] = field(default_factory=dict[str, str])
    underlined_links_at_rest: int = -1
    cell_bottoms: list[float] = field(default_factory=list[float])
    title_cell_display: str = ""
    after_a_click_on_the_row: str = ""
    after_enter_on_the_link: str = ""
    focused_row_stands_out: bool = False
    tab_of_a_middle_click: str = ""
    tab_of_a_modified_click: str = ""
    hash_after_a_modified_click: str = ""
    hash_after_selecting_text: str = ""
    hash_after_the_set_control: str = ""
    dialog_after_the_set_control: bool = False
    status_link: str = ""
    status_link_target: str = ""
    status_link_name: str = ""
    other_link: list[str] = field(default_factory=list[str])
    other_link_target: list[str] = field(default_factory=list[str])
    after_the_status_link: str = ""
    attempts: dict[str, int] = field(default_factory=dict[str, int])
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def rows(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Rows:
    seen = Rows()
    workspace = bare_workspace(tmp_path_factory, f"rows-{engine}")
    seen.attempts = {
        "python": start_an_attempt(workspace, OTHER_SLUG),
        "typescript": start_an_attempt(workspace, OTHER_SLUG, Language.TYPESCRIPT),
    }
    with opened_page(engine, workspace, seen.problems) as page:
        _read_a_row(page, seen)
        _click_the_row(page, seen)
        _keyboard(page, seen)
        _other_clicks(page, seen)
        _inner_controls(page, seen)
        _status_links(page, seen)
    return seen


def _read_a_row(page: Any, seen: Rows) -> None:
    seen.headers = page.locator(HEADERS).all_text_contents()
    link = page.locator(f"{ROW} {LINK}")
    seen.title_text = link.inner_text()
    seen.link_href = link.get_attribute("href") or ""
    slug = page.locator(f"{ROW} .slug")
    seen.slug_text = slug.inner_text()
    seen.slug_is_quieter = slug.evaluate("e => getComputedStyle(e).color") != link.evaluate(
        "e => getComputedStyle(e).color"
    )
    seen.slug_is_smaller = float(
        slug.evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
    ) < float(link.evaluate("e => parseFloat(getComputedStyle(e).fontSize)"))
    seen.link_style = link.evaluate(LINK_STYLE)
    seen.accent = page.evaluate(AS_RGB, page.evaluate(ACCENT).strip())
    seen.underlined_links_at_rest = page.locator(LINK).evaluate_all(
        "found => found.filter((link) => "
        "getComputedStyle(link).textDecorationLine.includes('underline')).length"
    )
    seen.cell_bottoms = page.locator(ROW).evaluate(CELL_BOTTOMS)
    seen.title_cell_display = page.locator(f"{ROW} td[data-column=problem]").evaluate(
        "e => getComputedStyle(e).display"
    )


def _home(page: Any) -> None:
    page.evaluate(BACK_HOME)
    page.wait_for_selector(ROW)


def _click_the_row(page: Any, seen: Rows) -> None:
    page.click(f"{ROW} td[data-column=difficulty]")
    page.wait_for_function("expected => location.hash === expected", arg=PROBLEM_HASH)
    seen.after_a_click_on_the_row = page.evaluate("location.hash")
    _home(page)


def _keyboard(page: Any, seen: Rows) -> None:
    page.mouse.move(0, 0)
    resting = page.locator(ROW).evaluate(BACKGROUND)
    page.focus(f"{ROW} {LINK}")
    seen.focused_row_stands_out = page.locator(ROW).evaluate(BACKGROUND) != resting
    page.keyboard.press("Enter")
    page.wait_for_function("expected => location.hash === expected", arg=PROBLEM_HASH)
    seen.after_enter_on_the_link = page.evaluate("location.hash")
    _home(page)


def _other_clicks(page: Any, seen: Rows) -> None:
    with page.context.expect_page() as middle:
        page.click(f"{ROW} {LINK}", button="middle")
    seen.tab_of_a_middle_click = middle.value.url.split("#")[-1]
    middle.value.close()
    with page.context.expect_page() as modified:
        page.click(f"{ROW} td[data-column=difficulty]", modifiers=["ControlOrMeta"])
    seen.tab_of_a_modified_click = modified.value.url.split("#")[-1]
    modified.value.close()
    seen.hash_after_a_modified_click = page.evaluate("location.hash")
    slug = page.locator(f"{ROW} .slug").bounding_box()
    assert slug is not None
    middle_of_slug = slug["y"] + slug["height"] / 2
    page.mouse.move(slug["x"] + 1, middle_of_slug)
    page.mouse.down()
    page.mouse.move(slug["x"] + slug["width"] - 1, middle_of_slug, steps=4)
    page.mouse.up()
    seen.hash_after_selecting_text = page.evaluate("location.hash")


def _inner_controls(page: Any, seen: Rows) -> None:
    page.click(COLUMNS_SUMMARY)
    page.check("#column-sets")
    page.keyboard.press("Escape")
    page.click(f"{ROW} .set-control")
    page.wait_for_selector("dialog.sheet[open]")
    seen.dialog_after_the_set_control = True
    seen.hash_after_the_set_control = page.evaluate("location.hash")
    page.keyboard.press("Escape")
    page.wait_for_selector("dialog.sheet[open]", state="detached")


def _status_links(page: Any, seen: Rows) -> None:
    links = page.locator(f"{ROWS}:has(a[href='#/problems/{OTHER_SLUG}']) td[data-column=status] a")
    first = links.first
    seen.status_link = first.text_content() or ""
    seen.status_link_target = first.get_attribute("href") or ""
    seen.status_link_name = first.get_attribute("aria-label") or ""
    others = links.all()[1:]
    seen.other_link = [link.text_content() or "" for link in others]
    seen.other_link_target = [link.get_attribute("href") or "" for link in others]
    first.click()
    page.wait_for_function("expected => location.hash === expected", arg=seen.status_link_target)
    seen.after_the_status_link = page.evaluate("location.hash")


def test_in_progress_is_not_a_column(rows):
    assert "in progress" not in rows.headers


def test_a_row_leads_with_the_title(rows):
    assert rows.title_text == TITLE


def test_the_title_is_the_link_to_the_problem(rows):
    assert rows.link_href == PROBLEM_HASH


def test_the_slug_follows_it(rows):
    assert rows.slug_text == TWO_SUM


def test_the_slug_is_quieter_in_colour(rows):
    assert rows.slug_is_quieter


def test_the_slug_is_quieter_in_size(rows):
    assert rows.slug_is_smaller


def test_the_link_is_not_the_accent_colour_at_rest(rows):
    assert rows.link_style["color"] != rows.accent


def test_no_title_is_underlined_at_rest(rows):
    assert rows.underlined_links_at_rest == 0


def test_the_title_cell_stays_a_table_cell(rows):
    assert rows.title_cell_display == "table-cell"


def test_the_rule_under_a_row_is_one_line(rows):
    assert len(set(rows.cell_bottoms)) == 1


def test_a_click_on_the_row_opens_the_problem(rows):
    assert rows.after_a_click_on_the_row == PROBLEM_HASH


def test_enter_on_the_link_opens_the_problem(rows):
    assert rows.after_enter_on_the_link == PROBLEM_HASH


def test_a_row_stands_out_while_its_link_has_the_focus(rows):
    assert rows.focused_row_stands_out


def test_a_middle_click_on_the_link_opens_a_tab(rows):
    assert rows.tab_of_a_middle_click == f"/problems/{TWO_SUM}"


def test_a_modified_click_on_the_row_opens_a_tab(rows):
    assert rows.tab_of_a_modified_click == f"/problems/{TWO_SUM}"


def test_a_modified_click_on_the_row_stays_on_the_list(rows):
    assert rows.hash_after_a_modified_click == "#/"


def test_selecting_text_in_a_row_does_not_open_the_problem(rows):
    assert rows.hash_after_selecting_text == "#/"


def test_a_control_in_a_row_does_what_it_does(rows):
    assert rows.dialog_after_the_set_control


def test_a_control_in_a_row_does_not_open_the_problem(rows):
    assert rows.hash_after_the_set_control == "#/"


def test_in_progress_is_a_link_to_the_attempt(rows):
    assert rows.status_link_target == f"#/attempts/{rows.attempts['python']}"


def test_in_progress_reads_as_the_status_does(rows):
    assert "in progress" in rows.status_link


def test_in_progress_tells_a_screen_reader_it_resumes(rows):
    assert rows.status_link_name == f"in progress: resume {OTHER_SLUG} in python"


def test_another_attempt_of_the_problem_gets_a_link_of_its_own(rows):
    assert rows.other_link_target == [f"#/attempts/{rows.attempts['typescript']}"]


def test_another_attempt_names_its_language(rows):
    assert ["typescript" in link for link in rows.other_link] == [True]


def test_in_progress_opens_the_attempt(rows):
    assert rows.after_the_status_link == f"#/attempts/{rows.attempts['python']}"


def test_the_rows_log_no_problem(rows):
    assert rows.problems == []


# P5: the Next panel


CARD = ".next-card"
ACTION = f"{CARD} .next-action"
SHEET = "dialog.sheet[open]"
PANEL_HEIGHT_PX = 76
REVIEW_PICK = {
    "pick": "review",
    "slug": TWO_SUM,
    "title": TITLE,
    "kind": "function",
    "difficulty": "easy",
    "group": "arrays-hashing",
    "reason": "overdue 3d, interval 7d",
    "language": "python",
    "start": f"cstudy start {TWO_SUM} --lang python",
}
FONT_SIZE = "e => parseFloat(getComputedStyle(e).fontSize)"


@dataclass
class NextPanel:
    start_tag: str = ""
    start_words: str = ""
    start_is_primary: bool = False
    height: float = 0
    command: str = ""
    command_is_small: bool = False
    dialog_title: str = ""
    dialog_command: str = ""
    focus_after_escape: bool = False
    hash_after_starting: str = ""
    review_note: str = ""
    resume_tag: str = ""
    resume_words: str = ""
    resume_target: str = ""
    hash_after_resuming: str = ""
    resume_height: float = 0
    attempt: int = 0
    slash_with_a_dialog_open: str = ""
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def next_panel(engine: str, tmp_path_factory: pytest.TempPathFactory) -> NextPanel:
    seen = NextPanel()
    workspace = bare_workspace(tmp_path_factory, f"next-{engine}")
    with opened_page(engine, workspace, seen.problems) as page:
        page.wait_for_selector(ACTION)
        _read_the_start(page, seen)
        _open_the_dialog(page, seen)
        _review(page, seen)
        _start_from_the_panel(page, seen)
        _home(page)
        _resume(page, seen)
    return seen


def _read_the_start(page: Any, seen: NextPanel) -> None:
    action = page.locator(ACTION)
    seen.start_tag = action.evaluate("e => e.tagName")
    seen.start_words = action.inner_text()
    seen.start_is_primary = action.evaluate("e => e.classList.contains('primary')")
    seen.height = page.locator(CARD).evaluate("e => e.getBoundingClientRect().height")
    command = page.locator(f"{CARD} .next-start .cmd")
    seen.command = command.inner_text()
    seen.command_is_small = command.evaluate(FONT_SIZE) < page.locator(
        f"{CARD} .next-line"
    ).evaluate(FONT_SIZE)


def _open_the_dialog(page: Any, seen: NextPanel) -> None:
    page.click(ACTION)
    page.wait_for_selector(SHEET)
    seen.dialog_title = page.locator(f"{SHEET} h2").inner_text()
    seen.dialog_command = page.locator(f"{SHEET} .sheet-command").inner_text()
    page.keyboard.press("/")
    seen.slash_with_a_dialog_open = page.evaluate(FOCUSED)
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    seen.focus_after_escape = page.evaluate(
        "() => document.activeElement?.classList.contains('next-action')"
    )


def _review(page: Any, seen: NextPanel) -> None:
    page.route("**/api/v1/next*", lambda route: route.fulfill(json=REVIEW_PICK))
    page.reload()
    page.wait_for_selector(ACTION)
    page.click(ACTION)
    page.wait_for_selector(f"{SHEET} .review-note")
    seen.review_note = page.locator(f"{SHEET} .review-note").inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    page.unroute("**/api/v1/next*")
    page.reload()
    page.wait_for_selector(ACTION)


def _start_from_the_panel(page: Any, seen: NextPanel) -> None:
    page.click(ACTION)
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_function("() => location.hash.startsWith('#/attempts/')")
    seen.hash_after_starting = page.evaluate("location.hash")
    seen.attempt = int(seen.hash_after_starting.rsplit("/", 1)[-1])


def _resume(page: Any, seen: NextPanel) -> None:
    page.wait_for_selector(f"{ACTION}:has-text('Resume')")
    action = page.locator(ACTION)
    seen.resume_tag = action.evaluate("e => e.tagName")
    seen.resume_words = action.inner_text()
    seen.resume_target = action.get_attribute("href") or ""
    seen.resume_height = page.locator(CARD).evaluate("e => e.getBoundingClientRect().height")
    action.click()
    page.wait_for_function("target => location.hash === target", arg=seen.resume_target)
    seen.hash_after_resuming = page.evaluate("location.hash")


def test_the_panel_offers_a_real_start_button(next_panel):
    assert next_panel.start_tag == "BUTTON"


def test_the_button_says_it_starts_and_asks_first(next_panel):
    assert next_panel.start_words == "Start…"


def test_the_button_is_the_panels_primary_action(next_panel):
    assert next_panel.start_is_primary


def test_the_panel_is_two_lines_tall(next_panel):
    assert next_panel.height <= PANEL_HEIGHT_PX


def test_the_command_stays_beside_the_button(next_panel):
    assert next_panel.command.startswith("cstudy start ")


def test_the_command_is_small_text(next_panel):
    assert next_panel.command_is_small


def test_start_opens_the_start_dialog_of_the_pick(next_panel):
    assert next_panel.dialog_title == f"start · {next_panel.command.split()[2]}"


def test_the_dialog_names_the_command_it_runs(next_panel):
    assert next_panel.command in next_panel.dialog_command


def test_the_slash_key_stays_in_an_open_dialog(next_panel):
    assert next_panel.slash_with_a_dialog_open != SEARCH.removeprefix("#")


def test_escape_gives_the_focus_back_to_the_button(next_panel):
    assert next_panel.focus_after_escape


def test_a_review_pick_opens_the_dialog_of_a_review(next_panel):
    assert "review attempt" in next_panel.review_note


def test_the_dialog_starts_the_attempt_and_opens_it(next_panel):
    assert next_panel.attempt > 0


def test_a_resume_pick_is_a_link_in_the_look_of_a_button(next_panel):
    assert next_panel.resume_tag == "A"


def test_a_resume_pick_says_resume(next_panel):
    assert next_panel.resume_words == "Resume"


def test_resume_opens_the_attempt(next_panel):
    assert next_panel.hash_after_resuming == f"#/attempts/{next_panel.attempt}"


def test_the_resume_panel_is_two_lines_tall(next_panel):
    assert next_panel.resume_height <= PANEL_HEIGHT_PX


def test_the_panel_logs_no_problem(next_panel):
    assert next_panel.problems == []


# P6: `in progress` in the top bar


ATTEMPTS_MENU = ".attempts-menu"
ATTEMPT_LINKS = f"{ATTEMPTS_MENU} .menu-list a"
HARD_ONLY = "#/?difficulty=hard"


@dataclass
class TopBar:
    at_rest: bool = True
    at_rest_on_another_view: bool = True
    after_opening_one: bool = False
    count: str = ""
    filtered_count: str = ""
    filtered_links: int = 0
    after_ending_it: bool = True
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def top_bar(engine: str, tmp_path_factory: pytest.TempPathFactory) -> TopBar:
    seen = TopBar()
    workspace = bare_workspace(tmp_path_factory, f"bar-{engine}")
    with opened_page(engine, workspace, seen.problems) as page:
        seen.at_rest = page.locator(ATTEMPTS_MENU).is_visible()
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(".settings")
        seen.at_rest_on_another_view = page.locator(ATTEMPTS_MENU).is_visible()
        page.evaluate(BACK_HOME)
        page.wait_for_selector(ROWS)
        _open_one_elsewhere(page, workspace, seen)
        _filter_it_out(page, seen)
        _end_it_elsewhere(page, workspace, seen)
    return seen


def _open_one_elsewhere(page: Any, workspace: Path, seen: TopBar) -> None:
    """As a start in the terminal: the page hears of it, and nothing here reloads it."""
    start_an_attempt(workspace, TWO_SUM)
    page.wait_for_selector(ATTEMPTS_MENU, state="visible")
    seen.after_opening_one = page.locator(ATTEMPTS_MENU).is_visible()
    seen.count = page.locator(f"{ATTEMPTS_MENU} .count").inner_text()


def _filter_it_out(page: Any, seen: TopBar) -> None:
    """The easy problem the attempt is on is not a row of this list, and the menu still lists it."""
    page.evaluate(f"location.hash = '{HARD_ONLY}'")
    page.wait_for_selector(f"{COUNT}:has-text('of')")
    page.wait_for_selector(ROWS)
    seen.filtered_count = page.locator(f"{ATTEMPTS_MENU} .count").inner_text()
    seen.filtered_links = page.locator(ATTEMPT_LINKS).count()


def _end_it_elsewhere(page: Any, workspace: Path, seen: TopBar) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", "abort", TWO_SUM, "--yes"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    page.wait_for_selector(ATTEMPTS_MENU, state="hidden")
    seen.after_ending_it = page.locator(ATTEMPTS_MENU).is_visible()


def test_with_nothing_open_the_top_bar_has_no_menu_of_attempts(top_bar):
    assert not top_bar.at_rest


def test_with_nothing_open_no_view_shows_the_menu_of_attempts(top_bar):
    assert not top_bar.at_rest_on_another_view


def test_the_menu_shows_when_an_attempt_opens_without_a_reload(top_bar):
    assert top_bar.after_opening_one


def test_the_menu_counts_the_attempt(top_bar):
    assert top_bar.count == "1"


def test_the_filters_do_not_narrow_the_count_of_attempts(top_bar):
    assert top_bar.filtered_count == "1"


def test_the_filters_do_not_narrow_the_menu_of_attempts(top_bar):
    assert top_bar.filtered_links == 1


def test_the_menu_hides_when_the_last_attempt_ends_without_a_reload(top_bar):
    assert not top_bar.after_ending_it


def test_the_top_bar_logs_no_problem(top_bar):
    assert top_bar.problems == []
