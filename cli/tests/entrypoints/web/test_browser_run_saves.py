"""A run tests what the editors show (docs/specs/web-ui.md#runs), in each engine of
`tests/browsers.py`: Run tests, Submit and Bench first save every tab with unsaved edits, through
the save the shortcut uses, and a tab with a conflict, or a file deleted on disk, stops the run and
says why. Run on save runs once. Done, which grades the latest run, refuses unsaved edits.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped."""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
SINGLE_FILE = "two-sum"
FILE = "bank/bank.py"
SECOND_FILE = "bank/models.py"
BROKEN_LINE = 15
"""`def deposit(…) -> int:`, whose colon the test deletes."""
SECOND_FILE_MARK = "# touched in a second tab"
LOAD_FAILED = "LOAD FAILED"
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
SECOND_FILE_BUTTON = f"button.tree-file[data-path='{SECOND_FILE}']"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
SAVED_TAB = f"{ACTIVE_TAB}:not(.is-modified)"
MODIFIED_TAB = f"{ACTIVE_TAB}.is-modified"
RUN = ".run-button.primary"
SUBMIT = ".run-button:not(.primary)"
SUMMARY = ".result-summary-text"
BANNER = ".panel:not([hidden]) .file-banner.is-conflict"
REFUSAL = ".results .state-error"
DONE_DIALOG = "dialog.sheet[open]"
WAIT_MS = 60_000
RUN_WAIT_MS = 240_000
"""Generous for a run: the machine running the slow tests is often loaded."""
SETTLE_MS = 800
"""More than a run on save's debounce, for a second run that must not come."""
MARK_THE_SUMMARY_OLD = "selector => document.querySelector(selector)?.setAttribute('data-old', '')"
"""So the summary a run draws can be told from the last run's."""
HIGHLIGHTED = f"{OPEN_EDITOR} .cm-line span"
"""Drawn once the file's language applies, which is when the tab starts to follow its edits."""
RUNS_OF_THE_ATTEMPT = """async () => {
  const hash = location.hash.split("/").pop();
  const answer = await fetch(`/api/v1/runs?attempt_id=${hash}`);
  return (await answer.json()).length;
}"""


@dataclass
class Seen:
    test_summary: str = ""
    test_saved_the_edit: bool = False
    test_cleared_the_mark: bool = False
    fixed_summary: str = ""
    submit_summary: str = ""
    submit_saved_the_edit: bool = False
    second_tab_saved: bool = False
    conflict_refusal: str = ""
    conflict_runs_started: int = -1
    conflict_banner: int = -1
    conflict_disk_kept: bool = False
    deleted_refusal: str = ""
    deleted_runs_started: int = -1
    deleted_stayed_gone: bool = False
    run_on_save_runs_started: int = -1
    done_refusal: str = ""
    done_dialog_open: int = -1
    bench_writes: list[str] = field(default_factory=list[str])
    bench_saved_the_edit: bool = False
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"run-saves-{engine}") / "workspace"
    )
    for problem in ([PROJECT], [SINGLE_FILE, "--lang", "python"]):
        subprocess.run(
            [sys.executable, "-m", "coding_study", "start", *problem, "--no-open"],
            env=served_environment(root),
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
        )
    return root


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path) -> Seen:
    found = Seen()
    file = workspace / "projects" / PROJECT / FILE
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        _open_the_project(page, server)
        _a_test_saves_first(page, file, found)
        _a_submit_saves_first(page, file, found)
        _every_tab_is_saved(page, workspace, found)
        _a_conflict_refuses(page, file, found)
        _a_deleted_file_refuses(page, file, found)
        _run_on_save_runs_once(page, found)
        _done_refuses_unsaved_edits(page, found)
        bench_page = browser.new_page(viewport={"width": 1440, "height": 900})
        bench_page.set_default_timeout(WAIT_MS)
        _bench_saves_first(bench_page, server, workspace, found)
        browser.close()
    return found


