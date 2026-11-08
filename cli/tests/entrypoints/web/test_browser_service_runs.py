"""Runs of a service project in a real browser (docs/specs/web-ui.md#attempt-view), in each engine
of `tests/browsers.py`, against a real `cstudy serve`: the page starts none, since `cstudy test`
streams no events on a service project yet. The header has no Run tests, Submit or Run options,
the results panel names the terminal commands, `cstudy dev`, `cstudy test` and `cstudy submit`,
with no flag, and neither the run shortcuts nor a save under Run on save starts a run. No console
error and no Content Security Policy violation.

The attempt is started in this process, since `cstudy start` would install the project in Docker
and nothing here needs it. Playwright and its engines are set up as `tests/browsers.py` says;
without them the test is skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.preferences import Preferences, preferences_document
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SLUG = "coworking-availability-typescript"
SOURCE_FILE = "src/server.ts"
FILE_BUTTON = f"button.tree-file[data-path='{SOURCE_FILE}']"
ACTIVE_TAB = "[role=tab][aria-selected=true]"
MODIFIED_TAB = f"{ACTIVE_TAB}.is-modified"
SAVED_TAB = f"{ACTIVE_TAB}:not(.is-modified)"
EDITOR = ".panel:not([hidden]) .cm-content"
PANEL = ".results"
COMMANDS = f"{PANEL} code.cmd"
WAIT_MS = 60_000
SETTLE_MS = 800
"""More than run on save's debounce, for a run that must not come."""
RUNS_OF_THE_ATTEMPT = """async () => {
  const hash = location.hash.split("/").pop();
  const answer = await fetch(`/api/v1/runs?attempt_id=${hash}`);
  return (await answer.json()).length;
}"""


@dataclass
class Seen:
    toolbar_shown: bool = True
    run_options_shown: bool = True
    commands: list[str] = field(default_factory=list[str])
    panel_text: str = ""
    runs_started: int = -1
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"service-runs-{engine}") / "workspace"
    )
    environment = load_environment(root, served_environment(root), root.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    FsPreferencesStore(root).write(preferences_document(Preferences(run_on_save=True)))
    return root


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    attempt_id = opened_page(server).attempts[SLUG]
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("id => { location.hash = `#/attempts/${id}` }", attempt_id)
        page.wait_for_selector(COMMANDS)
        found.toolbar_shown = page.is_visible(".run-toolbar")
        found.run_options_shown = page.is_visible("button:has-text('Run options')")
        found.commands = page.locator(COMMANDS).all_inner_texts()
        found.panel_text = page.locator(PANEL).inner_text()
        _save_and_press_the_run_keys(page, found)
        browser.close()
    return found


def _save_and_press_the_run_keys(page: Any, found: Seen) -> None:
    page.click(FILE_BUTTON)
    page.wait_for_selector(EDITOR)
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("// saved\n")
    page.wait_for_selector(MODIFIED_TAB)
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(SAVED_TAB)
    page.keyboard.press("ControlOrMeta+Enter")
    page.keyboard.press("ControlOrMeta+Shift+Enter")
    page.wait_for_timeout(SETTLE_MS)
    found.runs_started = page.evaluate(RUNS_OF_THE_ATTEMPT)


def test_the_header_has_no_run_buttons(seen):
    assert seen.toolbar_shown is False


def test_the_header_has_no_run_options(seen):
    assert seen.run_options_shown is False


def test_the_results_panel_names_the_terminal_commands(seen):
    assert seen.commands == [f"cstudy dev {SLUG}", f"cstudy test {SLUG}", f"cstudy submit {SLUG}"]


def test_the_results_panel_suggests_no_flag(seen):
    assert "--" not in seen.panel_text


def test_no_shortcut_and_no_save_starts_a_run(seen):
    assert seen.runs_started == 0


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []
