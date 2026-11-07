"""The commands the page names read as code text, not as buttons (docs/specs/web-ui.md#page), in
each engine of `tests/browsers.py`: the Next card's start line, the header's next step, the Run
options preview, the Done dialog's command, the Mock view's lock line and the chips of Settings
(`cstudy config edit`, `cstudy reset`) have no border, no fill and no padding around them, only the
prompt that marks them as a shell command.

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

PROBLEM = "two-sum"
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
STYLE = """element => {
  const style = getComputedStyle(element);
  return {
    text: element.textContent,
    border: style.borderTopWidth,
    radius: style.borderTopLeftRadius,
    padding: style.paddingLeft,
    fill: style.backgroundColor,
    image: style.backgroundImage,
    prompt: getComputedStyle(element, '::before').content,
  };
}"""


@dataclass
class Visit:
    """The style of the first command chip of each place the page shows one."""

    chips: dict[str, dict[str, str]] = field(default_factory=dict[str, dict[str, str]])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return mark_workspace(tmp_path_factory.mktemp(f"commands-{engine}") / "workspace")


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, server: RunningServer) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(".next-start .cmd")
        _note(page, seen, "the Next card", ".next-start .cmd")
        _start(page)
        _note(page, seen, "the next step", ".attempt-head .next-step .cmd")
        page.click("button:has-text('Run options')")
        _note(page, seen, "the Run options preview", ".run-options-command .cmd")
        page.click("button:has-text('Done')")
        _note(page, seen, "the Done dialog", f"{SHEET} .cmd")
        page.keyboard.press("Escape")
        _start_a_mock(page)
        _note(page, seen, "the Mock view", ".mock-lock .cmd")
        page.evaluate("location.hash = '#/settings'")
        _note(page, seen, "the config form", ".settings .cmd:has-text('cstudy config edit')")
        _note(page, seen, "the Danger section", ".settings .cmd:has-text('cstudy reset')")
        browser.close()
    return seen


def _note(page: Any, seen: Visit, place: str, selector: str) -> None:
    chip = page.wait_for_selector(selector)
    seen.chips[place] = chip.evaluate(STYLE)


def _start(page: Any) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.click(".practice-actions button.primary")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".attempt-head .flow-actions")


def _start_a_mock(page: Any) -> None:
    page.click("a.tab[data-view=mock]")
    page.fill("#mock-count", "1")
    page.fill("#mock-minutes", "30")
    page.click(".mock-form button[type=submit]")
    page.wait_for_selector(".mock-card")


PLACES = [
    "the Next card",
    "the next step",
    "the Run options preview",
    "the Done dialog",
    "the Mock view",
    "the config form",
    "the Danger section",
]


@pytest.mark.parametrize("place", PLACES)
def test_a_command_has_no_border_around_it(visit, place):
    assert (visit.chips[place]["border"], visit.chips[place]["radius"]) == ("0px", "0px")


@pytest.mark.parametrize("place", PLACES)
def test_a_command_has_no_fill_and_no_padding(visit, place):
    chip = visit.chips[place]
    assert (chip["fill"], chip["image"], chip["padding"]) == ("rgba(0, 0, 0, 0)", "none", "0px")


@pytest.mark.parametrize("place", PLACES)
def test_a_command_keeps_the_prompt_that_marks_it_as_a_shell_command(visit, place):
    assert visit.chips[place]["prompt"] == '"$ "'


def test_the_settings_chips_name_the_commands(visit):
    assert visit.chips["the config form"]["text"] == "cstudy config edit"
    assert visit.chips["the Danger section"]["text"] == "cstudy reset"


def test_the_page_logs_no_error(visit):
    assert visit.errors == []
