"""The top bar and the table headers stay in view while the page scrolls, in a real browser
(docs/specs/web-ui.md#page, docs/specs/web-ui.md#keyboard-and-accessibility), in each engine of
`tests/browsers.py`. Each test scrolls and then measures where things are laid out: the bar's top
stays at 0, a table's header stays under it with the rows scrolled beneath, a window too narrow for
a table scrolls it in its own box with the header on top of its rows, and the Attempt view, which
fits the window between its bars, grows no second scrollbar.

The workspace is a bare one over the catalog of the checkout, with one Python attempt started in
it. Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
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

WAIT_MS = 60_000
SLUG = "two-sum"
BAR = ".topbar"
ROWS = "table.problems tbody tr"
LISTING = ".listing:not([aria-busy])"
HEALTH_ROWS = "table.checks tbody tr"
HEALTH_REGION = ".checks-region"
SCROLLED_PX = 3000
WIDE = (1440, 900)
MIDDLE = (900, 700)
PHONE = (390, 844)
SHORT = (1440, 560)
"""A window shorter than the Attempt view's workbench, which keeps a height of its own."""
HEADER_CELL = "thead th"
SUBPIXEL = 1.0

PAGE_PLACES = """([bar, header, rows]) => {
  const place = (selector) => {
    const found = document.querySelector(selector);
    return found ? found.getBoundingClientRect() : null;
  };
  const cell = place(header);
  const at = (x, y) => document.elementFromPoint(x, y);
  return {
    scrolled: window.scrollY,
    bar: place(bar),
    header: cell,
    header_on_top: cell
      ? at(cell.left + 20, cell.top + cell.height / 2)?.closest("thead") !== null
      : null,
    rows_beneath: cell ? [...document.querySelectorAll(rows)].filter(
      (row) => row.getBoundingClientRect().bottom <= cell.bottom).length : null,
    page_width: document.documentElement.scrollWidth,
    window_width: window.innerWidth,
  };
}"""
"""Where the bar and the first header cell are laid out, whether that cell is what a click at its
middle would hit, and how many rows lie above its lower edge."""


@dataclass
class Places:
    """Positions in CSS pixels from the top of the window, after a scroll."""

    scrolled: float = 0
    bar_top: float = 1
    bar_bottom: float = 0
    bar_height: float = 0
    header_top: float = -1
    header_on_top: bool = False
    rows_beneath: int = 0
    page_width: float = 0
    window_width: float = 0


@dataclass
class Region:
    """A table's own scroll box, after its rows were scrolled and its width measured."""

    top: float = 0
    header_top: float = -1
    header_on_top: bool = False
    scrolled_rows: float = 0
    sideways_overflow: float = 0
    scrolled_sideways: float = 0
    keyboard_focusable: bool = False


@dataclass
class Visit:
    problems: Places = field(default_factory=Places)
    health: Places = field(default_factory=Places)
    middle: Region = field(default_factory=Region)
    middle_page: Places = field(default_factory=Places)
    phone: Region = field(default_factory=Region)
    phone_page: Places = field(default_factory=Places)
    problem_view: Places = field(default_factory=Places)
    side_top: float = 0
    attempt_page_height: float = 0
    attempt_window_height: float = 0
    attempt_head_top: float = 0
    attempt_bar_bottom: float = 0
    attempt_short: Places = field(default_factory=Places)
    attempt_short_status_bottom: float = 0
    attempt_short_window: float = 0
    main_top_on_anchor: float = 0
    focused_link_top: float = 0
    focused_header_bottom: float = 0
    narrow_link_top: float = 0
    narrow_header_bottom: float = 0
    menu_item_on_top: bool = False
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = mark_workspace(tmp_path_factory.mktemp(f"navigation-{engine}") / "workspace")
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", SLUG, "--no-open"],
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
def visit(engine: str, server: RunningServer) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(
            browser.new_page(viewport={"width": WIDE[0], "height": WIDE[1]}), seen.errors
        )
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(ROWS)
        _wide_problems(page, seen)
        _wide_health(page, seen)
        _problem_view(page, seen)
        _attempt_view(page, seen)
        _middle_window(page, seen)
        _phone(page, seen)
        browser.close()
    return seen


def _window(page: Any, size: tuple[int, int]) -> None:
    page.set_viewport_size({"width": size[0], "height": size[1]})


def _open(page: Any, route: str, shown: str) -> None:
    page.evaluate("route => { location.hash = route }", route)
    page.wait_for_selector(shown)


def _places(page: Any, header: str = HEADER_CELL, rows: str = ROWS) -> Places:
    raw = page.evaluate(PAGE_PLACES, [BAR, header, rows])
    bar, cell = raw["bar"], raw["header"]
    return Places(
        scrolled=raw["scrolled"],
        bar_top=bar["top"],
        bar_bottom=bar["bottom"],
        bar_height=bar["height"],
        header_top=cell["top"] if cell else -1,
        header_on_top=bool(raw["header_on_top"]),
        rows_beneath=raw["rows_beneath"] or 0,
        page_width=raw["page_width"],
        window_width=raw["window_width"],
    )


