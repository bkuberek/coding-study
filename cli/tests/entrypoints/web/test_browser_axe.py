"""axe-core over every view of the page (docs/specs/web-ui.md#keyboard-and-accessibility), in
light and dark, 1440 and 390 pixels wide, in each engine of `tests/browsers.py`: the problem list,
a project problem, its attempt with a file in the editor and a run's results, the file tree's menu,
its new-file dialog and restore question, the start, done and solution dialogs, the mock view
before and during a mock, the progress, health and settings views. Each view must have no
violation of WCAG 2.2 A and AA, nor of axe's best practices.

axe-core comes with `axe-playwright-python`, in the optional `browser` dependency group; Playwright
and its engines are set up as `tests/browsers.py` says. Without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
axe_playwright = pytest.importorskip("axe_playwright_python.sync_playwright", reason="no axe-core")

PROJECT = "bank-project-python"
SINGLE_FILE = "two-sum"
FILE_BUTTON = "button.tree-file[data-path='bank/bank.py']"
SHEET = "dialog.sheet[open]"
WAIT_MS = 60_000
RUN_WAIT_MS = 240_000
"""Generous for a run or the health checks: the machine running the slow tests is often loaded."""
SCHEMES = ("light", "dark")
WIDTHS = (1440, 390)
HEIGHT = 900
RULES = {
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"],
    },
    "resultTypes": ["violations"],
}
AT_REST = """() => Promise.race([
    new Promise(resolve => setTimeout(resolve, 2000)),
    Promise.all(document.getAnimations().map(animation => {
        if (animation.effect?.getTiming().iterations !== Infinity) {
            return animation.finished.catch(() => null);
        }
        animation.pause();
        return null;
    })),
])"""
"""Waits, at most 2 s, for the animations that end, such as a dialog's entrance, and pauses the
endless ones, such as a blinking cursor, so colours are measured at rest."""
VIEWS = (
    "problems",
    "problem",
    "attempt",
    "file menu",
    "new file dialog",
    "restore question",
    "start dialog",
    "done dialog",
    "solution dialog",
    "mock",
    "mock running",
    "progress",
    "health",
    "settings",
)


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp(f"axe-{engine}") / "ws")
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
def violations(engine: str, server: RunningServer) -> dict[str, list[str]]:
    """Each view's violations, as `rule (impact): element, in scheme at width`."""
    found: dict[str, list[str]] = {}
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": WIDTHS[0], "height": HEIGHT})
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        for view, show in _tour(page):
            show()
            found[view] = _checked(page)
            page.set_viewport_size({"width": WIDTHS[0], "height": HEIGHT})
        browser.close()
    return found


def _tour(page: Any) -> Iterator[tuple[str, Callable[[], None]]]:
    """Each view, and how to show it from the one before."""
    yield "problems", lambda: None
    yield "problem", lambda: _open(page, f"#/problems/{PROJECT}", ".statement-pane .prose")
    yield "attempt", lambda: _attempt_with_results(page)
    yield "file menu", lambda: _file_menu(page)
    yield "new file dialog", lambda: _sheet(page, "button.tree-tool[title='New file']")
    yield "restore question", lambda: _restore_question(page)
    yield "done dialog", lambda: _sheet(page, ".flow-actions button:has-text('Done')")
    yield "solution dialog", lambda: _sheet(page, ".flow-actions button:has-text('Solution')")
    yield "start dialog", lambda: _start_dialog(page)
    yield "mock", lambda: _open(page, "#/mock", ".mock-form")
    yield "progress", lambda: _open(page, "#/progress", ".stats-summary")
    yield "health", lambda: _open(page, "#/health", "table.checks", RUN_WAIT_MS)
    yield "settings", lambda: _open(page, "#/settings", "#pref-vim")
    yield "mock running", lambda: _mock_running(page)


def _open(page: Any, route: str, shown: str, timeout: int = WAIT_MS) -> None:
    page.keyboard.press("Escape")
    page.evaluate("route => { location.hash = route }", route)
    page.wait_for_selector(shown, timeout=timeout)


def _attempt_with_results(page: Any) -> None:
    page.click("a.button.primary")
    page.click(FILE_BUTTON)
    page.wait_for_selector(".panel:not([hidden]) .cm-content")
    page.click(".run-button.primary")
    page.wait_for_selector(".result-summary-text", timeout=RUN_WAIT_MS)


def _file_menu(page: Any) -> None:
    page.focus(FILE_BUTTON)
    page.keyboard.press("Shift+F10")
    page.wait_for_selector(".tree-menu [role=menuitem]")


def _sheet(page: Any, opener: str) -> None:
    page.keyboard.press("Escape")
    page.click(opener)
    page.wait_for_selector(SHEET)


def _restore_question(page: Any) -> None:
    """Restoring a starter file the page saved asks first, since its changes go."""
    page.keyboard.press("Escape")
    page.click(".panel:not([hidden]) .cm-content")
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("\n# changed\n")
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector(f"{FILE_BUTTON} .badge")
    _file_menu(page)
    page.click(".tree-menu [role=menuitem]:has-text('Restore')")
    page.wait_for_selector(SHEET)


def _start_dialog(page: Any) -> None:
    _open(page, f"#/problems/{SINGLE_FILE}", ".practice-actions button.primary")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)


def _mock_running(page: Any) -> None:
    _open(page, "#/mock", ".mock-form")
    page.fill("#mock-count", "1")
    page.click(".mock-form button[type=submit]")
    page.wait_for_selector(".mock-card")


def _checked(page: Any) -> list[str]:
    found: list[str] = []
    for scheme in SCHEMES:
        for width in WIDTHS:
            page.emulate_media(color_scheme=scheme)
            page.set_viewport_size({"width": width, "height": HEIGHT})
            page.evaluate(AT_REST)
            where = f"in {scheme} at {width}"
            response = axe_playwright.Axe().run(page, options=RULES).response
            found.extend(_described(response["violations"], where))
            found.extend(_reflow(page, where))
    return found


def _reflow(page: Any, where: str) -> list[str]:
    """WCAG 1.4.10, which axe-core does not check: the page never scrolls sideways; a wide table
    or bar scrolls in its own box."""
    wide = page.evaluate("document.documentElement.scrollWidth")
    window = page.evaluate("document.documentElement.clientWidth")
    return [f"reflow: the page is {wide} pixels wide, {where}"] if wide > window else []


def _described(violations: list[dict[str, Any]], where: str) -> list[str]:
    return [
        f"{violation['id']} ({violation['impact']}): {node['target']}, {where}"
        for violation in violations
        for node in violation["nodes"]
    ]


@pytest.mark.parametrize("view", VIEWS)
def test_the_view_has_no_accessibility_violation(violations, view):
    assert violations[view] == []
