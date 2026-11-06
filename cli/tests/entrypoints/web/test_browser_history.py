"""A past attempt's code in a real browser (docs/specs/web-ui.md#past-attempt-files): finish an
attempt, open the Problem view, expand its History row and open the file read-only, with no save
and no run; start the review, which moves the files to `.archive/`, finish it, and find the first
attempt reading from the archive and the second from the files as they are, in each engine of
`tests/browsers.py`.

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

PROBLEM = "two-sum"
PRACTICE_FILE = Path("python") / "practice" / "two_sum.py"
SOLVED = "def two_sum(nums, target):\n    return [0, 1]\n"
STUB_MARK = "def two_sum"
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
ROWS = "ol.attempts > li"
VIEWER = f"{SHEET} .cm-content"
NBSP = chr(0xA0)
CLOSE = "esc " + chr(0xD7)
PRACTISE = "section[aria-labelledby=practice-heading]"
ARCHIVE_NOTE = (
    "your current files move to .archive/ \N{EM DASH} "
    "nothing is deleted, and History keeps them readable"
)
BUTTONS_OF_A_RUN = ".run-button, .save-hint, .flow-actions"


@dataclass
class Viewed:
    """What the browser saw of the History of two attempts of one problem."""

    first_source: str = ""
    first_summary: str = ""
    first_button: str = ""
    first_title: str = ""
    first_text: str = ""
    first_read_only: str | None = None
    first_note: str = ""
    sheet_buttons: list[str] = field(default_factory=list[str])
    run_controls: int = -1
    text_after_typing: str = ""
    focus_after_close: str = ""
    running_row: str = ""
    running_files: int = -1
    summaries: list[str] = field(default_factory=list[str])
    archived_source: str = ""
    archived_text: str = ""
    current_source: str = ""
    current_text: str = ""
    first_practise: str = ""
    first_start_note: str = ""
    review_practise: str = ""
    review_start_note: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"history-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def viewed(engine: str, server: RunningServer) -> Viewed:
    seen = Viewed()
    workspace = Path(server.environment["CSTUDY_WORKSPACE"])
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        watched(page, seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        seen.first_practise, seen.first_start_note = _start(page)
        (workspace / PRACTICE_FILE).write_text(SOLVED)
        _done(page)
        _first_attempt(page, seen)
        seen.review_practise, seen.review_start_note = _start(page)
        _running_attempt(page, seen)
        _done(page)
        _both_attempts(page, seen)
        browser.close()
    return seen


def _problem(page: Any) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.wait_for_selector(".practice-actions button.primary")


def _start(page: Any) -> tuple[str, str]:
    """Starts from the Problem view; answers the Practise panel's text and the Start dialog's
    review note, empty for a start that is no review."""
    _problem(page)
    practise = page.locator(PRACTISE).inner_text()
    page.click(".practice-actions button.primary")
    page.wait_for_selector(f"{SHEET} form")
    notes = page.locator(f"{SHEET} .review-note")
    note = notes.inner_text() if notes.count() else ""
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".attempt-head .flow-actions")
    return practise, note


def _done(page: Any) -> None:
    page.click(".flow-actions button:has-text('Done')")
    page.click(f"{SHEET} label[for=done-gave-up]")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(f"{SHEET} .outcome-lines")
    page.keyboard.press("Escape")
    page.wait_for_selector("dialog.sheet", state="detached")


def _expand(page: Any, row: int) -> Any:
    """The row of the History's attempt `row` (0: the newest), opened and with its files read."""
    item = page.locator(ROWS).nth(row)
    item.locator("summary").click()
    return item


def _first_attempt(page: Any, seen: Viewed) -> None:
    _problem(page)
    row = _expand(page, 0)
    source = row.locator(".past-source")
    source.wait_for()
    seen.first_summary = row.locator("summary").inner_text()
    seen.first_source = source.inner_text()
    opener = row.locator(".past-open button")
    seen.first_button = opener.inner_text()
    opener.focus()
    page.keyboard.press("Enter")
    page.wait_for_selector(VIEWER)
    seen.first_title = page.locator(f"{SHEET} h2").inner_text()
    seen.first_text = page.locator(VIEWER).inner_text()
    seen.first_read_only = page.locator(VIEWER).get_attribute("aria-readonly")
    seen.first_note = page.locator(f"{SHEET} .past-note").inner_text()
    seen.sheet_buttons = page.locator(f"{SHEET} button").all_inner_texts()
    seen.run_controls = page.locator(BUTTONS_OF_A_RUN).count()
    page.click(VIEWER)
    page.keyboard.type("typed into a read-only editor")
    seen.text_after_typing = page.locator(VIEWER).inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector("dialog.sheet", state="detached")
    seen.focus_after_close = page.evaluate("document.activeElement.textContent")


