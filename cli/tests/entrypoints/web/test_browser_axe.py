"""axe-core over every view of the page (docs/specs/web-ui.md#keyboard-and-accessibility), in
light and dark, 1440 and 390 pixels wide, in each engine of `tests/browsers.py`: the problem list,
a project problem, its attempt with a file in the editor and a run's results, the file tree's menu,
its new-file dialog and restore question, the start, done and solution dialogs, the History of a
problem with a finished attempt, expanded, and the dialog that shows that attempt's code read-only,
the mock view before and during a mock, the progress, health and settings views, and, on a server
whose JDK cannot run Java and Kotlin, the list with its marks, the start dialog of a problem and of
a Java project with the languages disabled, and a start refused with a `fix:` hint; and, with code
intelligence on against the scripted language server, the status bar's segment ready, stopped with
its Restart and for a language whose server is not installed, and the Health view with the
`code intelligence` rows. Each view must have no violation of WCAG 2.2 A and AA, nor of axe's
best practices.

axe-core comes with `axe-playwright-python`, in the optional `browser` dependency group; Playwright
and its engines are set up as `tests/browsers.py` says. Without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.domain.preferences import Preferences, preferences_document
from tests.browsers import launched, refusing_starts
from tests.helpers import mark_workspace, selecting_jdk
from tests.language_server_scripts import ScriptedServer, fake_node, install_fake_basedpyright
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
axe_playwright = pytest.importorskip("axe_playwright_python.sync_playwright", reason="no axe-core")

PROJECT = "bank-project-python"
SINGLE_FILE = "two-sum"
JDK_PROJECT = "bank-project-java"
FILE_BUTTON = "button.tree-file[data-path='bank/bank.py']"
SHEET = "dialog.sheet[open]"
HISTORY_ROW = "ol.attempts > li"
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
    "history",
    "past code dialog",
    "mock",
    "mock running",
    "progress",
    "health",
    "settings",
)
JDK_VIEWS = (
    "problems on a JDK that cannot run Java",
    "start dialog on a JDK that cannot run Java",
    "start dialog of a Java project",
    "start refused with a fix",
)
INTELLIGENCE_VIEWS = (
    "code intelligence ready",
    "code intelligence stopped",
    "code intelligence not installed",
    "health with code intelligence rows",
)
SEGMENT = ".statusbar .code-intelligence"
HEALTH_ROW = "table.checks td.check-name:has-text('code intelligence python')"
SERVES = {"reply": "initialize", "result": {"capabilities": {"textDocumentSync": 2}}}
EXITS: tuple[dict[str, object], ...] = (
    {"reply": "initialize", "result": {"capabilities": {}}},
    {"err": "boom"},
    {"exit": 3},
)
JDK_REFUSAL = (
    "two-sum runs its java version on JDK 21 to 26; "
    "JAVA_HOME selects JDK 27, which cstudy does not support yet"
)
JDK_FIX = "select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: https://example.org/guide#jdk"


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """A workspace with the project in progress and a single-file problem given up on, whose
    History has an attempt to show."""
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp(f"axe-{engine}") / "ws")
    for command in (
        ("start", PROJECT, "--no-open"),
        ("start", SINGLE_FILE, "--lang", "python", "--no-open"),
        ("done", SINGLE_FILE, "--gave-up"),
    ):
        subprocess.run(
            [sys.executable, "-m", "coding_study", *command],
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


@pytest.fixture(scope="module")
def jdk_server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    """A server in a bare workspace whose JDK is a 27, which cstudy does not support yet."""
    workspace = mark_workspace(tmp_path_factory.mktemp(f"axe-jdk-{engine}") / "ws")
    jdk = selecting_jdk(tmp_path_factory.mktemp("axe-jdk-home"), 27)
    with running_server(workspace, variables=jdk) as running:
        yield running


@pytest.fixture(scope="module")
def jdk_violations(engine: str, jdk_server: RunningServer) -> dict[str, list[str]]:
    """The violations of the views a JDK that cannot run Java and Kotlin changes."""
    found: dict[str, list[str]] = {}
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": WIDTHS[0], "height": HEIGHT})
        page.set_default_timeout(WAIT_MS)
        page.goto(jdk_server.login_url)
        page.wait_for_selector("table.problems .ref-blocked")
        refusing_starts(page, JDK_REFUSAL, JDK_FIX)
        for view, show in _jdk_tour(page):
            show()
            found[view] = _checked(page)
            page.set_viewport_size({"width": WIDTHS[0], "height": HEIGHT})
        browser.close()
    return found


@dataclass
class Intelligence:
    """A server with code intelligence on, whose language server is the scripted fake."""

    server: RunningServer
    script: ScriptedServer
    attempts: dict[str, int]


@pytest.fixture(scope="module")
def intelligence(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Intelligence]:
    base = tmp_path_factory.mktemp(f"axe-intelligence-{engine}")
    root = workspace_like(practice_workspace, base / "ws")
    for slug, language in ((SINGLE_FILE, "python"), ("lru-cache", "typescript")):
        subprocess.run(
            [sys.executable, "-m", "coding_study", "start", slug, "--lang", language, "--no-open"],
            env=served_environment(root),
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
        )
    install_fake_basedpyright(root)
    FsPreferencesStore(root).write(preferences_document(Preferences(code_intelligence=True)))
    script = ScriptedServer(base / "server.json")
    script.play(SERVES)
    with running_server(root, variables={"PATH": fake_node(base / "bin", script)}) as running:
        yield Intelligence(running, script, opened_page(running).attempts)


@pytest.fixture(scope="module")
def intelligence_violations(engine: str, intelligence: Intelligence) -> dict[str, list[str]]:
    """The violations of the status bar's code-intelligence segment in each of its states."""
    found: dict[str, list[str]] = {}
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": WIDTHS[0], "height": HEIGHT})
        page.set_default_timeout(WAIT_MS)
        page.goto(intelligence.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        for view, show in _intelligence_tour(page, intelligence):
            show()
            found[view] = _checked(page)
            page.set_viewport_size({"width": WIDTHS[0], "height": HEIGHT})
        browser.close()
    return found


def _intelligence_tour(
    page: Any, intelligence: Intelligence
) -> Iterator[tuple[str, Callable[[], None]]]:
    yield INTELLIGENCE_VIEWS[0], lambda: _segment(page, intelligence, SINGLE_FILE, "ready")
    yield INTELLIGENCE_VIEWS[1], lambda: _stopped_segment(page, intelligence)
    yield INTELLIGENCE_VIEWS[2], lambda: _segment(page, intelligence, "lru-cache", "Health")
    yield INTELLIGENCE_VIEWS[3], lambda: _open(page, "#/health", HEALTH_ROW, RUN_WAIT_MS)


def _segment(page: Any, intelligence: Intelligence, slug: str, word: str) -> None:
    _open(page, f"#/attempts/{intelligence.attempts[slug]}", ".panel:not([hidden]) .cm-content")
    page.wait_for_selector(f"{SEGMENT}:has-text('{word}')")


def _stopped_segment(page: Any, intelligence: Intelligence) -> None:
    """A server that exits after initializing: a reload opens the session again, against it."""
    intelligence.script.play(*EXITS)
    page.reload()
    _segment(page, intelligence, SINGLE_FILE, "Restart")


def _jdk_tour(page: Any) -> Iterator[tuple[str, Callable[[], None]]]:
    yield JDK_VIEWS[0], lambda: None
    yield JDK_VIEWS[1], lambda: _start_dialog(page)
    yield JDK_VIEWS[2], lambda: _java_project_dialog(page)
    yield JDK_VIEWS[3], lambda: _refused_start(page)


def _java_project_dialog(page: Any) -> None:
    _open(page, f"#/problems/{JDK_PROJECT}", ".practice-actions button.primary")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)


