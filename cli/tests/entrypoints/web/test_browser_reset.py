"""The Settings view's Danger section in a real browser (docs/specs/web-ui.md#settings-view), in
each engine of `tests/browsers.py`, on a scratch workspace: the dialog shows what goes with its
counts and says it can't be undone, Reset stays disabled until the word is typed, the API refuses a
request without the word, Escape closes it and gives the focus back, and a reset empties the page's
menu of attempts and the Problems view without a reload, keeping what it says it keeps. A tab
showing the attempt says it ended.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
WAIT_MS = 60_000
OPEN_DIALOG = "button:has-text('Reset progress')"
SHEET = "dialog.sheet[open]"
WORD = f"{SHEET} input[type=text]"
SUBMIT = f"{SHEET} button[type=submit]"
ISSUE = f"{SHEET} .dialog-issue"
STATUS = ".settings > p[role=status]"
ATTEMPTS_MENU = ".attempts-menu"
EDITOR = ".panel:not([hidden]) .cm-content"
ENDED_NOTE = ".attempt-ended"
PRACTICE_FILE = Path("python") / "practice" / "two_sum.py"
SETS_FILE = "sets:\n  backend-loop:\n    problems:\n      - two-sum\n"
PLAIN_POST = """async (csrf) => {
  const answer = await fetch("/api/v1/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Cstudy-CSRF": csrf },
    body: "{}",
  });
  const counts = await (await fetch("/api/v1/reset")).json();
  return [answer.status, counts.groups[0].entries[0].count];
}"""


@dataclass
class Seen:
    warning: str = ""
    counts: list[str] = field(default_factory=list[str])
    kept: str = ""
    disabled_at_first: bool = False
    disabled_with_another_word: bool = False
    issue_with_another_word: str = ""
    focus_in_the_field: bool = False
    plain_post: list[int] = field(default_factory=list[int])
    focus_after_escape: bool = False
    dialogs_after_escape: int = -1
    menu_before: str = ""
    status_after: str = ""
    dialogs_after: int = -1
    menu_after: str = ""
    status_in_problems: str = ""
    practice_file_kept: bool = False
    marker_kept: bool = False
    preferences_kept: bool = False
    runs_left: list[str] = field(default_factory=list[str])
    practice_file_after_files: bool = True
    sets_after_reset: str = ""
    sets_after_files: str = ""
    other_tab_says: str = ""
    logged: list[str] = field(default_factory=list[str])
    errors_before_the_refusal: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = Path(mark_workspace(tmp_path_factory.mktemp(f"reset-{engine}") / "workspace"))
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROBLEM, "--no-open"],
        env=served_environment(root),
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    run_folder = root / ".cs" / "runs" / "20261106-1"
    run_folder.mkdir(parents=True)
    (run_folder / "out.json").write_text("{}")
    (root / "sets.yaml").write_text(SETS_FILE)
    return root


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        found.menu_before = page.locator(ATTEMPTS_MENU).inner_text()
        other_tab = browser.new_page(viewport={"width": 1440, "height": 900})
        other_tab.set_default_timeout(WAIT_MS)
        other_tab.goto(server.login_url)
        other_tab.wait_for_selector("table.problems tbody tr")
        other_tab.click(f"{ATTEMPTS_MENU} summary")
        other_tab.click(f"{ATTEMPTS_MENU} a")
        other_tab.wait_for_selector(EDITOR)
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(OPEN_DIALOG)
        (workspace / ".cs" / "serve").mkdir(parents=True, exist_ok=True)
        (workspace / ".cs" / "serve" / "preferences.json").write_text('{"format": 1, "vim": true}')
        page.click(OPEN_DIALOG)
        page.wait_for_selector(WORD)
        _read_the_dialog(page, found)
        found.errors_before_the_refusal = list(found.logged)
        _refuse_without_the_word(page, found)
        _escape(page, found)
        _reset(page, workspace, found)
        other_tab.wait_for_selector(ENDED_NOTE)
        found.other_tab_says = other_tab.locator(ENDED_NOTE).inner_text()
        _reset_the_files_too(page, workspace, found)
        browser.close()
    return found


def _read_the_dialog(page: Any, found: Seen) -> None:
    found.warning = page.locator(f"{SHEET} .question").inner_text()
    found.counts = page.locator(f"{SHEET} li").all_inner_texts()
    found.kept = page.locator(f"{SHEET} p.quiet").last.inner_text()
    found.disabled_at_first = page.is_disabled(SUBMIT)
    found.focus_in_the_field = page.evaluate(
        "() => document.activeElement?.closest('dialog') !== null"
    )


def _refuse_without_the_word(page: Any, found: Seen) -> None:
    page.fill(WORD, "yes")
    found.disabled_with_another_word = page.is_disabled(SUBMIT)
    found.issue_with_another_word = page.locator(ISSUE).inner_text()
    csrf = page.get_attribute("meta[name=cstudy-csrf]", "content")
    found.plain_post = page.evaluate(PLAIN_POST, csrf)


def _escape(page: Any, found: Seen) -> None:
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    found.dialogs_after_escape = page.locator(SHEET).count()
    found.focus_after_escape = page.evaluate(
        "() => document.activeElement?.textContent.startsWith('Reset progress')"
    )


def _reset(page: Any, workspace: Path, found: Seen) -> None:
    page.click(OPEN_DIALOG)
    page.fill(WORD, "reset")
    page.click(SUBMIT)
    page.wait_for_selector(SHEET, state="detached")
    done = f"{STATUS}:has-text('deleted')"
    page.wait_for_selector(done)
    found.status_after = page.locator(done).inner_text()
    found.dialogs_after = page.locator(SHEET).count()
    page.wait_for_function(
        "selector => !document.querySelector(selector)?.textContent.includes('1')",
        arg=ATTEMPTS_MENU,
    )
    found.menu_after = page.locator(ATTEMPTS_MENU).inner_text()
    page.evaluate("location.hash = '#/?status=new'")
    page.wait_for_selector(f"table.problems a[href='#/problems/{PROBLEM}']")
    found.status_in_problems = page.locator(
        f"table.problems tr:has(a[href='#/problems/{PROBLEM}']) .badge"
    ).inner_text()
    found.practice_file_kept = (workspace / PRACTICE_FILE).exists()
    found.sets_after_reset = (workspace / "sets.yaml").read_text()
    found.marker_kept = (workspace / ".cs" / "workspace.toml").exists()
    found.preferences_kept = (workspace / ".cs" / "serve" / "preferences.json").exists()
    runs = workspace / ".cs" / "runs"
    found.runs_left = [entry.name for entry in runs.iterdir()] if runs.exists() else []


def _reset_the_files_too(page: Any, workspace: Path, found: Seen) -> None:
    page.evaluate("location.hash = '#/settings'")
    page.click(OPEN_DIALOG)
    page.wait_for_selector(WORD)
    page.check("#reset-files")
    page.fill(WORD, "reset")
    page.click(SUBMIT)
    page.wait_for_selector(SHEET, state="detached")
    found.practice_file_after_files = (workspace / PRACTICE_FILE).exists()
    found.sets_after_files = (workspace / "sets.yaml").read_text()


def test_the_dialog_says_it_cannot_be_undone(seen):
    assert seen.warning == "This can't be undone."


def test_the_dialog_counts_what_goes(seen):
    assert "attempts: 1" in seen.counts


def test_the_dialog_counts_the_run_folders(seen):
    assert "run folders: 1" in seen.counts


def test_the_dialog_counts_the_practice_files_it_would_delete_when_asked(seen):
    assert "practice files: 1" in seen.counts


def test_the_dialog_says_what_stays(seen):
    assert "config.toml" in seen.kept


def test_the_focus_is_in_the_dialog(seen):
    assert seen.focus_in_the_field


def test_reset_is_disabled_until_the_word_is_typed(seen):
    assert (seen.disabled_at_first, seen.disabled_with_another_word) == (True, True)


def test_another_word_says_which_is_wanted(seen):
    assert seen.issue_with_another_word == "type reset"


def test_a_plain_post_is_refused_and_deletes_nothing(seen):
    assert seen.plain_post == [409, 1]


def test_escape_closes_the_dialog_and_gives_the_focus_back(seen):
    assert (seen.dialogs_after_escape, seen.focus_after_escape) == (0, True)


def test_the_menu_showed_the_attempt_before(seen):
    assert "1" in seen.menu_before


def test_a_reset_says_what_it_deleted(seen):
    assert "attempts 1" in seen.status_after


def test_a_reset_closes_its_dialog(seen):
    assert seen.dialogs_after == 0


def test_the_menu_of_attempts_empties_without_a_reload(seen):
    assert "1" not in seen.menu_after


def test_the_problems_view_shows_the_problem_as_new(seen):
    assert "new" in seen.status_in_problems


def test_the_practice_file_stays_by_default(seen):
    assert seen.practice_file_kept


def test_the_workspace_s_marker_and_preferences_stay(seen):
    assert (seen.marker_kept, seen.preferences_kept) == (True, True)


def test_the_run_folders_are_gone(seen):
    assert seen.runs_left == []


def test_the_files_option_deletes_the_practice_file(seen):
    assert not seen.practice_file_after_files


def test_a_tab_showing_the_attempt_says_it_ended(seen):
    assert "a reset deleted it" in seen.other_tab_says


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors_before_the_refusal == []


def test_the_dialog_says_sets_stay(seen):
    assert "sets.yaml" in seen.kept


def test_a_reset_keeps_sets(seen):
    assert seen.sets_after_reset == SETS_FILE


def test_a_reset_of_the_files_keeps_sets(seen):
    assert seen.sets_after_files == SETS_FILE
