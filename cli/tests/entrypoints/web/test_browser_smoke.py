"""The page in a real browser (docs/specs/web-ui.md#testing): log in with the printed URL, open
the problem list, open a project problem with its statement, resume its attempt, open a file of
its tree in the editor, edit it and save it with Cmd or Ctrl-S, see its state turn `modified`,
restore it from the tree and see it `unchanged`, run its tests and see their rows while the run goes
on, cancel that run, run the tests to their end, name a new file in the tree's dialog, and turn Run
on save on to see a save start a run, under the page's Content Security Policy, in each engine
of `tests/browsers.py`.

The workspace shares the session's practice workspace's toolchains, so the project's suite runs
with the real pytest. Playwright and its engines are set up as `tests/browsers.py` says; without
them the test is skipped.
"""

import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pytest

from tests.browsers import launched, watched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
TYPED = "# saved from the page"
CREATED = "bank/scratch.py"
SAVED_AGAIN = "# saved again"
RUNS_OF_THE_ATTEMPT = """([id, known]) =>
    fetch(`/api/v1/runs?attempt_id=${id}`).then(r => r.json())
        .then(runs => runs.map(run => run.id).filter(found => !known.includes(found)))"""
POLL_MS = 250
WAIT_MS = 60_000
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"
RUN_WAIT_MS = 240_000
"""Generous for a run: the machine running the slow tests is often loaded."""
SLOW_TEST = "tests/test_slow.py"
SLOW_TEST_TEXT = "import time\n\n\ndef test_slow():\n    time.sleep(120)\n"


class Keyboard(Protocol):
    def press(self, key: str) -> None: ...

    def type(self, text: str) -> None: ...


class Located(Protocol):
    def count(self) -> int: ...

    def inner_text(self) -> str: ...


class BrowserPage(Protocol):
    """The parts of Playwright's page the steps below use."""

    @property
    def keyboard(self) -> Keyboard: ...

    def click(self, selector: str) -> None: ...

    def focus(self, selector: str) -> None: ...

    def locator(self, selector: str) -> Located: ...

    def wait_for_selector(self, selector: str) -> object: ...


@dataclass
class Visit:
    """What the browser saw on the way from the list to the editor."""

    rows: int = 0
    statement: str = ""
    tree: list[str] = field(default_factory=list[str])
    editor: str = ""
    unsaved_tabs: int = 0
    saved_state: str = ""
    saved_text: str = ""
    restored_badges: int = -1
    restored_editor: str = ""
    rows_while_running: list[str] = field(default_factory=list[str])
    cancelled: str = ""
    finished: str = ""
    tree_after_create: list[str] = field(default_factory=list[str])
    runs_started_by_a_save: int = 0
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"browser-{engine}") / "workspace"
    )
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROJECT, "--no-open"],
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
def visit(engine: str, server: RunningServer, workspace: Path) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        seen.rows = page.locator("table.problems tbody tr").count()
        page.click(f"a.slug[href='#/problems/{PROJECT}']")
        seen.statement = page.locator(".statement-pane .prose").inner_text()
        page.click("a.button.primary")
        page.wait_for_selector("button.tree-file")
        seen.tree = page.locator("button.tree-file").evaluate_all(
            "buttons => buttons.map(button => button.dataset.path)"
        )
        page.click(FILE_BUTTON)
        seen.editor = page.locator(OPEN_EDITOR).inner_text()
        _save_an_edit(page, seen)
        seen.saved_text = (workspace / "projects" / PROJECT / FILE).read_text()
        _restore(page, seen)
        _run_and_cancel(page, workspace / "projects" / PROJECT / SLOW_TEST, seen)
        page.click(".run-button.primary")
        finished = ".result-summary-text:has-text('passed')"
        seen.finished = page.wait_for_selector(finished, timeout=RUN_WAIT_MS).inner_text()
        _create_a_file(page, seen)
        _save_with_run_on_save(page, seen)
        browser.close()
    return seen


def _save_an_edit(page: BrowserPage, seen: Visit) -> None:
    """Types at the end of the file, saves it with the shortcut, and waits for its state."""
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type(f"\n{TYPED}\n")
    seen.unsaved_tabs = page.locator("[role=tab].is-modified").count()
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(f"{FILE_BUTTON} .badge")
    seen.saved_state = page.locator(f"{FILE_BUTTON} .badge").inner_text()


