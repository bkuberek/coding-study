"""Aborting an attempt from the page, in a real browser (docs/specs/web-ui.md#attempt-view), in each
engine of `tests/browsers.py`: Abort asks the question `cstudy abort` asks, naming the command; Keep
working leaves the attempt as it was; Abort ends it as `abandoned`, takes it out of the menu of
attempts in progress, keeps the practice file, and opens the problem, where a new start begins a
fresh attempt in the same file. A run that holds the workspace refuses it in words, and so do edits
that are not saved.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptStatus
from coding_study.domain.config import DEFAULT_PROGRESS_DB
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
ABORT_BUTTON = ".attempt-head .flow-actions button:has-text('Abort')"
ABORT_PATH = "**/api/v1/attempts/*/abort"
PRACTICE_FILE = Path("python") / "practice" / "two_sum.py"
EDITOR = ".panel:not([hidden]) .cm-editor"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
MENU_LINKS = ".attempts-menu .menu-list a"
BUSY = "cstudy abort waits until it ends: two-sum is in progress"
CONFLICT = "status of 409"


@dataclass
class Aborting:
    """What the browser saw while the attempt was aborted, and what the workspace holds after."""

    button_title: str = ""
    question: str = ""
    command: str = ""
    kept_working_hash: str = ""
    first_attempt: int = 0
    refusal: str = ""
    unsaved_refusal: str = ""
    status_after: AttemptStatus | None = None
    hash_after: str = ""
    menu_before: int = 0
    menu_after: int = -1
    file_after: str = ""
    second_attempt: int = 0
    second_status: AttemptStatus | None = None
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return mark_workspace(tmp_path_factory.mktemp(f"abort-{engine}") / "workspace")


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def aborting(engine: str, server: RunningServer, workspace: Path) -> Aborting:
    seen = Aborting()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        watched(page, seen.errors, expected=_is_a_refusal_or_a_question)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _start(page)
        seen.first_attempt = _attempt_id(page)
        page.wait_for_selector(MENU_LINKS, state="attached")
        seen.menu_before = page.locator(MENU_LINKS).count()
        seen.button_title = page.locator(ABORT_BUTTON).get_attribute("title") or ""
        _ask_and_keep_working(page, seen)
        _unsaved_edits_refuse(page, seen)
        _a_busy_workspace_refuses(page, seen)
        _abort(page, seen, workspace)
        _start(page)
        seen.second_attempt = _attempt_id(page)
        seen.second_status = _status(workspace, seen.second_attempt)
        browser.close()
    return seen


def _start(page: Any) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.click(".practice-actions button.primary")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".attempt-head .flow-actions")
    page.wait_for_selector(EDITOR)


def _attempt_id(page: Any) -> int:
    return int(page.evaluate("location.hash").rsplit("/", 1)[1])


def _ask_and_keep_working(page: Any, seen: Aborting) -> None:
    page.click(ABORT_BUTTON)
    seen.question = page.wait_for_selector(f"{SHEET} .question").inner_text()
    seen.command = page.locator(f"{SHEET} .sheet-command .cmd").inner_text()
    page.click(f"{SHEET} button:has-text('Keep working')")
    page.wait_for_selector(SHEET, state="detached")
    seen.kept_working_hash = page.evaluate("location.hash")


def _unsaved_edits_refuse(page: Any, seen: Aborting) -> None:
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("# unsaved\n")
    page.wait_for_selector(f"{ACTIVE_TAB}.is-modified")
    page.click(ABORT_BUTTON)
    seen.unsaved_refusal = page.wait_for_selector(f"{SHEET} [role=alert]").inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(f"{ACTIVE_TAB}:not(.is-modified)")


def _a_busy_workspace_refuses(page: Any, seen: Aborting) -> None:
    refusal = {
        "error": {"code": "conflict", "message": BUSY, "fix": None, "run": "c8a4df906a913818"}
    }

    def refuse(route: Any) -> None:
        route.fulfill(status=409, content_type="application/json", body=json.dumps(refusal))

    page.route(ABORT_PATH, refuse)
    page.click(ABORT_BUTTON)
    seen.refusal = page.wait_for_selector(f"{SHEET} [role=alert]").inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    page.unroute(ABORT_PATH)


def _abort(page: Any, seen: Aborting, workspace: Path) -> None:
    page.click(ABORT_BUTTON)
    page.click(f"{SHEET} button.danger")
    page.wait_for_function("() => location.hash === '#/problems/two-sum'")
    seen.hash_after = page.evaluate("location.hash")
    page.wait_for_selector(".attempts-menu", state="hidden")
    seen.menu_after = page.locator(MENU_LINKS).count()
    seen.status_after = _status(workspace, seen.first_attempt)
    seen.file_after = (workspace / PRACTICE_FILE).read_text()


def _status(workspace: Path, attempt_id: int) -> AttemptStatus | None:
    found = SqliteProgressStore(workspace / DEFAULT_PROGRESS_DB).attempt(attempt_id)
    return found.status if found else None


def _is_a_refusal_or_a_question(message: Any) -> bool:
    """The browser logs every 409 answer: the question of the abort, and the refusals."""
    return CONFLICT in message.text and message.location.get("url", "").endswith("/abort")


def test_the_abort_button_names_the_command_it_runs(aborting):
    assert "cstudy abort two-sum" in aborting.button_title


def test_abort_asks_the_clis_question(aborting):
    assert aborting.question == (
        "Abort two-sum in python? The attempt ends as abandoned. "
        "Your files stay; progress and the review schedule do not change."
    )


def test_the_question_names_the_cli_command(aborting):
    assert aborting.command == "cstudy abort two-sum"


def test_keep_working_leaves_the_attempt_open(aborting):
    assert aborting.kept_working_hash == f"#/attempts/{aborting.first_attempt}"


def test_unsaved_edits_refuse_the_abort_and_name_the_file(aborting):
    assert "not saved" in aborting.unsaved_refusal
    assert "two_sum.py" in aborting.unsaved_refusal


def test_a_run_in_progress_refuses_the_abort_in_words(aborting):
    assert BUSY in aborting.refusal


def test_abort_ends_the_attempt_as_abandoned(aborting):
    assert aborting.status_after is AttemptStatus.ABANDONED


def test_abort_opens_the_problem(aborting):
    assert aborting.hash_after == f"#/problems/{PROBLEM}"


def test_the_attempt_in_progress_is_in_the_menu_until_it_is_aborted(aborting):
    assert (aborting.menu_before, aborting.menu_after) == (1, 0)


def test_abort_keeps_the_practice_file(aborting):
    assert "def two_sum" in aborting.file_after


def test_a_new_start_begins_a_fresh_attempt(aborting):
    assert aborting.second_attempt > aborting.first_attempt
    assert aborting.second_status is AttemptStatus.IN_PROGRESS


def test_the_page_logs_no_error(aborting):
    assert aborting.errors == []
