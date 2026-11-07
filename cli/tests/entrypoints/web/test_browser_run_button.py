"""Run and Cancel are one button on the Attempt view (docs/specs/web-ui.md#attempt-view), in each
engine of `tests/browsers.py`: while idle the toolbar has Run tests and no Cancel, disabled or
not; while a run is active the button that started it reads Cancel in the same place, keeps the
keyboard focus, and a screen reader is told; Cancel asks the question Escape asks before it stops
the run; and the button reads Run again once the run ended. A project's Submit is treated the same.

The workspace shares the session's practice workspace's toolchains, so the project's suite runs
with the real pytest, held by a test that sleeps. Playwright and its engines are set up as
`tests/browsers.py` says; without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROJECT = "bank-project-python"
SLOW_TEST = "tests/test_slow.py"
SLOW_TEST_TEXT = "import time\n\n\ndef test_slow():\n    time.sleep(120)\n"
WAIT_MS = 60_000
RUN_WAIT_MS = 240_000
TOOLBAR = ".run-toolbar"
RUN = f"{TOOLBAR} .run-button.primary"
SUBMIT = f"{TOOLBAR} .run-button:not(.primary)"
CANCEL = f"{TOOLBAR} .is-cancel"
OPTIONS = f"{TOOLBAR} button:has-text('Run options')"
DIALOG = "dialog.sheet[open]"
ANNOUNCER = ".sr-only[role=status]"
CONFLICT = "status of 409"
CANCELLED = ("interrupted", "cstudy exited 130")
"""How the summary reads once the child stopped on the signal, with its own `run_end` or without."""


@dataclass
class Moment:
    """The toolbar at one point: what a screen reader finds in it, and where the focus is."""

    buttons: str = ""
    cancel_buttons: int = 0
    focused: str = ""
    announced: str = ""
    options_left: float = 0.0


@dataclass
class Pass:
    """One run, from its button through its cancel."""

    idle: Moment = field(default_factory=Moment)
    running: Moment = field(default_factory=Moment)
    asked: str = ""
    kept: Moment = field(default_factory=Moment)
    ended: Moment = field(default_factory=Moment)
    summary: str = ""


@dataclass
class Visit:
    run: Pass = field(default_factory=Pass)
    submit: Pass = field(default_factory=Pass)
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    root = workspace_like(
        practice_workspace, tmp_path_factory.mktemp(f"run-button-{engine}") / "workspace"
    )
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
def visit(engine: str, server: RunningServer, workspace: Path) -> Visit:
    seen = Visit()
    slow_test = workspace / "projects" / PROJECT / SLOW_TEST
    slow_test.write_text(SLOW_TEST_TEXT)
    try:
        with sync_api.sync_playwright() as playwright:
            browser = launched(playwright, engine)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            watched(page, seen.errors, expected=_is_the_question_of_an_ended_run)
            page.set_default_timeout(WAIT_MS)
            page.goto(server.login_url)
            page.click(f"a.slug[href='#/problems/{PROJECT}']")
            page.click("a.button.primary")
            page.wait_for_selector(RUN)
            seen.run = _pass(page, RUN)
            seen.submit = _pass(page, SUBMIT)
            browser.close()
    finally:
        slow_test.unlink(missing_ok=True)
    return seen


def _pass(page: Any, button: str) -> Pass:
    """Clicks `button`, which starts a run, then cancels it through its question."""
    found = Pass(idle=_moment(page, button))
    page.click(button)
    page.wait_for_selector(f"{button}.is-cancel", timeout=RUN_WAIT_MS)
    sync_api.expect(page.locator(ANNOUNCER)).to_contain_text("now cancels it")
    found.running = _moment(page, button)
    page.click(CANCEL)
    found.asked = page.wait_for_selector(f"{DIALOG} .question").inner_text()
    page.click(f"{DIALOG} button:has-text('Keep it running')")
    page.wait_for_selector(DIALOG, state="detached")
    found.kept = _moment(page, button)
    page.click(CANCEL)
    page.click(f"{DIALOG} button.danger")
    page.wait_for_selector(f"{button}:not(.is-cancel)", timeout=RUN_WAIT_MS)
    found.summary = page.locator(".result-summary-text").inner_text()
    found.ended = _moment(page, button)
    return found


def _moment(page: Any, button: str) -> Moment:
    has_the_focus = page.evaluate(
        "selector => document.activeElement === document.querySelector(selector)", button
    )
    return Moment(
        buttons=page.locator(TOOLBAR).aria_snapshot(),
        cancel_buttons=page.locator(CANCEL).count(),
        focused="the button" if has_the_focus else "elsewhere",
        announced=page.locator(ANNOUNCER).text_content() or "",
        options_left=page.locator(OPTIONS).bounding_box()["x"],
    )


def _is_the_question_of_an_ended_run(message: Any) -> bool:
    """The browser logs a 409, such as the cancel of a run that just ended."""
    return CONFLICT in message.text and message.location.get("url", "").endswith("/cancel")


def test_idle_the_toolbar_has_run_tests_and_no_cancel(visit):
    assert 'button "Run tests' in visit.run.idle.buttons
    assert (visit.run.idle.cancel_buttons, "Cancel" in visit.run.idle.buttons) == (0, False)


def test_a_running_run_turns_the_run_button_into_cancel_in_its_place(visit):
    running = visit.run.running
    assert (running.cancel_buttons, 'button "Cancel"' in running.buttons) == (1, True)
    assert 'button "Run tests' not in running.buttons


def test_the_run_button_keeps_the_focus_when_it_turns_into_cancel(visit):
    assert (visit.run.running.focused, visit.run.kept.focused) == ("the button", "the button")


def test_a_screen_reader_is_told_the_button_now_cancels(visit):
    assert visit.run.running.announced == (
        f"running cstudy test {PROJECT}; the same button now cancels it"
    )


def test_cancel_asks_the_question_escape_asks(visit):
    assert visit.run.asked == "cstudy stops it as Ctrl-C does and records nothing."


def test_keeping_the_run_running_leaves_the_button_cancel(visit):
    assert visit.run.kept.cancel_buttons == 1


def test_the_cancelled_run_ends_with_the_signal(visit):
    assert visit.run.summary in CANCELLED


def test_once_the_run_ended_the_button_reads_run_tests_again_with_the_focus(visit):
    ended = visit.run.ended
    assert 'button "Run tests' in ended.buttons
    assert (ended.cancel_buttons, ended.focused) == (0, "the button")


def test_submit_turns_into_cancel_in_its_own_place(visit):
    running = visit.submit.running
    assert (running.cancel_buttons, 'button "Cancel"' in running.buttons) == (1, True)
    assert 'button "Submit' not in running.buttons


def test_the_run_button_waits_disabled_while_submit_runs(visit):
    assert 'button "Run tests' in visit.submit.running.buttons
    assert "[disabled]" in visit.submit.running.buttons


def test_a_cancelled_submit_ends_with_the_signal_and_reads_submit_again(visit):
    assert visit.submit.summary in CANCELLED
    assert 'button "Submit' in visit.submit.ended.buttons


def test_the_page_logs_no_error(visit):
    assert visit.errors == []


def test_the_buttons_after_the_swap_do_not_move_when_a_run_starts_or_ends(visit):
    for found in (visit.run, visit.submit):
        assert {
            found.idle.options_left,
            found.running.options_left,
            found.ended.options_left,
        } == {found.idle.options_left}