def _restore(page: BrowserPage, seen: Visit) -> None:
    """Restores the file from its menu in the tree, confirming that its changes go."""
    page.focus(FILE_BUTTON)
    page.keyboard.press("Shift+F10")
    page.click(".tree-menu [role=menuitem]:has-text('Restore')")
    page.click("dialog.sheet button.danger")
    page.wait_for_selector(f"{FILE_BUTTON}:not(:has(.badge))")
    seen.restored_badges = page.locator(f"{FILE_BUTTON} .badge").count()
    seen.restored_editor = page.locator(OPEN_EDITOR).inner_text()


def _create_a_file(page: Any, seen: Visit) -> None:
    """Types a name in the dialog the tree's New file opens, and reads the tree once it lists it."""
    page.click("button.tree-tool[title='New file']")
    page.wait_for_selector("dialog.sheet[open] input")
    page.keyboard.type(CREATED)
    page.keyboard.press("Enter")
    page.wait_for_selector(f"button.tree-file[data-path='{CREATED}']")
    seen.tree_after_create = page.locator("button.tree-file").evaluate_all(
        "buttons => buttons.map(button => button.dataset.path)"
    )


def _save_with_run_on_save(page: Any, seen: Visit) -> None:
    """Turns Run on save on, saves an edit of the attempt, and waits for the run the save starts."""
    attempt = page.evaluate("location.hash")
    attempt_id = attempt.rsplit("/", 1)[1]
    known = _runs_of(page, attempt_id, [])
    page.evaluate("location.hash = '#/settings'")
    page.click("#pref-run_on_save")
    page.evaluate("hash => { location.hash = hash }", attempt)
    page.click(FILE_BUTTON)
    page.click(OPEN_EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type(f"\n{SAVED_AGAIN}\n")
    page.keyboard.press("ControlOrMeta+s")
    deadline = time.monotonic() + RUN_WAIT_MS / 1000
    started: list[str] = []
    while not started and time.monotonic() < deadline:
        page.wait_for_timeout(POLL_MS)
        started = [found for found in _runs_of(page, attempt_id, known) if found not in known]
    seen.runs_started_by_a_save = len(started)


def _runs_of(page: Any, attempt_id: str, known: list[str]) -> list[str]:
    """The ids of the attempt's runs the server keeps, which are not in `known`."""
    return page.evaluate(RUNS_OF_THE_ATTEMPT, [attempt_id, known])


def _run_and_cancel(page: Any, slow_test: Path, seen: Visit) -> None:
    """Runs the tests with one that sleeps, reads the rows shown while it runs, then cancels."""
    slow_test.write_text(SLOW_TEST_TEXT)
    try:
        page.click(".run-button.primary")
        page.wait_for_selector(".result-running:has-text('test_slow')", timeout=RUN_WAIT_MS)
        seen.rows_while_running = page.locator(".result-row .result-id").all_inner_texts()
        page.click(".cancel-button")
        page.wait_for_selector(".result-summary", timeout=RUN_WAIT_MS)
        seen.cancelled = page.locator(".result-summary-text").inner_text()
    finally:
        slow_test.unlink(missing_ok=True)
    page.wait_for_selector(".run-button.primary:not([disabled])")


def test_the_problem_list_shows_the_catalog(visit):
    assert visit.rows > 1


def test_a_project_problem_shows_its_statement(visit):
    assert "Bank" in visit.statement


def test_resuming_the_attempt_shows_the_projects_tree(visit):
    assert FILE in visit.tree


def test_a_file_opens_in_the_editor(visit):
    assert "class Bank" in visit.editor


def test_an_edit_marks_its_tab_unsaved(visit):
    assert visit.unsaved_tabs == 1


def test_the_save_shortcut_writes_the_file(visit):
    assert TYPED in visit.saved_text


def test_a_saved_starter_file_turns_modified_in_the_tree(visit):
    assert visit.saved_state.endswith("modified")


def test_a_restore_from_the_tree_turns_it_unchanged(visit):
    assert visit.restored_badges == 0


def test_a_restore_shows_the_starter_in_the_open_tab(visit):
    assert TYPED not in visit.restored_editor


def test_a_run_shows_its_test_rows_while_it_goes_on(visit):
    assert visit.rows_while_running == ["test_ex1", "test_ex2"]


def test_a_cancelled_run_ends_interrupted(visit):
    assert visit.cancelled == "interrupted"


def test_a_run_ends_with_the_reports_summary(visit):
    assert visit.finished.startswith("0/2 passed · 2 errors · total ")


def test_a_new_file_named_in_the_dialog_shows_in_the_tree(visit):
    assert CREATED in visit.tree_after_create


def test_a_save_starts_a_run_when_run_on_save_is_on(visit):
    assert visit.runs_started_by_a_save >= 1


def test_the_page_logs_no_error_under_its_content_security_policy(visit):
    assert visit.errors == []
