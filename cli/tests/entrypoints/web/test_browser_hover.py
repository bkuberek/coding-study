"""Hover documentation in a real browser (docs/specs/web-ui.md#hover), in each engine of
`tests/browsers.py`, against the scripted fake language server: the pointer at rest over a symbol
opens the tooltip with the broker's rendered documentation and, in the same box above it, the
diagnostic under the pointer; Cmd or Ctrl-K then Cmd or Ctrl-I opens it from the keyboard and the
polite live region reads its first paragraph; Escape closes it; an answer of null opens none; text
a server sends that is not `cstudy-html` is shown as text, never as markup; and under Vim `K`
opens it.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.preferences import Preferences
from tests.browsers import launched, watched
from tests.intelligence_lab import (
    EDITOR,
    PANEL,
    SERVES,
    Lab,
    intelligence_lab,
    open_attempt,
    store,
    wait_for_status,
)
from tests.language_server_scripts import notification

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
TOOLTIP = ".cm-tooltip-hover"
DOCUMENTATION = f"{TOOLTIP} .cs-hover"
DIAGNOSTIC = f"{TOOLTIP} .cm-tooltip-lint"
LIVE_REGION = ".sr-only[role=status]"
ERROR = f"{PANEL} .cm-lintRange-error"
FUNCTION_LINE = 3
"""`def two_sum(…)` in the starter file."""
RAISE_LINE = 4
MARKDOWN = (
    "```python\n(function) def two_sum(nums, target)\n```\n---\n"
    "Finds the **pair** that adds up.\n\nThe second paragraph."
)
MARKUP = "<img src=x onerror=alert(1)>\n\nThe second paragraph."
ANSWERS = {
    "answer": {
        "textDocument/hover": {
            "cases": [
                {
                    "when": {"position": {"line": FUNCTION_LINE}},
                    "result": {"contents": {"kind": "markdown", "value": MARKDOWN}},
                },
                {
                    "when": {"position": {"line": RAISE_LINE}},
                    "result": {"contents": {"kind": "plaintext", "value": MARKUP}},
                },
            ]
        }
    }
}
ERROR_ON_THE_FUNCTION = {
    "range": {
        "start": {"line": FUNCTION_LINE, "character": 4},
        "end": {"line": FUNCTION_LINE, "character": 11},
    },
    "severity": 1,
    "source": "basedpyright",
    "code": "reportUndefinedVariable",
    "message": '"two_sum" is not defined',
}
SCRIPT = (
    SERVES,
    ANSWERS,
    {"await": "textDocument/didOpen"},
    {
        "send": notification(
            "textDocument/publishDiagnostics",
            {"uri": "$uri", "diagnostics": [ERROR_ON_THE_FUNCTION]},
        )
    },
)
SECOND_PARAGRAPH = "The second paragraph."
FIRST_PARAGRAPH = "Finds the pair that adds up."
TOP_OF = "selector => document.querySelector(selector).getBoundingClientRect().top"


@dataclass
class Seen:
    pointer_documentation: str = ""
    pointer_has_code_block: bool = False
    pointer_diagnostic: str = ""
    diagnostic_above_documentation: bool = False
    pointer_announced: str = ""
    tooltip_after_leaving: int = -1
    keyboard_documentation: str = ""
    keyboard_announced: str = ""
    injected_images: int = -1
    escape_closed: int = -1
    nothing_announced: str = ""
    nothing_tooltips: int = -1
    documentation_is_focusable: bool = False
    vim_documentation: str = ""
    vim_escape_closed: int = -1
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"hover-{engine}")
    with intelligence_lab(practice_workspace, base, SCRIPT) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, lab: Lab) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(lab.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _by_pointer(page, lab, found)
        _by_keyboard(page, found)
        _vim(browser, lab, found)
        browser.close()
    return found


def _by_pointer(page: Any, lab: Lab, found: Seen) -> None:
    open_attempt(page, lab)
    wait_for_status(page, "python · basedpyright · ready · 1 error")
    page.hover(ERROR)
    page.wait_for_selector(DOCUMENTATION)
    page.wait_for_selector(DIAGNOSTIC)
    found.pointer_documentation = page.locator(DOCUMENTATION).inner_text()
    found.pointer_has_code_block = page.locator(f"{DOCUMENTATION} pre").count() > 0
    found.pointer_diagnostic = page.locator(DIAGNOSTIC).inner_text()
    found.diagnostic_above_documentation = page.evaluate(TOP_OF, DIAGNOSTIC) < page.evaluate(
        TOP_OF, DOCUMENTATION
    )
    found.documentation_is_focusable = page.get_attribute(DOCUMENTATION, "tabindex") == "0"
    found.pointer_announced = page.locator(LIVE_REGION).inner_text()
    page.mouse.move(5, 5)
    page.wait_for_selector(TOOLTIP, state="detached")
    found.tooltip_after_leaving = page.locator(TOOLTIP).count()


def _go_to_line(page: Any, line: int) -> None:
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+Home")
    for _ in range(line):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowRight")


def _by_keyboard(page: Any, found: Seen) -> None:
    _go_to_line(page, RAISE_LINE)
    page.keyboard.press("ControlOrMeta+k")
    page.keyboard.press("ControlOrMeta+i")
    page.wait_for_selector(DOCUMENTATION)
    found.keyboard_documentation = page.locator(DOCUMENTATION).inner_text()
    found.injected_images = page.locator(f"{DOCUMENTATION} img").count()
    page.wait_for_function(
        "selector => document.querySelector(selector).textContent !== ''", arg=LIVE_REGION
    )
    found.keyboard_announced = page.locator(LIVE_REGION).inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(TOOLTIP, state="detached")
    found.escape_closed = page.locator(TOOLTIP).count()
    _go_to_line(page, 0)
    page.keyboard.press("ControlOrMeta+k")
    page.keyboard.press("ControlOrMeta+i")
    page.wait_for_function(
        "selector => document.querySelector(selector).textContent.includes('no documentation')",
        arg=LIVE_REGION,
    )
    found.nothing_announced = page.locator(LIVE_REGION).inner_text()
    found.nothing_tooltips = page.locator(DOCUMENTATION).count()


def _vim(browser: Any, lab: Lab, found: Seen) -> None:
    """With Vim on, `K` in normal mode opens the hover at the cursor."""
    store(lab, Preferences(code_intelligence=True, vim=True))
    page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
    page.set_default_timeout(WAIT_MS)
    page.goto(lab.server.login_url)
    page.wait_for_selector("table.problems tbody tr")
    open_attempt(page, lab)
    wait_for_status(page, "python · basedpyright · ready")
    page.click(EDITOR)
    page.keyboard.press("Escape")
    page.keyboard.press("g")
    page.keyboard.press("g")
    for _ in range(RAISE_LINE):
        page.keyboard.press("j")
    page.keyboard.press("K")
    page.wait_for_selector(DOCUMENTATION)
    found.vim_documentation = page.locator(DOCUMENTATION).inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(TOOLTIP, state="detached")
    found.vim_escape_closed = page.locator(TOOLTIP).count()


def test_the_pointer_at_rest_shows_the_rendered_documentation(seen):
    assert FIRST_PARAGRAPH in seen.pointer_documentation


def test_documentation_code_blocks_arrive_as_code(seen):
    assert seen.pointer_has_code_block


def test_a_diagnostic_under_the_pointer_shares_the_box(seen):
    assert "basedpyright reportUndefinedVariable" in seen.pointer_diagnostic


def test_the_diagnostic_is_above_the_documentation(seen):
    assert seen.diagnostic_above_documentation


def test_the_documentation_can_be_scrolled_from_the_keyboard(seen):
    assert seen.documentation_is_focusable


def test_a_hover_by_pointer_is_not_read_out(seen):
    assert seen.pointer_announced == ""


def test_moving_the_pointer_away_closes_the_tooltip(seen):
    assert seen.tooltip_after_leaving == 0


def test_the_keyboard_opens_the_hover_at_the_cursor(seen):
    assert SECOND_PARAGRAPH in seen.keyboard_documentation


def test_the_live_region_reads_the_first_paragraph_as_plain_text(seen):
    assert seen.keyboard_announced == "<img src=x onerror=alert(1)>"


def test_text_that_is_not_cstudy_html_is_never_markup(seen):
    assert seen.injected_images == 0


def test_escape_closes_the_tooltip(seen):
    assert seen.escape_closed == 0


def test_a_keyboard_hover_with_nothing_to_show_says_so(seen):
    assert (seen.nothing_announced, seen.nothing_tooltips) == ("no documentation here", 0)


def test_under_vim_k_opens_the_hover(seen):
    assert SECOND_PARAGRAPH in seen.vim_documentation


def test_under_vim_escape_closes_the_hover(seen):
    assert seen.vim_escape_closed == 0


def test_the_page_logs_no_error_for_hover(seen):
    assert seen.errors == []