def _open_the_project(page: Any, server: RunningServer) -> None:
    page.goto(server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    page.click(f"a.problem-link[href='#/problems/{PROJECT}']")
    page.click("a.button.primary")
    page.click(FILE_BUTTON)
    page.wait_for_selector(OPEN_EDITOR)


def _go_to_the_broken_line(page: Any) -> None:
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    for _ in range(BROKEN_LINE - 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("End")


def _delete_the_colon(page: Any) -> None:
    """A syntax error in the editor, unsaved."""
    _go_to_the_broken_line(page)
    page.keyboard.press("Backspace")
    page.wait_for_selector(MODIFIED_TAB)


def _put_the_colon_back(page: Any) -> None:
    _go_to_the_broken_line(page)
    page.keyboard.type(":")


def _run_and_read(page: Any, button: str) -> str:
    """Clicks `button` and reads the summary of the run it starts, once that run ended."""
    page.evaluate(MARK_THE_SUMMARY_OLD, SUMMARY)
    page.click(button)
    fresh = f"{SUMMARY}:not([data-old])"
    page.wait_for_selector(fresh, timeout=RUN_WAIT_MS)
    return page.locator(fresh).inner_text()


def _a_test_saves_first(page: Any, file: Path, found: Seen) -> None:
    _delete_the_colon(page)
    found.test_summary = _run_and_read(page, RUN)
    found.test_saved_the_edit = "-> int\n" in file.read_text()
    found.test_cleared_the_mark = page.locator(SAVED_TAB).count() == 1
    _put_the_colon_back(page)
    found.fixed_summary = _run_and_read(page, RUN)


def _a_submit_saves_first(page: Any, file: Path, found: Seen) -> None:
    _delete_the_colon(page)
    found.submit_summary = _run_and_read(page, SUBMIT)
    found.submit_saved_the_edit = "-> int\n" in file.read_text()
    _put_the_colon_back(page)
    _run_and_read(page, RUN)


def _every_tab_is_saved(page: Any, workspace: Path, found: Seen) -> None:
    _delete_the_colon(page)
    page.click(SECOND_FILE_BUTTON)
    page.wait_for_selector(f"{ACTIVE_TAB}[title^='{SECOND_FILE}']")
    page.wait_for_selector(HIGHLIGHTED)
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type(SECOND_FILE_MARK)
    page.wait_for_selector(MODIFIED_TAB)
    _run_and_read(page, RUN)
    second = workspace / "projects" / PROJECT / SECOND_FILE
    found.second_tab_saved = SECOND_FILE_MARK in second.read_text()
    page.click(FILE_BUTTON)
    page.wait_for_selector(f"{ACTIVE_TAB}[title^='{FILE}']")
    _put_the_colon_back(page)
    _run_and_read(page, RUN)


def _refusal_after_clicking_run(page: Any) -> tuple[str, int]:
    runs = page.evaluate(RUNS_OF_THE_ATTEMPT)
    page.click(RUN)
    page.wait_for_selector(REFUSAL)
    page.wait_for_timeout(SETTLE_MS)
    return page.locator(REFUSAL).inner_text(), page.evaluate(RUNS_OF_THE_ATTEMPT) - runs


def _a_conflict_refuses(page: Any, file: Path, found: Seen) -> None:
    _go_to_the_broken_line(page)
    page.keyboard.type(" ")
    page.wait_for_selector(MODIFIED_TAB)
    theirs = file.read_text() + "# changed elsewhere\n"
    file.write_text(theirs)
    page.wait_for_selector(BANNER)
    found.conflict_refusal, found.conflict_runs_started = _refusal_after_clicking_run(page)
    found.conflict_banner = page.locator(BANNER).count()
    found.conflict_disk_kept = file.read_text() == theirs
    page.click(f"{BANNER} button:has-text('Reload theirs')")
    page.wait_for_selector(BANNER, state="hidden")


def _a_deleted_file_refuses(page: Any, file: Path, found: Seen) -> None:
    file.unlink()
    page.wait_for_selector(BANNER)
    found.deleted_refusal, found.deleted_runs_started = _refusal_after_clicking_run(page)
    found.deleted_stayed_gone = not file.exists()
    page.click(f"{BANNER} button:has-text('Save mine again')")
    page.wait_for_selector(BANNER, state="hidden")


def _run_on_save_runs_once(page: Any, found: Seen) -> None:
    hash_of_the_view = page.evaluate("location.hash")
    page.evaluate("location.hash = '#/settings'")
    page.click("#pref-run_on_save")
    page.wait_for_selector("p.quiet[role=status]:has-text('saved in')")
    page.evaluate("hash => { location.hash = hash }", hash_of_the_view)
    page.click(FILE_BUTTON)
    page.wait_for_selector(OPEN_EDITOR)
    runs = page.evaluate(RUNS_OF_THE_ATTEMPT)
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("# once\n")
    page.wait_for_selector(MODIFIED_TAB)
    page.click(RUN)
    page.wait_for_selector(".cancel-button:not(:disabled)")
    page.wait_for_selector(".cancel-button:disabled", timeout=RUN_WAIT_MS)
    page.wait_for_timeout(SETTLE_MS)
    page.wait_for_selector(".cancel-button:disabled", timeout=RUN_WAIT_MS)
    found.run_on_save_runs_started = page.evaluate(RUNS_OF_THE_ATTEMPT) - runs
    page.evaluate("location.hash = '#/settings'")
    page.click("#pref-run_on_save")
    page.wait_for_selector("p.quiet[role=status]:has-text('saved in')")
    page.evaluate("hash => { location.hash = hash }", hash_of_the_view)
    page.click(FILE_BUTTON)
    page.wait_for_selector(OPEN_EDITOR)


def _done_refuses_unsaved_edits(page: Any, found: Seen) -> None:
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("# not saved\n")
    page.wait_for_selector(MODIFIED_TAB)
    page.click("button:has-text('Done')")
    page.wait_for_selector(DONE_DIALOG)
    page.click(f"{DONE_DIALOG} button[type=submit]")
    page.wait_for_selector(f"{DONE_DIALOG} .state-error")
    found.done_refusal = page.locator(f"{DONE_DIALOG} .state-error").inner_text()
    found.done_dialog_open = page.locator(DONE_DIALOG).count()
    page.click(f"{DONE_DIALOG} [data-close]")


def _bench_saves_first(page: Any, server: RunningServer, workspace: Path, found: Seen) -> None:
    """A single-file attempt, with the job itself answered by the test: only what comes before it
    matters, and a real bench takes minutes."""
    writes: list[str] = []
    page.on(
        "request",
        lambda request: (
            writes.append(f"{request.method} {request.url.rsplit('/', 1)[-1]}")
            if request.method != "GET"
            else None
        ),
    )
    page.route(
        "**/api/v1/jobs",
        lambda route: route.fulfill(status=201, content_type="application/json", body='{"id":"j"}'),
    )
    page.goto(server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    page.click(f"a.problem-link[href='#/problems/{SINGLE_FILE}']")
    page.click("a.button.primary")
    page.wait_for_selector(OPEN_EDITOR)
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("# benched\n")
    page.wait_for_selector(MODIFIED_TAB)
    page.click("button:has-text('Bench')")
    page.wait_for_function("() => document.querySelector('[role=tab].is-modified') === null")
    page.wait_for_timeout(SETTLE_MS)
    found.bench_writes = writes
    stub = workspace / "python" / "practice" / "two_sum.py"
    found.bench_saved_the_edit = "# benched" in stub.read_text()


def test_run_tests_runs_what_the_editor_shows(seen):
    assert LOAD_FAILED in seen.test_summary


def test_run_tests_saves_the_edit_first(seen):
    assert seen.test_saved_the_edit


def test_a_run_clears_the_unsaved_mark_of_what_it_saved(seen):
    assert seen.test_cleared_the_mark


def test_a_fix_that_is_not_saved_reaches_the_run_too(seen):
    assert LOAD_FAILED not in seen.fixed_summary


def test_submit_runs_what_the_editor_shows(seen):
    assert LOAD_FAILED in seen.submit_summary


def test_submit_saves_the_edit_first(seen):
    assert seen.submit_saved_the_edit


def test_a_run_saves_every_tab_with_unsaved_edits(seen):
    assert seen.second_tab_saved


def test_a_tab_with_a_conflict_stops_the_run_and_says_why(seen):
    assert (FILE in seen.conflict_refusal, "changed on disk" in seen.conflict_refusal) == (
        True,
        True,
    )


def test_a_tab_with_a_conflict_starts_no_run(seen):
    assert seen.conflict_runs_started == 0


def test_a_conflict_leaves_its_banner_in_charge(seen):
    assert seen.conflict_banner == 1


def test_a_conflict_writes_nothing_over_the_file_on_disk(seen):
    assert seen.conflict_disk_kept


def test_a_file_deleted_on_disk_stops_the_run_and_says_why(seen):
    assert (FILE in seen.deleted_refusal, "deleted" in seen.deleted_refusal) == (True, True)


def test_a_file_deleted_on_disk_starts_no_run(seen):
    assert seen.deleted_runs_started == 0


def test_a_file_deleted_on_disk_stays_deleted(seen):
    assert seen.deleted_stayed_gone


def test_run_on_save_does_not_run_a_second_time(seen):
    assert seen.run_on_save_runs_started == 1


def test_done_refuses_unsaved_edits_and_names_them(seen):
    assert (FILE.rsplit("/", 1)[-1] in seen.done_refusal, seen.done_dialog_open) == (True, 1)


def test_bench_saves_before_its_job_starts(seen):
    assert seen.bench_writes[:2] == ["PUT two_sum.py", "POST jobs"]


def test_bench_saves_the_edit(seen):
    assert seen.bench_saved_the_edit


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors == []
