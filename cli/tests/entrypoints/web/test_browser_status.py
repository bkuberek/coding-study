"""A problem with an attempt in progress reads `in progress` in a real browser
(docs/specs/progress-and-scheduling.md#problem-status, docs/specs/web-ui.md#problems-view), in each
engine of `tests/browsers.py`: before the attempt the row is `new`; once an attempt is open,
`cstudy list` and the Problems view both say `in progress`, the Status filter offers it, with the
value `in_progress` that the route keeps, and lists just that problem, and the problem's Resume
link is still there.

The workspace is a bare one over the catalog of the checkout; the attempt is a row of its progress
database, as `cstudy start` leaves one. Playwright and its engines are set up as
`tests/browsers.py` says; without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
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
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
SLUG = "two-sum"
STATUS_FILTER = "#filter-status"
ROWS = ".listing:not([aria-busy]) table.problems tbody tr"
SLUGS = "table.problems tbody tr .slug"
STATUS_CELL = f"{ROWS}:has(a.problem-link[href='#/problems/{SLUG}']) td[data-column=status]"
RESUME_CELL = f"{ROWS}:has(a.problem-link[href='#/problems/{SLUG}']) td[data-column=status] a"
IN_PROGRESS = "in_progress"
IN_WORDS = "in progress"


@dataclass
class Visit:
    """What the CLI and the page said about the problem before and after its attempt began."""

    status_before: str = ""
    cli_row: str = ""
    cli_filtered: list[str] = field(default_factory=list[str])
    status_after: str = ""
    resume_links: int = 0
    choices: list[str] = field(default_factory=list[str])
    choice_labels: list[str] = field(default_factory=list[str])
    filtered_slugs: list[str] = field(default_factory=list[str])
    fragment: str = ""
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return mark_workspace(tmp_path_factory.mktemp(f"status-{engine}") / "workspace")


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, server: RunningServer, workspace: Path) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.problems)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(ROWS)
        seen.status_before = _status(page)
        _start_an_attempt(workspace)
        seen.cli_row, seen.cli_filtered = _cli(workspace)
        page.reload()
        page.wait_for_selector(ROWS)
        seen.status_after = _status(page)
        seen.resume_links = page.locator(RESUME_CELL).count()
        seen.choices = page.locator(f"{STATUS_FILTER} option").evaluate_all(
            "options => options.map(option => option.value)"
        )
        seen.choice_labels = page.locator(f"{STATUS_FILTER} option").all_inner_texts()
        page.select_option(STATUS_FILTER, IN_PROGRESS)
        sync_api.expect(page.locator(ROWS)).to_have_count(1)
        seen.filtered_slugs = page.locator(SLUGS).all_inner_texts()
        seen.fragment = page.evaluate("location.hash")
        browser.close()
    return seen


def _status(page: Any) -> str:
    return page.locator(STATUS_CELL).evaluate("cell => cell.textContent")


def _start_an_attempt(workspace: Path) -> None:
    store = SqliteProgressStore(workspace / DEFAULT_PROGRESS_DB)
    store.add_attempt(NewAttempt(SLUG, Language.PYTHON, AttemptMode.NEW, datetime.now(UTC)))


def _cli(workspace: Path) -> tuple[str, list[str]]:
    def listing(*flags: str) -> list[str]:
        done = subprocess.run(
            [sys.executable, "-m", "coding_study", "list", *flags],
            env=served_environment(workspace),
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
        return done.stdout.splitlines()[1:]

    row = next(line for line in listing() if f" {SLUG} " in line)
    return row, [line.split()[1] for line in listing("--status", "in-progress")]


def test_an_untouched_problem_reads_new(visit):
    assert visit.status_before == "○new"


def test_cstudy_list_says_in_progress_in_words_for_a_started_problem(visit):
    assert f" {IN_WORDS} " in visit.cli_row


def test_cstudy_list_filters_by_in_progress_written_with_a_hyphen(visit):
    assert visit.cli_filtered == [SLUG]


def test_the_problems_view_says_in_progress_in_words_for_a_started_problem(visit):
    assert visit.status_after == f"▸{IN_WORDS}"


def test_the_started_problem_keeps_its_resume_link(visit):
    assert visit.resume_links == 1


def test_the_status_filter_keeps_in_progress_as_the_value_of_its_option(visit):
    assert IN_PROGRESS in visit.choices


def test_the_status_filter_reads_in_progress_in_words(visit):
    assert IN_WORDS in visit.choice_labels


def test_the_status_filter_lists_just_the_started_problem(visit):
    assert visit.filtered_slugs == [SLUG]


def test_the_filter_is_kept_in_the_route_by_its_value(visit):
    assert visit.fragment == f"#/?status={IN_PROGRESS}"


def test_the_page_logs_no_problem(visit):
    assert visit.problems == []