def _running_attempt(page: Any, seen: Viewed) -> None:
    """The review attempt in progress: its row leads to the Attempt view and offers no files; the
    page then resumes it."""
    _problem(page)
    row = _expand(page, 0)
    row.locator("a").wait_for()
    seen.running_row = row.inner_text()
    seen.running_files = row.locator(".past-block").count()
    page.click("a.button.primary")
    page.wait_for_selector(".attempt-head .flow-actions")


def _both_attempts(page: Any, seen: Viewed) -> None:
    _problem(page)
    seen.summaries = page.locator(f"{ROWS} summary").all_inner_texts()
    for row, source_to, text_to in (
        (1, "archived_source", "archived_text"),
        (0, "current_source", "current_text"),
    ):
        item = _expand(page, row)
        source = item.locator(".past-source")
        source.wait_for()
        setattr(seen, source_to, source.inner_text())
        item.locator(".past-open button").click()
        page.wait_for_selector(VIEWER)
        setattr(seen, text_to, page.locator(VIEWER).inner_text())
        page.keyboard.press("Escape")
        page.wait_for_selector("dialog.sheet", state="detached")


def test_a_finished_attempt_says_its_files_are_the_current_ones(viewed):
    assert "current files, which may have changed since this attempt ended" in viewed.first_source


def test_the_row_names_the_file_it_opens(viewed):
    assert viewed.first_button == "View two_sum.py"


def test_the_dialog_is_titled_with_the_attempt(viewed):
    assert viewed.first_title == "code · two-sum · attempt 1 · python"


def test_the_file_shows_what_the_attempt_wrote(viewed):
    assert viewed.first_text.replace(NBSP, " ").strip() == SOLVED.strip()


def test_the_editor_is_read_only(viewed):
    assert viewed.first_read_only == "true"


def test_the_dialog_says_it_is_read_only(viewed):
    assert "read-only" in viewed.first_note


def test_typing_into_the_editor_changes_nothing(viewed):
    assert viewed.text_after_typing == viewed.first_text


def test_the_dialog_has_no_save_and_no_run(viewed):
    assert viewed.sheet_buttons == [CLOSE]
    assert viewed.run_controls == 0


def test_closing_the_dialog_returns_the_focus_to_the_button_that_opened_it(viewed):
    assert viewed.focus_after_close == "View two_sum.py"


def test_the_row_of_an_attempt_in_progress_leads_to_the_attempt_view(viewed):
    assert "Open it in the Attempt view" in viewed.running_row
    assert viewed.running_files == 0


def test_the_history_lists_the_review_before_the_first_attempt(viewed):
    assert [summary.split(" ")[0] for summary in viewed.summaries] == ["#2", "#1"]


def test_the_first_attempt_reads_from_the_archive_after_the_review_started(viewed):
    assert "archived" in viewed.archived_source
    assert ".archive/two-sum/1-python" in viewed.archived_source


def test_the_archived_file_is_what_the_first_attempt_wrote(viewed):
    assert viewed.archived_text.replace(NBSP, " ").strip() == SOLVED.strip()


def test_the_review_reads_the_files_as_they_are(viewed):
    assert "current files" in viewed.current_source


def test_the_review_shows_its_own_stub(viewed):
    assert STUB_MARK in viewed.current_text
    assert "return [0, 1]" not in viewed.current_text


def test_a_start_of_a_problem_never_finished_is_no_review(viewed):
    assert viewed.first_start_note == ""
    assert "review attempt" not in viewed.first_practise


def test_the_start_dialog_of_a_review_says_nothing_is_deleted(viewed):
    assert viewed.review_start_note == f"review attempt: {ARCHIVE_NOTE}"


def test_the_practise_panel_of_a_review_says_the_same(viewed):
    assert f"a start is a review attempt: {ARCHIVE_NOTE}" in viewed.review_practise.replace(
        "\n", " "
    )


def test_the_page_logs_no_error_under_its_content_security_policy(viewed):
    assert viewed.errors == []