def _refused_start(page: Any) -> None:
    _open(page, f"#/problems/{SINGLE_FILE}", ".practice-actions button.primary")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(f"{SHEET} .state-error")


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
    yield "history", lambda: _history(page)
    yield "past code dialog", lambda: _past_code_dialog(page)
    yield "mock", lambda: _open(page, "#/mock", ".mock-form")
    yield "progress", lambda: _open(page, "#/progress", ".stats-summary")
    yield "health", lambda: _open(page, "#/health", "table.checks", RUN_WAIT_MS)
    yield "settings", lambda: _open(page, "#/settings", "ul.languages .language-name")
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


def _history(page: Any) -> None:
    """The first attempt's row opened, with where its files come from."""
    _open(page, f"#/problems/{SINGLE_FILE}", ".statement-pane .prose")
    page.click(f"{HISTORY_ROW} summary")
    page.wait_for_selector(f"{HISTORY_ROW} .past-source")


def _past_code_dialog(page: Any) -> None:
    page.click(f"{HISTORY_ROW} .past-open button")
    page.wait_for_selector(f"{SHEET} .cm-content")


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
            found.extend(_squeezed_segments(page, where))
    return found


def _reflow(page: Any, where: str) -> list[str]:
    """WCAG 1.4.10, which axe-core does not check: the page never scrolls sideways; a wide table
    or bar scrolls in its own box."""
    wide = page.evaluate("document.documentElement.scrollWidth")
    window = page.evaluate("document.documentElement.clientWidth")
    return [f"reflow: the page is {wide} pixels wide, {where}"] if wide > window else []


SQUEEZED_SEGMENTS = """[...document.querySelectorAll('.statusbar .segment')]
  .filter((s) => s.offsetParent !== null
    && s.clientWidth + 1 < Math.min(s.scrollWidth, window.innerWidth / 2))
  .map((s) => s.className)"""
"""Status bar segments narrower than their text or half the window: a narrow window scrolls the
bar instead of squeezing a segment."""


def _squeezed_segments(page: Any, where: str) -> list[str]:
    return [
        f"squeezed: status bar segment .{name.replace(' ', '.')}, {where}"
        for name in page.evaluate(SQUEEZED_SEGMENTS)
    ]


def _described(violations: list[dict[str, Any]], where: str) -> list[str]:
    return [
        f"{violation['id']} ({violation['impact']}): {node['target']}, {where}"
        for violation in violations
        for node in violation["nodes"]
    ]


@pytest.mark.parametrize("view", VIEWS)
def test_the_view_has_no_accessibility_violation(violations, view):
    assert violations[view] == []


@pytest.mark.parametrize("view", INTELLIGENCE_VIEWS)
def test_the_code_intelligence_segment_has_no_accessibility_violation(
    intelligence_violations, view
):
    assert intelligence_violations[view] == []


@pytest.mark.parametrize("view", JDK_VIEWS)
def test_a_view_a_jdk_that_cannot_run_java_changes_has_no_accessibility_violation(
    jdk_violations, view
):
    assert jdk_violations[view] == []
