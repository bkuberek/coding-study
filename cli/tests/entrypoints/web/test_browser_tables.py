"""The page's tables in a real browser (docs/specs/web-ui.md#keyboard-and-accessibility), in each
engine of `tests/browsers.py`, wide and narrow: only `thead th` is a column header. A row header in
the body looks like its row, with no header background, no heavy rule and no sticky position, and
once a table has scrolled no body cell paints over the stuck header, in the first column as well as
the others.

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
WIDE = {"width": 1440, "height": 500}
NARROW = {"width": 900, "height": 500}
"""Short, so each table outgrows the window; narrow enough, the second, to scroll in its own box."""
TABLES = {
    "problems": ("#/", "table.problems"),
    "progress": ("#/progress", "table.stats-table"),
    "health": ("#/health", ".checks-region table"),
}
CHECKS = [
    {"name": f"check {number}", "status": "pass", "detail": "fine", "fix": None}
    for number in range(40)
]
HEAVY_RULE = "inset"
TRANSPARENT = "rgba(0, 0, 0, 0)"
SCROLL = """table => {
  const box = table.closest(".table-scroll");
  window.scrollTo(0, 0);
  box.scrollTop = 0;
  if (box.scrollHeight > box.clientHeight + 1) box.scrollTop = box.scrollHeight;
  else window.scrollTo(0, document.documentElement.scrollHeight);
}"""
OVER_THE_HEADER = """table => [...table.querySelectorAll("thead th")]
  .filter((cell) => cell.getBoundingClientRect().width > 0)
  .map((cell) => {
    const { left, top, width, height } = cell.getBoundingClientRect();
    const found = document.elementFromPoint(left + width / 2, top + height / 2);
    return found === cell || cell.contains(found) ? "" : `${cell.textContent}: ${found?.tagName}`;
  })
  .filter(Boolean)"""
ROWS_UNDER_THE_HEADER = """table => {
  const bottom = table.querySelector("thead th").getBoundingClientRect().bottom;
  return [...table.querySelectorAll("tbody tr")]
    .filter((row) => row.getBoundingClientRect().top < bottom).length;
}"""
HEADER_POSITIONS = """table => [...new Set([...table.querySelectorAll("thead th")]
  .map((cell) => getComputedStyle(cell).position))]"""
BODY_POSITIONS = """table => [...new Set([...table.querySelectorAll("tbody th, tbody td")]
  .map((cell) => getComputedStyle(cell).position))]"""
ROW_HEADER = """table => {
  const cell = table.querySelector("tbody th");
  const style = getComputedStyle(cell);
  const plain = getComputedStyle(table.querySelector("tbody td"));
  return {
    shadow: style.boxShadow,
    background: style.backgroundColor,
    transform: style.textTransform,
    rule: style.borderBottomWidth,
    plain_rule: plain.borderBottomWidth,
    padding: style.paddingTop,
    plain_padding: plain.paddingTop,
    align: style.textAlign,
  };
}"""


@dataclass
class Seen:
    over_the_header: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    rows_under_the_header: dict[str, int] = field(default_factory=dict[str, int])
    header_positions: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    body_positions: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    row_header: dict[str, str] = field(default_factory=dict[str, str])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"tables-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport=WIDE), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.route(
            "**/api/v1/doctor",
            lambda route: route.fulfill(json={"passed": True, "checks": CHECKS}),
        )
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        for size_name, size in (("wide", WIDE), ("narrow", NARROW)):
            page.set_viewport_size(size)
            for name, (route, table) in TABLES.items():
                _measure(page, found, f"{name} {size_name}", route, table)
        page.set_viewport_size(WIDE)
        page.evaluate(f"location.hash = '{TABLES['progress'][0]}'")
        found.row_header = page.locator(f"{TABLES['progress'][1]} tbody tr >> nth=0").evaluate(
            f"row => ({ROW_HEADER})(row.closest('table'))"
        )
        browser.close()
    return found


def _measure(page: Any, found: Seen, name: str, route: str, selector: str) -> None:
    page.evaluate(f"location.hash = '{route}'")
    page.wait_for_selector(f"{selector} tbody tr")
    table = page.locator(selector)
    table.evaluate(SCROLL)
    found.over_the_header[name] = table.evaluate(OVER_THE_HEADER)
    found.rows_under_the_header[name] = table.evaluate(ROWS_UNDER_THE_HEADER)
    found.header_positions[name] = table.evaluate(HEADER_POSITIONS)
    found.body_positions[name] = table.evaluate(BODY_POSITIONS)


NAMES = [f"{table} {size}" for table in TABLES for size in ("wide", "narrow")]


@pytest.mark.parametrize("name", NAMES)
def test_rows_scroll_under_the_header(seen, name):
    assert seen.rows_under_the_header[name] > 0


@pytest.mark.parametrize("name", NAMES)
def test_the_header_cells_are_on_top_of_every_column_after_a_scroll(seen, name):
    assert seen.over_the_header[name] == []


@pytest.mark.parametrize("name", NAMES)
def test_the_column_headers_stick(seen, name):
    assert seen.header_positions[name] == ["sticky"]


@pytest.mark.parametrize("name", NAMES)
def test_no_body_cell_is_positioned(seen, name):
    assert seen.body_positions[name] == ["static"]


def test_a_row_header_has_no_heavy_rule(seen):
    assert HEAVY_RULE not in seen.row_header["shadow"]


def test_a_row_header_has_no_header_background(seen):
    assert seen.row_header["background"] == TRANSPARENT


def test_a_row_header_is_not_set_in_capitals(seen):
    assert seen.row_header["transform"] == "none"


def test_a_row_header_has_the_rule_of_its_row(seen):
    assert seen.row_header["rule"] == seen.row_header["plain_rule"]


def test_a_row_header_has_the_padding_of_its_row(seen):
    assert seen.row_header["padding"] == seen.row_header["plain_padding"]


def test_a_row_header_starts_at_the_left_of_its_column(seen):
    assert seen.row_header["align"] in {"left", "start"}


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors == []
