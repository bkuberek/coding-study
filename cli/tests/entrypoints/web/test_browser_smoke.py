"""The page in a real browser (docs/specs/web-ui.md#testing): log in with the printed URL, open
the problem list, open a project problem with its statement, resume its attempt, and open a file
of its tree in the editor, under the page's Content Security Policy.

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
WAIT_MS = 60_000


class ConsoleLine(Protocol):
    """A message the page logged, as Playwright reports it."""

    @property
    def type(self) -> str: ...

    @property
    def text(self) -> str: ...


@dataclass
class Visit:
    """What the browser saw on the way from the list to the editor."""

    rows: int = 0
    statement: str = ""
    tree: list[str] = field(default_factory=list[str])
    editor: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp("browser") / "workspace")
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROJECT, "--no-open"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def visit(server: RunningServer) -> Visit:
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
        page.click(f"button.tree-file[data-path='{FILE}']")
        seen.editor = page.locator(".panel:not([hidden]) .cm-content").inner_text()
        browser.close()
    return seen


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


def test_the_page_logs_no_error_under_its_content_security_policy(visit):
    assert visit.errors == []
