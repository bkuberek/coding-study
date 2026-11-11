"""Level passes in a real browser (docs/specs/progress-and-scheduling.md#level-passes): a problem
an earlier attempt passed through level 2 of 4, mastered through level 2, shows that attempt, its
best, its mastery and the level to try in the Problem view, a new attempt shows the goal in its
statement, and Done after a run through level 1 reads `passed · through level 1 of 4`; a set whose
entry targets level 2 counts it passed and names the target; in each engine of `tests/browsers.py`.

Progress is written to the workspace's progress.db as `cstudy done` and `cstudy test` would leave
it, so no code runs. Playwright and its engines are set up as `tests/browsers.py` says; without
them the test is skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import (
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import LevelReview, ReviewState, ScheduleEntry
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "tamper-evident-ledger"
LEVELS = 4
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
PRACTISE = "section[aria-labelledby=practice-heading]"
HISTORY = "section[aria-labelledby=history-heading]"
GOAL = "last time: through level 2 of 4; try level 3"
EARLIER = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
SET = "ledger-loop"
SETS_YAML = f"sets:\n  {SET}:\n    problems:\n      - {{slug: {PROBLEM}, level: 2}}\n"


@dataclass
class Viewed:
    """What the browser saw of a problem passed through level 2 of 4, then of a new attempt."""

    practise: str = ""
    badge: str = ""
    best: str = ""
    summary: str = ""
    statement: str = ""
    outcome: str = ""
    set_counts: str = ""
    set_row: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"levels-{engine}") / "workspace")
    _passed_through_level_2(SqliteProgressStore(workspace / "progress.db"))
    (workspace / "sets.yaml").write_text(SETS_YAML)
    with running_server(Path(workspace)) as running:
        yield running


def _passed_through_level_2(store: SqliteProgressStore) -> None:
    """An earlier attempt in Python, finished as `cstudy done` leaves a pass through level 2."""
    attempt = store.add_attempt(NewAttempt(PROBLEM, Language.PYTHON, AttemptMode.NEW, EARLIER))
    store.update_attempt(
        replace(
            attempt,
            status=AttemptStatus.PASSED,
            ended_at=EARLIER + timedelta(minutes=40),
            rating=Rating.OK,
            grade=Grade.OK,
            level_unlocked=3,
            levels_passed=2,
            levels_total=LEVELS,
        )
    )
    recalled = ReviewState(interval_days=45, reps=4)
    store.save_schedule_entry(
        ScheduleEntry(
            PROBLEM,
            recalled,
            date(2099, 1, 1),
            Grade.OK,
            EARLIER,
            (LevelReview(2, recalled, Grade.OK),),
        )
    )


@pytest.fixture(scope="module")
def viewed(engine: str, server: RunningServer) -> Viewed:
    seen = Viewed()
    store = SqliteProgressStore(Path(server.environment["CSTUDY_WORKSPACE"]) / "progress.db")
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        watched(page, seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate(f"location.hash = '#/sets/{SET}'")
        page.wait_for_selector("table.set-table tbody tr")
        seen.set_counts = page.locator(".set-facts .num").inner_text()
        seen.set_row = page.locator("table.set-table tbody tr").first.inner_text()
        page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
        page.wait_for_selector(".practice-actions button.primary")
        seen.practise = page.locator(PRACTISE).inner_text()
        seen.badge = page.locator(".problem-facts .badge").inner_text()
        seen.best = page.locator(f"{HISTORY} .best-line").inner_text()
        seen.summary = page.locator(f"{HISTORY} ol.attempts > li summary").first.inner_text()
        _start(page)
        seen.statement = page.locator(".brief").inner_text()
        _ran_through_level_1(store)
        seen.outcome = _done(page)
        browser.close()
    return seen


def _start(page: Any) -> None:
    page.click(".practice-actions button.primary")
    page.wait_for_selector(f"{SHEET} form")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".attempt-head .flow-actions")
    page.wait_for_selector(".brief blockquote")


def _ran_through_level_1(store: SqliteProgressStore) -> None:
    """A `cstudy test` of the new attempt that passed level 1 and failed a case of level 2."""
    attempt = store.active_attempt(PROBLEM)
    assert attempt is not None
    store.update_attempt(replace(attempt, level_unlocked=2))
    tally = Tally(total=10, passed=9, failed=1)
    store.add_test_run(
        RunRecord(attempt.id, attempt.started_at, "hash", tally, 10, levels_passed=1)
    )


def _done(page: Any) -> str:
    page.click(".flow-actions button:has-text('Done')")
    page.click(f"{SHEET} label[for=done-ok]")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(f"{SHEET} .outcome-lines")
    return page.locator(f"{SHEET} .outcome-lines strong").inner_text()


def test_the_practise_panel_names_the_level_to_try(viewed):
    assert f"python: {GOAL}" in viewed.practise


def test_the_status_reads_mastered_through_level_2(viewed):
    assert viewed.badge.endswith("mastered through level 2 of 4")


def test_the_history_names_the_best_level(viewed):
    assert viewed.best == "passed python through level 2 of 4"


def test_the_earlier_attempt_reads_passed_through_level_2(viewed):
    assert "passed through level 2 of 4" in viewed.summary


def test_the_statement_of_the_new_attempt_shows_the_goal(viewed):
    assert GOAL in viewed.statement


def test_done_after_a_run_through_level_1_is_a_pass_through_it(viewed):
    assert " · python · passed · through level 1 of 4 · " in viewed.outcome


def test_the_set_counts_the_entry_that_reached_its_target(viewed):
    assert viewed.set_counts == "1 of 1 passed"


def test_the_set_row_names_its_target(viewed):
    assert "through level 2 (target)" in viewed.set_row


def test_no_console_error(viewed):
    assert viewed.errors == []
