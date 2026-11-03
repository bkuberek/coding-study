"""Code intelligence in a real browser against the real basedpyright
(docs/specs/web-ui.md#testing), in each engine of `tests/browsers.py`: an undefined name is
underlined, hovering `sorted` shows its documentation, Cmd-click (Ctrl-click off macOS) on `sorted`
opens `builtins.pyi` in a read-only library tab, and with autocomplete on, typing `so` offers
`sorted` with its documentation in the panel.

The servers are installed in `.cs/lsp/` of the practice workspace from the shipped lock, which needs
Node, pnpm and, the first time, the network; the test is skipped where they cannot be installed.
Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.preferences_fs import FsPreferencesStore
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.domain.preferences import Preferences, preferences_document
from tests.browsers import launched, watched
from tests.intelligence_lab import (
    ACTIVE_TAB,
    EDITOR,
    PANEL,
    PYTHON,
    point_at,
)
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        shutil.which("node") is None or shutil.which("pnpm") is None,
        reason="node and pnpm are not installed",
    ),
]
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SERVER_MS = 180_000
"""Generous: a real server starts and checks a file slowly on a loaded machine."""
SOURCE = "total = undefined_name + 1\nprint(sorted([3, 1, 2]))\n"
UNDEFINED = (0, 8)
SORTED = (1, 8)
"""The line and column inside `undefined_name` and `sorted`."""
SEGMENT = ".statusbar .code-intelligence"
DOCUMENTATION_OF_SORTED = "Return a new list containing all items from the iterable"
LIST = ".cm-tooltip-autocomplete"


@dataclass
class Seen:
    underlined: list[str] = field(default_factory=list[str])
    hover: str = ""
    library_badge: str = ""
    library_path: str = ""
    library_readonly: str = ""
    library_text: str = ""
    library_cursor_line: str = ""
    offered: list[str] = field(default_factory=list[str])
    panel: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def installed(practice_workspace: Path) -> Path:
    directory = LspDirectory(practice_workspace, SubprocessToolProbe(), SubprocessCommandRunner())
    result = directory.install()
    if result is None or result.exit_code != 0:
        pytest.skip(f"the language servers are not installed: {result and result.output}")
    return practice_workspace / ".cs" / "lsp"


@dataclass
class Real:
    server: RunningServer
    attempt: int


@pytest.fixture(scope="module")
def real(
    engine: str, practice_workspace: Path, installed: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Real]:
    workspace = workspace_like(practice_workspace, tmp_path_factory.mktemp(f"real-{engine}") / "ws")
    (workspace / ".cs").mkdir(exist_ok=True)
    (workspace / ".cs" / "lsp").symlink_to(installed, target_is_directory=True)
    slug, language = PYTHON
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", slug, "--lang", language, "--no-open"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    (workspace / "python" / "practice" / "two_sum.py").write_text(SOURCE)
    preferences = Preferences(code_intelligence=True, autocomplete=True)
    FsPreferencesStore(workspace).write(preferences_document(preferences))
    with running_server(workspace) as running:
        yield Real(running, opened_page(running).attempts[slug])


@pytest.fixture(scope="module")
def seen(engine: str, real: Real) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(SERVER_MS)
        page.goto(real.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("id => { location.hash = `#/attempts/${id}` }", real.attempt)
        page.wait_for_selector(EDITOR)
        page.wait_for_function(
            "selector => document.querySelector(selector)?.textContent.includes('ready')",
            arg=SEGMENT,
        )
        _underlined(page, found)
        _hover(page, found)
        _definition(page, found)
        _completion(page, found)
        browser.close()
    return found


def _underlined(page: Any, found: Seen) -> None:
    page.wait_for_selector(f"{PANEL} .cm-lintRange-error")
    found.underlined = page.locator(f"{PANEL} .cm-lintRange-error").all_inner_texts()


def _hover(page: Any, found: Seen) -> None:
    point = point_at(page, *SORTED)
    page.mouse.move(point["x"], point["y"])
    page.wait_for_selector(".cm-tooltip-hover .cs-hover")
    page.wait_for_function(
        "text => document.querySelector('.cm-tooltip-hover .cs-hover')?.textContent.includes(text)",
        arg=DOCUMENTATION_OF_SORTED,
    )
    found.hover = page.locator(".cm-tooltip-hover .cs-hover").inner_text()
    page.mouse.move(5, 5)


def _definition(page: Any, found: Seen) -> None:
    point = point_at(page, *SORTED)
    page.keyboard.down("ControlOrMeta")
    page.mouse.click(point["x"], point["y"])
    page.keyboard.up("ControlOrMeta")
    page.wait_for_selector(f"{ACTIVE_TAB} .badge")
    page.wait_for_selector(f"{PANEL} .cm-content")
    found.library_badge = page.locator(f"{ACTIVE_TAB} .badge").inner_text()
    found.library_path = page.get_attribute(ACTIVE_TAB, "title")
    found.library_readonly = page.get_attribute(f"{PANEL} .cm-content", "aria-readonly")
    page.wait_for_selector(f"{PANEL} .cm-activeLine")
    found.library_text = page.locator(f"{PANEL} .cm-activeLine").inner_text()
    found.library_cursor_line = page.locator(
        f"{PANEL} .cm-lineNumbers .cm-activeLineGutter"
    ).inner_text()
    page.keyboard.press("Control+Minus")
    page.wait_for_function(
        "selector => !document.querySelector(selector)?.querySelector('.badge')", arg=ACTIVE_TAB
    )


def _completion(page: Any, found: Seen) -> None:
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("so")
    labels = f"{LIST} .cm-completionLabel"
    page.wait_for_function(
        "s => [...document.querySelectorAll(s)].some((e) => e.textContent === 'sorted')", arg=labels
    )
    found.offered = page.locator(labels).all_inner_texts()
    page.keyboard.type("rte")
    page.wait_for_selector(".cm-completionInfo")
    page.wait_for_function(
        "text => document.querySelector('.cm-completionInfo')?.textContent.includes(text)",
        arg=DOCUMENTATION_OF_SORTED,
    )
    found.panel = page.locator(".cm-completionInfo").inner_text()


def test_an_undefined_name_is_underlined(seen):
    assert seen.underlined == ["undefined_name"]


def test_hovering_sorted_shows_its_documentation(seen):
    assert DOCUMENTATION_OF_SORTED in seen.hover


def test_cmd_or_ctrl_click_on_sorted_opens_builtins_pyi_read_only(seen):
    assert (seen.library_badge, seen.library_readonly) == ("library", "true")
    assert seen.library_path.endswith("builtins.pyi")


def test_the_cursor_is_on_the_definition_of_sorted(seen):
    assert "def sorted" in seen.library_text


def test_typing_so_offers_sorted(seen):
    assert "sorted" in seen.offered


def test_the_panel_of_sorted_shows_its_documentation(seen):
    assert DOCUMENTATION_OF_SORTED in seen.panel


def test_the_page_logs_no_error_against_the_real_server(seen):
    assert seen.errors == []
