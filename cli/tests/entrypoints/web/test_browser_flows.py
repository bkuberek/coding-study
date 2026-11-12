"""The attempt flows in a real browser (docs/specs/web-ui.md#testing): start a single-file problem
with a time box from its Problem view, turn Vim keybindings on and see them survive a reload, take
a hint, reveal the solution through its question, finish with Done, then start a mock interview
and find Hint locked in its attempt, all under the page's Content Security Policy, in each engine
of `tests/browsers.py`.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
PREFERENCES = Path(".cs") / "serve" / "preferences.json"
WAIT_MS = 60_000
NOTICE_WAIT_MS = 1_500
EDITOR = ".panel:not([hidden]) .cm-editor"
SHEET = "dialog.sheet[open]"
QUESTION_PATH = f"/api/v1/problems/{PROBLEM}/solution"
CONFLICT = "status of 409"
TURN_VIM_ON = "button.toggle:has-text('vim off')"
TURN_VIM_OFF = "button.toggle:has-text('vim on')"


class ConsoleLine(Protocol):
    """A message the page logged, as Playwright reports it."""

    @property
    def type(self) -> str: ...

    @property
    def text(self) -> str: ...

    @property
    def location(self) -> dict[str, Any]: ...


@dataclass
class Practice:
    """What the browser saw from the start of an attempt to the start of a mock."""

    started: str = ""
    vim_after_reload: bool = False
    vim_preference: object = None
    hint: str = ""
    question: str = ""
    solution: str = ""
    outcome: str = ""
    banner: str = ""
    mock_cards: int = 0
    locked_hint: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"flows-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def practice(engine: str, server: RunningServer) -> Practice:
    seen = Practice()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        watched(page, seen.errors, expected=_asks_its_question)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _start(page, seen)
        _vim(page, seen, server)
        _hint(page, seen)
        _solution(page, seen)
        _done(page, seen)
        _mock(page, seen)
        browser.close()
    return seen


def _start(page: Any, seen: Practice) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.click(".practice-actions button.primary")
    page.fill(f"{SHEET} #start-timer", "25")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".attempt-head .flow-actions")
    seen.started = page.locator(".attempt-head").inner_text()


def _vim(page: Any, seen: Practice, server: RunningServer) -> None:
    page.wait_for_selector(EDITOR)
    page.click(TURN_VIM_ON)
    page.wait_for_selector(f"{EDITOR} .cm-scroller.cm-vimMode")
    workspace = Path(server.environment["CSTUDY_WORKSPACE"])
    seen.vim_preference = json.loads((workspace / PREFERENCES).read_text())["vim"]
    page.reload()
    seen.vim_after_reload = page.wait_for_selector(f"{EDITOR} .cm-scroller.cm-vimMode") is not None
    page.click(TURN_VIM_OFF)
    page.wait_for_selector(f"{EDITOR} .cm-scroller:not(.cm-vimMode)")


def _hint(page: Any, seen: Practice) -> None:
    page.click(".flow-actions button:has-text('Hint')")
    seen.hint = page.locator(".hints .hint h3").first.text_content() or ""


def _solution(page: Any, seen: Practice) -> None:
    page.click(".flow-actions button:has-text('Solution')")
    page.click("dialog.sheet-wide[open] form button[type=submit]")
    question = page.wait_for_selector("dialog.sheet[open]:not(.sheet-wide) .question")
    seen.question = question.inner_text()
    page.click("dialog.sheet[open]:not(.sheet-wide) button.primary")
    seen.solution = page.locator(".solution-reference").inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector("dialog.sheet-wide", state="detached")


def _done(page: Any, seen: Practice) -> None:
    page.click(".flow-actions button:has-text('Done')")
    page.click(f"{SHEET} label[for=done-gave-up]")
    page.click(f"{SHEET} button[type=submit]")
    seen.outcome = page.locator(f"{SHEET} .outcome-lines").inner_text()
    # The server tells the page of the change a moment later; the attempt behind the dialog must not
    # read an attempt that is over, which the browser would log as a 409.
    page.wait_for_timeout(NOTICE_WAIT_MS)
    page.keyboard.press("Escape")


def _mock(page: Any, seen: Practice) -> None:
    page.click("a.tab[data-view=mock]")
    page.fill("#mock-count", "1")
    page.fill("#mock-minutes", "30")
    page.click(".mock-form button[type=submit]")
    page.wait_for_selector(".mock-card")
    seen.mock_cards = page.locator(".mock-card").count()
    seen.banner = page.locator(".mock-banner").inner_text()
    page.click(".mock-card a.button")
    hint = page.wait_for_selector(".flow-actions button:disabled", state="attached")
    seen.locked_hint = hint.get_attribute("title") or ""


def _asks_its_question(message: ConsoleLine) -> bool:
    """The browser logs every 409 answer, so also the `confirmation_required` of the solution,
    which the page answers by asking (docs/specs/web-ui.md#solutions)."""
    url = message.location.get("url", "")
    return CONFLICT in message.text and url.endswith(QUESTION_PATH)


def test_a_start_with_a_time_box_opens_the_attempt(practice):
    assert PROBLEM in practice.started
    assert "/ 25:00" in practice.started


def test_vim_keybindings_turn_on_and_are_stored(practice):
    assert practice.vim_preference is True


def test_vim_keybindings_survive_a_reload(practice):
    assert practice.vim_after_reload


def test_a_hint_shows_with_its_number(practice):
    assert practice.hint.startswith("hint 1 of ")


def test_revealing_the_solution_asks_the_clis_question(practice):
    assert practice.question == "Reveal the solution? The attempt will be graded as again."


def test_the_revealed_solution_shows_the_attempt_graded_again(practice):
    assert "is graded as again" in practice.solution


def test_done_shows_the_lines_cstudy_done_prints(practice):
    first, second = practice.outcome.splitlines()
    assert first.startswith(f"{PROBLEM} · python · failed · ")
    assert first.endswith(" · gave up · hints 1")
    assert second.startswith("next review  ")


def test_a_mock_starts_from_the_page(practice):
    assert practice.mock_cards == 1


def test_the_banner_counts_the_mock_down(practice):
    assert practice.banner.startswith("Mock interview · ")
    assert practice.banner.endswith(" left · hints and solutions locked")


def test_hint_is_locked_with_the_clis_message_in_a_mock_attempt(practice):
    assert practice.locked_hint.startswith("cstudy hint is locked during the mock interview (")


def test_the_page_logs_no_error_under_its_content_security_policy(practice):
    assert practice.errors == []
