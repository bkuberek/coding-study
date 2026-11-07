"""The Settings view's page in a real browser (docs/specs/web-ui.md#settings-view), in each engine
of `tests/browsers.py`: it fills the page in two columns that stack with the workspace first, keeps
a readable line length, opens the workspace's column with its path and a working copy button, and
keeps `Reset progress…` red and apart.

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

WAIT_MS = 60_000
WIDE = {"width": 1440, "height": 900}
VERY_WIDE = {"width": 2560, "height": 1200}
MEDIUM = {"width": 900, "height": 900}
NARROW = {"width": 390, "height": 844}
READABLE_PX = 640
"""About 72 characters of the help text."""
READY = "ul.languages .language-name"
COLUMNS = ".settings-column"
RESET_PROGRESS = "button:has-text('Reset progress')"
SHEET = "dialog.sheet[open]"
COPY = ".workspace-path button"


@dataclass
class Layout:
    """What a width shows: the two columns' boxes, and whether the page scrolls sideways."""

    first: dict[str, float]
    second: dict[str, float]
    sideways: bool


@dataclass
class Seen:
    fills: bool = False
    wide: Layout | None = None
    medium: Layout | None = None
    narrow: Layout | None = None
    column_headings: list[str] = field(default_factory=list[str])
    longest_help_px: float = 0
    longest_label_row_px: float = 0
    first_after_heading: str = ""
    path_shown: str = ""
    copied: str = ""
    copy_says: str = ""
    copy_name: str = ""
    fail_ink: str = ""
    reset_progress_ink: str = ""
    reset_progress_in_a_column: bool = False
    dialog_reset_ink: str = ""
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"settings-page-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        context = browser.new_context(viewport=WIDE)
        if engine == "chromium":
            context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = watched(context.new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(READY)
        _read_the_columns(page, found)
        _read_the_widths(page, found)
        _read_the_path(page, found, engine)
        _read_the_danger(page, found)
        browser.close()
    return found


def _layout(page: Any, viewport: dict[str, int]) -> Layout:
    page.set_viewport_size(viewport)
    first, second = page.locator(COLUMNS).all()
    return Layout(
        first.bounding_box(),
        second.bounding_box(),
        page.evaluate("document.documentElement.scrollWidth > window.innerWidth"),
    )


def _read_the_columns(page: Any, found: Seen) -> None:
    found.fills = page.evaluate(
        """() => {
            const main = document.querySelector("main");
            const { paddingLeft, paddingRight } = getComputedStyle(main);
            const room = main.clientWidth - parseFloat(paddingLeft) - parseFloat(paddingRight);
            return document.querySelector(".settings").getBoundingClientRect().width === room;
        }"""
    )
    found.column_headings = page.locator(f"{COLUMNS} > h2").all_inner_texts()


def _read_the_widths(page: Any, found: Seen) -> None:
    found.wide = _layout(page, WIDE)
    found.medium = _layout(page, MEDIUM)
    found.narrow = _layout(page, NARROW)
    page.set_viewport_size(VERY_WIDE)
    found.longest_help_px = page.evaluate(
        """() => Math.max(...[...document.querySelectorAll(".settings p")].map(
            (line) => line.getBoundingClientRect().width))"""
    )
    page.set_viewport_size(WIDE)


def _read_the_path(page: Any, found: Seen, engine: str) -> None:
    found.first_after_heading = page.evaluate(
        f"""() => document.querySelector("{COLUMNS} > h2").nextElementSibling.className"""
    )
    found.path_shown = page.locator(".workspace-path code").inner_text()
    found.copy_name = page.get_attribute(COPY, "aria-label") or ""
    page.click(COPY)
    page.wait_for_selector(f"{COPY}:has-text('copied')")
    found.copy_says = page.locator(COPY).inner_text()
    if engine == "chromium":
        found.copied = page.evaluate("navigator.clipboard.readText()")


def _background(page: Any, selector: str) -> str:
    return page.locator(selector).evaluate("button => getComputedStyle(button).backgroundColor")


def _read_the_danger(page: Any, found: Seen) -> None:
    found.fail_ink = page.evaluate(
        """() => {
            const probe = document.createElement("span");
            probe.style.color = "var(--fail)";
            document.body.append(probe);
            const ink = getComputedStyle(probe).color;
            probe.remove();
            return ink;
        }"""
    )
    found.reset_progress_ink = _background(page, RESET_PROGRESS)
    found.reset_progress_in_a_column = page.locator(f"{COLUMNS} {RESET_PROGRESS}").count() == 1
    page.click(RESET_PROGRESS)
    page.wait_for_selector(f"{SHEET} input[type=text]")
    found.dialog_reset_ink = _background(page, f"{SHEET} button[type=submit]")
    page.keyboard.press("Escape")


def test_settings_fills_the_page(seen):
    assert seen.fills


def test_the_columns_sit_side_by_side_on_a_wide_window(seen):
    assert seen.wide.first["y"] == seen.wide.second["y"]
    assert seen.wide.first["x"] + seen.wide.first["width"] < seen.wide.second["x"]


def test_the_columns_are_equally_wide(seen):
    assert seen.wide.first["width"] == seen.wide.second["width"]


def test_the_workspace_comes_first_and_the_global_settings_second(seen):
    assert seen.column_headings == ["THIS WORKSPACE", "ALL YOUR WORKSPACES"]


@pytest.mark.parametrize("width", ["medium", "narrow"])
def test_below_the_width_where_both_fit_they_stack_with_the_workspace_first(seen, width):
    layout = getattr(seen, width)
    assert layout.first["y"] + layout.first["height"] <= layout.second["y"]


@pytest.mark.parametrize("width", ["wide", "medium", "narrow"])
def test_the_page_never_scrolls_sideways(seen, width):
    assert not getattr(seen, width).sideways


def test_a_line_stays_readable_on_a_very_wide_window(seen):
    assert seen.longest_help_px <= READABLE_PX


def test_the_workspace_column_opens_with_the_path(seen):
    assert seen.first_after_heading == "workspace-path"


def test_the_path_is_the_workspace(seen, workspace):
    assert seen.path_shown == str(workspace)


def test_the_copy_button_copies_the_path(seen, workspace, engine):
    if engine != "chromium":
        pytest.skip("only Chromium lets a page read the clipboard back")
    assert seen.copied == str(workspace)


def test_the_copy_button_says_it_copied(seen):
    assert seen.copy_says == "copied"


def test_the_copy_button_is_named_for_what_it_copies(seen):
    assert seen.copy_name == "Copy the workspace path"


def test_reset_progress_is_red(seen):
    assert seen.reset_progress_ink == seen.fail_ink


def test_the_dialog_keeps_its_reset_red(seen):
    assert seen.dialog_reset_ink == seen.fail_ink


def test_reset_progress_stays_in_the_workspace_column(seen):
    assert seen.reset_progress_in_a_column


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.logged == []
