"""The Settings view's code intelligence and autocomplete checkboxes in a real browser
(docs/specs/web-ui.md#settings-view), in each engine of `tests/browsers.py`: both start off,
Autocomplete is disabled with its note while Code intelligence is off, turning Code intelligence
on enables it, before any Save, a stored Autocomplete survives Code intelligence going off and on,
and a Save stores both in `.cs/serve/preferences.json`.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, save_preferences
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
PREFERENCES = Path(".cs") / "serve" / "preferences.json"
CODE_INTELLIGENCE = "#pref-code_intelligence"
AUTOCOMPLETE = "#pref-autocomplete"
NOTE = "#pref-autocomplete-note"
NOTE_TEXT = "Turn on code intelligence first"


@dataclass
class Gate:
    """What the Settings view showed at each step of turning the two checkboxes on and off."""

    default_checked: tuple[bool, bool] = (True, True)
    off_disabled: bool = False
    off_note: str = ""
    off_described_by: str = ""
    on_disabled: bool = True
    on_note_visible: bool = True
    autocomplete_stored: object = None
    off_again_checked: bool = False
    off_again_disabled: bool = False
    after_reload: tuple[bool, bool, bool] = (False, False, True)
    stored: dict[str, object] | None = None


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"settings-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def gate(engine: str, server: RunningServer) -> Gate:
    seen = Gate()
    workspace = Path(server.environment["CSTUDY_WORKSPACE"])
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(CODE_INTELLIGENCE)
        _defaults(page, seen)
        _turn_on(page, seen, workspace)
        _turn_off_again(page, seen)
        _reload(page, seen, workspace)
        browser.close()
    return seen


def _stored(workspace: Path) -> dict[str, object]:
    return json.loads((workspace / PREFERENCES).read_text())


def _defaults(page: Any, seen: Gate) -> None:
    seen.default_checked = (page.is_checked(CODE_INTELLIGENCE), page.is_checked(AUTOCOMPLETE))
    seen.off_disabled = page.is_disabled(AUTOCOMPLETE)
    seen.off_note = page.locator(NOTE).inner_text()
    description = page.get_attribute(AUTOCOMPLETE, "aria-describedby")
    seen.off_described_by = description or ""


def _turn_on(page: Any, seen: Gate, workspace: Path) -> None:
    page.check(CODE_INTELLIGENCE)
    seen.on_disabled = page.is_disabled(AUTOCOMPLETE)
    seen.on_note_visible = page.is_visible(NOTE)
    page.check(AUTOCOMPLETE)
    save_preferences(page)
    seen.autocomplete_stored = _stored(workspace)["autocomplete"]


def _turn_off_again(page: Any, seen: Gate) -> None:
    page.uncheck(CODE_INTELLIGENCE)
    save_preferences(page)
    seen.off_again_checked = page.is_checked(AUTOCOMPLETE)
    seen.off_again_disabled = page.is_disabled(AUTOCOMPLETE)


def _reload(page: Any, seen: Gate, workspace: Path) -> None:
    seen.stored = _stored(workspace)
    page.reload()
    page.wait_for_selector(CODE_INTELLIGENCE)
    seen.after_reload = (
        page.is_checked(CODE_INTELLIGENCE),
        page.is_checked(AUTOCOMPLETE),
        page.is_disabled(AUTOCOMPLETE),
    )


def test_both_start_off(gate):
    assert gate.default_checked == (False, False)


def test_autocomplete_is_disabled_while_code_intelligence_is_off(gate):
    assert gate.off_disabled


def test_the_disabled_autocomplete_says_why(gate):
    assert gate.off_note == NOTE_TEXT


def test_the_note_is_tied_to_the_checkbox(gate):
    assert "pref-autocomplete-note" in gate.off_described_by.split()


def test_code_intelligence_enables_autocomplete(gate):
    assert (gate.on_disabled, gate.on_note_visible) == (False, False)


def test_autocomplete_is_stored(gate):
    assert gate.autocomplete_stored is True


def test_turning_code_intelligence_off_keeps_the_stored_autocomplete(gate):
    assert (gate.off_again_checked, gate.off_again_disabled) == (True, True)


def test_the_stored_file_keeps_autocomplete_while_code_intelligence_is_off(gate):
    assert gate.stored is not None
    assert (gate.stored["code_intelligence"], gate.stored["autocomplete"]) == (False, True)


def test_a_reload_shows_what_was_stored(gate):
    assert gate.after_reload == (False, True, True)
