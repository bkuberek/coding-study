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
