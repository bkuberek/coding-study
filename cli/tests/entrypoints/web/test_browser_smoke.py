"""The page in a real browser (docs/specs/web-ui.md#testing): log in with the printed URL, open
the problem list, open a project problem with its statement, resume its attempt, open a file of
its tree in the editor, edit it and save it with Cmd or Ctrl-S, see its state turn `modified`,
then restore it from the tree and see it `unchanged`, under the page's Content Security Policy.

Playwright is in the optional `browser` dependency group: `uv sync --group browser`, then
`uv run --group browser playwright install chromium`. Without either the test is skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pytest

from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
FILE = "bank/bank.py"
TYPED = "# saved from the page"
WAIT_MS = 60_000
FILE_BUTTON = f"button.tree-file[data-path='{FILE}']"
OPEN_EDITOR = ".panel:not([hidden]) .cm-content"


class ConsoleLine(Protocol):
    """A message the page logged, as Playwright reports it."""

    @property
    def type(self) -> str: ...

    @property
    def text(self) -> str: ...


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
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return mark_workspace(tmp_path_factory.mktemp("browser") / "workspace")


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROJECT, "--no-open"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def visit(server: RunningServer, workspace: Path) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except sync_api.Error as error:
            pytest.skip(f"no Chromium for Playwright: {error.message.splitlines()[0]}")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.on("console", lambda message: _console(seen, message))
        page.on("pageerror", lambda error: seen.errors.append(str(error)))
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
    page.click("dialog.file-dialog button.danger")
    page.wait_for_selector(f"{FILE_BUTTON}:not(:has(.badge))")
    seen.restored_badges = page.locator(f"{FILE_BUTTON} .badge").count()
    seen.restored_editor = page.locator(OPEN_EDITOR).inner_text()


def _console(seen: Visit, message: ConsoleLine) -> None:
    if message.type in ("error", "warning"):
        seen.errors.append(f"{message.type}: {message.text}")


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


def test_the_page_logs_no_error_under_its_content_security_policy(visit):
    assert visit.errors == []