def _scroll_page(page: Any, distance: int = SCROLLED_PX) -> None:
    page.evaluate("distance => window.scrollTo(0, distance)", distance)


def _wide_problems(page: Any, seen: Visit) -> None:
    _scroll_page(page)
    seen.problems = _places(page)
    _focus_a_link_far_down(page, seen)
    _anchor_to_main(page, seen)
    _menu_over_the_header(page, seen)


def _focus_a_link_far_down(page: Any, seen: Visit) -> None:
    """Moves the focus to a row's link, as Tab does, and reads how far under the header it lies."""
    _scroll_page(page, 0)
    page.focus(f"{ROWS}:nth-child(80) a.problem-link")
    link = page.locator(f"{ROWS}:nth-child(80) a.problem-link").evaluate(
        "e => e.getBoundingClientRect().top"
    )
    seen.focused_link_top = link
    seen.focused_header_bottom = page.locator(HEADER_CELL).first.evaluate(
        "e => e.getBoundingClientRect().bottom"
    )


def _anchor_to_main(page: Any, seen: Visit) -> None:
    """Scrolls `main` into view, as the skip link and an in-page anchor do."""
    _scroll_page(page)
    page.evaluate("document.getElementById('main').scrollIntoView()")
    seen.main_top_on_anchor = page.locator("main").evaluate("e => e.getBoundingClientRect().top")


def _menu_over_the_header(page: Any, seen: Visit) -> None:
    """Opens the attempts menu while the header is stuck under the bar: the menu is above it."""
    _scroll_page(page)
    page.click(".attempts-menu summary")
    item = page.locator(".menu-list a").first
    seen.menu_item_on_top = item.evaluate(
        """e => { const r = e.getBoundingClientRect();
        const hit = document.elementFromPoint(r.left + 10, r.top + r.height / 2);
        return hit?.closest('.menu-list') !== null; }"""
    )
    page.click(".attempts-menu summary")


def _wide_health(page: Any, seen: Visit) -> None:
    _open(page, "#/health", HEALTH_ROWS)
    _scroll_page(page)
    seen.health = _places(page, rows=HEALTH_ROWS)


def _problem_view(page: Any, seen: Visit) -> None:
    _open(page, f"#/problems/{SLUG}", ".problem-side")
    _scroll_page(page)
    seen.problem_view = _places(page, header="main", rows="main")
    seen.side_top = page.locator(".problem-side").evaluate("e => e.getBoundingClientRect().top")


def _attempt_view(page: Any, seen: Visit) -> None:
    _open(page, "#/attempts/1", ".workbench:not([aria-busy]) .attempt-head")
    seen.attempt_page_height = page.evaluate("document.documentElement.scrollHeight")
    seen.attempt_window_height = page.evaluate("window.innerHeight")
    seen.attempt_head_top = page.locator(".attempt-head").evaluate(
        "e => e.getBoundingClientRect().top"
    )
    seen.attempt_bar_bottom = page.locator(BAR).evaluate("e => e.getBoundingClientRect().bottom")
    _window(page, SHORT)
    _scroll_page(page, 400)
    seen.attempt_short = _places(page, header=".attempt-head", rows=".attempt-head")
    seen.attempt_short_status_bottom = page.locator(".statusbar").evaluate(
        "e => e.getBoundingClientRect().bottom"
    )
    seen.attempt_short_window = page.evaluate("window.innerHeight")
    _window(page, WIDE)


def _middle_window(page: Any, seen: Visit) -> None:
    _window(page, MIDDLE)
    _open(page, "#/", ROWS)
    _turn_on_every_column(page)
    seen.middle = _region(page, LISTING)
    _focus_a_link_in_the_box(page, seen)
    _scroll_page(page)
    seen.middle_page = _places(page)
    _scroll_page(page, 0)


def _turn_on_every_column(page: Any) -> None:
    """The table starts with few enough columns to fit this window; with all of them it does not."""
    page.click(".columns-menu > summary")
    for column in ("kind", "scope", "domain", "role"):
        page.check(f"#column-{column}")
    page.wait_for_selector("table.problems thead th:has-text('role')")
    page.keyboard.press("Escape")


def _focus_a_link_in_the_box(page: Any, seen: Visit) -> None:
    """Moves the focus to a row's link in the table's own box, scrolled to its end."""
    page.locator(LISTING).evaluate("e => { e.scrollTop = e.scrollHeight; }")
    page.focus(f"{ROWS}:nth-child(20) a.problem-link")
    seen.narrow_link_top = page.locator(f"{ROWS}:nth-child(20) a.problem-link").evaluate(
        "e => e.getBoundingClientRect().top"
    )
    seen.narrow_header_bottom = page.locator(HEADER_CELL).first.evaluate(
        "e => e.getBoundingClientRect().bottom"
    )


def _phone(page: Any, seen: Visit) -> None:
    _window(page, PHONE)
    _open(page, "#/", ROWS)
    seen.phone = _region(page, LISTING)
    _scroll_page(page)
    seen.phone_page = _places(page)


