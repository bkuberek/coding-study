"""The Problems view's label filters in a real browser (docs/specs/web-ui.md#problems-view), in
each engine of `tests/browsers.py`: choose a Domain, and a Role and a Scope under More, and see
the table show the rows that `cstudy list --domain X --role Y --scope Z` lists, a Scope column,
once the columns menu turns it on, that names each row's scope, the filters in the route's query
and in the command above the view, the `cstudy next` pick of the same filters on the next card, and
the filters again after a reload.

The workspace is a bare one over the catalog of the checkout, and nothing is run. Playwright and
its engines are set up as `tests/browsers.py` says; without them the test is skipped.
"""

import json
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.taxonomy import DOMAINS, JOB_ROLES, Scope
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
DOMAIN, ROLE, SCOPE = "backend", "platform", "function"
FLAGS = ("--domain", DOMAIN, "--role", ROLE, "--scope", SCOPE)
FILTERED_COMMAND = f"cstudy list {' '.join(FLAGS)}"
FILTERED_NEXT = f"cstudy next {' '.join(FLAGS)}"
FILTERED_QUERY = f"#/?domain={DOMAIN}&role={ROLE}&scope={SCOPE}"
LISTED = ".listing:not([aria-busy]) table.problems"
SLUGS = "table.problems tbody tr .slug"
SCOPE_CELLS = "table.problems tbody tr td[data-column=scope]"
COMMAND = ".command-text"
MORE = ".filter-more > summary"
NEXT_SLUG = ".next-card a.next-slug"
NEXT_START = ".next-card .next-start"
COMMAND_IS = "expected => document.querySelector('.command-text')?.textContent === expected"


@dataclass
class Visit:
    """What the browser saw of the Problems view with and without the label filters."""

    cli_slugs: list[str] = field(default_factory=list[str])
    cli_pick: str = ""
    unfiltered_rows: int = 0
    domain_choices: list[str] = field(default_factory=list[str])
    role_choices: list[str] = field(default_factory=list[str])
    scope_choices: list[str] = field(default_factory=list[str])
    headers: list[str] = field(default_factory=list[str])
    rows: list[str] = field(default_factory=list[str])
    scopes: list[str] = field(default_factory=list[str])
    fragment: str = ""
    command: str = ""
    pick: str = ""
    next_start: str = ""
    reloaded_rows: list[str] = field(default_factory=list[str])
    reloaded_choices: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"labels-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, workspace: Path, server: RunningServer) -> Visit:
    seen = Visit()
    _read_the_cli(workspace, seen)
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(LISTED)
        _read_the_unfiltered_list(page, seen)
        _filter(page)
        _read_the_filtered_list(page, seen)
        _reload(page, seen)
        browser.close()
    return seen


def _cstudy(workspace: Path, *arguments: str) -> Any:
    """The JSON document of a `cstudy` command run as the server runs, in the same checkout."""
    done = subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments, "--json"],
        env=served_environment(workspace),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)


def _read_the_cli(workspace: Path, seen: Visit) -> None:
    listing = _cstudy(workspace, "list", *FLAGS)
    seen.cli_slugs = [entry["slug"] for entry in listing["entries"]]
    seen.cli_pick = _cstudy(workspace, "next", *FLAGS)["slug"]


def _read_the_unfiltered_list(page: Any, seen: Visit) -> None:
    seen.unfiltered_rows = page.locator(SLUGS).count()
    page.click(".columns-menu > summary")
    page.check("#column-scope")
    page.wait_for_selector("table.problems thead th:has-text('scope')")
    page.keyboard.press("Escape")
    seen.headers = page.locator("table.problems thead th").all_text_contents()
    for key, choices in (
        ("domain", seen.domain_choices),
        ("role", seen.role_choices),
        ("scope", seen.scope_choices),
    ):
        choices.extend(_choices(page, key))


def _choices(page: Any, key: str) -> list[str]:
    return page.locator(f"#filter-{key} option").all_text_contents()


def _filter(page: Any) -> None:
    """Chooses the three filters one after the other, as a user does; each choice draws the view
    again, with the filters so far in the command above it."""
    page.select_option("#filter-domain", DOMAIN)
    page.wait_for_function(COMMAND_IS, arg=f"cstudy list --domain {DOMAIN}")
    page.wait_for_selector(LISTED)
    page.click(MORE)
    for key, value, command in (
        ("role", ROLE, f"cstudy list --domain {DOMAIN} --role {ROLE}"),
        ("scope", SCOPE, FILTERED_COMMAND),
    ):
        page.select_option(f"#filter-{key}", value)
        page.wait_for_function(COMMAND_IS, arg=command)
        page.wait_for_selector(LISTED)
    page.wait_for_selector(NEXT_SLUG)


def _read_the_filtered_list(page: Any, seen: Visit) -> None:
    seen.rows = page.locator(SLUGS).all_inner_texts()
    seen.scopes = page.locator(SCOPE_CELLS).all_inner_texts()
    seen.fragment = page.evaluate("() => location.hash")
    seen.command = page.locator(COMMAND).inner_text()
    seen.pick = page.locator(NEXT_SLUG).inner_text()
    seen.next_start = page.locator(NEXT_START).inner_text()


def _reload(page: Any, seen: Visit) -> None:
    page.reload()
    page.wait_for_selector(LISTED)
    page.wait_for_selector(NEXT_SLUG)
    seen.reloaded_rows = page.locator(SLUGS).all_inner_texts()
    seen.reloaded_choices = [
        page.locator(f"#filter-{key}").input_value() for key in ("domain", "role", "scope")
    ]


def test_the_table_shows_the_rows_cstudy_list_lists_for_the_same_filters(visit):
    assert visit.rows == visit.cli_slugs


def test_the_filters_leave_some_of_the_rows_out(visit):
    assert 0 < len(visit.rows) < visit.unfiltered_rows


def test_the_table_has_a_scope_column(visit):
    assert "scope" in visit.headers


def test_the_scope_column_names_the_scope_of_each_row(visit):
    assert visit.scopes == [SCOPE] * len(visit.rows)


def test_the_filters_offer_the_values_of_the_labels(visit):
    assert (visit.domain_choices, visit.role_choices, visit.scope_choices) == (
        ["domain", *DOMAINS],
        ["any", *JOB_ROLES],
        ["any", *(scope.value for scope in Scope)],
    )


def test_the_filters_are_kept_in_the_routes_query(visit):
    assert visit.fragment == FILTERED_QUERY


def test_the_command_above_the_view_is_the_cstudy_list_command(visit):
    assert visit.command == FILTERED_COMMAND


def test_the_next_card_shows_the_pick_of_cstudy_next_for_the_same_filters(visit):
    assert visit.pick == visit.cli_pick


def test_the_next_card_names_the_cstudy_next_command_with_the_filters(visit):
    assert FILTERED_NEXT in visit.next_start


def test_a_reload_shows_the_same_rows(visit):
    assert visit.reloaded_rows == visit.cli_slugs


def test_a_reload_keeps_the_choices(visit):
    assert visit.reloaded_choices == [DOMAIN, ROLE, SCOPE]


def test_the_page_logs_no_error_while_filtering(visit):
    assert visit.errors == []