def _region(page: Any, selector: str) -> Region:
    """Scrolls the table's own box down and to the right, and measures it."""
    box = page.locator(selector)
    box.evaluate("e => { e.scrollTop = 3000; e.scrollLeft = 100; }")
    raw = box.evaluate(
        """e => { const header = e.querySelector('thead th').getBoundingClientRect();
        return {
          top: e.getBoundingClientRect().top, header_top: header.top,
          header_on_top: document.elementFromPoint(header.left + 20, header.top + header.height / 2)
            ?.closest('thead') !== null,
          scrolled_rows: e.scrollTop, sideways_overflow: e.scrollWidth - e.clientWidth,
          scrolled_sideways: e.scrollLeft, keyboard_focusable: e.tabIndex >= 0 };
        }"""
    )
    return Region(**raw)


def test_the_bar_stays_at_the_top_of_the_problems_view_after_scrolling(visit):
    assert (visit.problems.scrolled > 0, visit.problems.bar_top) == (True, 0)


def test_the_header_of_the_problems_table_stays_just_under_the_bar(visit):
    assert abs(visit.problems.header_top - visit.problems.bar_bottom) < SUBPIXEL


def test_the_rows_of_the_problems_table_scroll_beneath_its_header(visit):
    assert visit.problems.rows_beneath > 0


def test_the_header_of_the_problems_table_is_what_a_click_under_the_bar_hits(visit):
    assert visit.problems.header_on_top


def test_the_bar_stays_at_the_top_of_the_health_view_after_scrolling(visit):
    assert (visit.health.scrolled > 0, visit.health.bar_top) == (True, 0)


def test_the_header_of_the_checks_stays_just_under_the_bar(visit):
    assert abs(visit.health.header_top - visit.health.bar_bottom) < SUBPIXEL


def test_the_header_of_the_checks_is_what_a_click_under_the_bar_hits(visit):
    assert visit.health.header_on_top


def test_the_bar_stays_at_the_top_of_the_problem_view_after_scrolling(visit):
    assert (visit.problem_view.scrolled > 0, visit.problem_view.bar_top) == (True, 0)


def test_the_side_column_of_the_problem_view_sticks_below_the_bar(visit):
    assert visit.side_top >= visit.problem_view.bar_bottom


def test_the_bar_is_not_taller_than_its_row(visit):
    assert visit.problems.bar_height == 40


def test_a_row_focused_far_down_is_not_hidden_under_the_header(visit):
    assert visit.focused_link_top >= visit.focused_header_bottom


def test_an_anchor_to_main_leaves_its_top_below_the_bar(visit):
    assert visit.main_top_on_anchor >= visit.problems.bar_bottom


def test_the_attempts_menu_opens_above_the_stuck_header(visit):
    assert visit.menu_item_on_top


def test_the_attempt_view_fits_the_window_without_a_second_scrollbar(visit):
    assert visit.attempt_page_height <= visit.attempt_window_height


def test_the_attempt_head_starts_below_the_bar(visit):
    assert visit.attempt_head_top >= visit.attempt_bar_bottom


def test_the_bar_stays_at_the_top_of_a_short_attempt_view_after_scrolling(visit):
    assert (visit.attempt_short.scrolled > 0, visit.attempt_short.bar_top) == (True, 0)


def test_the_status_bar_stays_at_the_bottom_of_a_short_attempt_view(visit):
    assert abs(visit.attempt_short_status_bottom - visit.attempt_short_window) < SUBPIXEL


def test_a_window_too_narrow_for_the_table_scrolls_it_in_its_own_box(visit):
    assert visit.middle.sideways_overflow > 0


def test_the_narrow_table_scrolls_sideways_in_its_box(visit):
    assert visit.middle.scrolled_sideways > 0


def test_the_narrow_table_scrolls_its_rows_in_its_box(visit):
    assert visit.middle.scrolled_rows > 0


def test_the_header_of_the_narrow_table_stays_at_the_top_of_its_box(visit):
    assert abs(visit.middle.header_top - visit.middle.top) < SUBPIXEL


def test_the_header_of_the_narrow_table_is_what_a_click_hits(visit):
    assert visit.middle.header_on_top


def test_the_narrow_table_box_can_take_the_keyboard_focus(visit):
    assert visit.middle.keyboard_focusable


def test_a_row_focused_in_the_narrow_box_is_not_hidden_under_the_header(visit):
    assert visit.narrow_link_top >= visit.narrow_header_bottom


def test_the_bar_stays_at_the_top_of_a_narrow_window_after_scrolling(visit):
    assert (visit.middle_page.scrolled > 0, visit.middle_page.bar_top) == (True, 0)


def test_the_bar_stays_at_the_top_of_a_phone_window_after_scrolling(visit):
    assert (visit.phone_page.scrolled > 0, visit.phone_page.bar_top) == (True, 0)


def test_the_bar_keeps_its_height_in_a_phone_window(visit):
    assert visit.phone_page.bar_height == 40


def test_the_phone_window_never_scrolls_sideways(visit):
    assert visit.phone_page.page_width <= visit.phone_page.window_width


def test_the_phone_table_still_scrolls_sideways_in_its_box(visit):
    assert visit.phone.scrolled_sideways > 0


def test_the_page_logs_no_problem(visit):
    assert visit.errors == []
