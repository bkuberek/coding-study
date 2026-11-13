"""The dev stack of a service project in a real browser (docs/specs/web-ui.md#dev-stack), in each
engine of `tests/browsers.py`, against a real `cstudy serve` whose `cstudy dev` runs on the fake
Docker of `tests/scripted_sandbox.py`: nothing starts until asked; Start dev stack brings it up and
shows where the app answers, its lines, and a picker per mock server of its visible scenarios only;
a pick switches the scenario live; Stop brings the stack down; and leaving the view stops a stack
the tab started. No console error and no Content Security Policy violation.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.scripted_runs import eventually
from tests.scripted_sandbox import logged_calls, sandbox_variables
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.waits import GENEROUS_WAIT_S
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SLUG = "coworking-availability-typescript"
PANEL = ".dev-stack"
BUTTON = f"{PANEL} .dev-button"
START_OFFERED = f"{BUTTON}:enabled:text-is('Start dev stack')"
STATE = f"{PANEL} .dev-state"
APP_LINK = f"{PANEL} .dev-app-link"
LOG = f"{PANEL} .dev-log"
ROOM_VENDOR = f"{PANEL} #dev-scenario-room-vendor"
ANNEX_VENDOR = f"{PANEL} #dev-scenario-annex-vendor"
APP_LINE = "listening on 8000"
WAIT_MS = int(GENEROUS_WAIT_S * 1000)


@dataclass
class Seen:
    idle_state: str = ""
    idle_button: str = ""
    ready_state: str = ""
    app_url: str = ""
    log: str = ""
    room_choices: list[str] = field(default_factory=list[str])
    annex_choices: list[str] = field(default_factory=list[str])
    picked: str = ""
    stopped_state: str = ""
    calls_after_stop: list[str] = field(default_factory=list[str])
    calls_after_leaving: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@dataclass
class Lab:
    workspace: Path
    sandbox: Path
    variables: dict[str, str]


@pytest.fixture(scope="module")
def lab(engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Lab:
    base = tmp_path_factory.mktemp(f"service-dev-{engine}")
    root = workspace_like(practice_workspace, base / "workspace")
    environment = load_environment(root, served_environment(root), root.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    (root / "projects" / SLUG / "node_modules").mkdir()
    sandbox = base / "sandbox"
    return Lab(root, sandbox, sandbox_variables(sandbox, {"app_lines": [APP_LINE]}))


@pytest.fixture(scope="module")
def server(lab: Lab) -> Iterator[RunningServer]:
    with running_server(lab.workspace, variables=lab.variables) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, lab: Lab) -> Seen:
    found = Seen()
    attempt_id = opened_page(server).attempts[SLUG]
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        watched(page, found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("id => { location.hash = `#/attempts/${id}` }", attempt_id)
        found.idle_state = page.locator(STATE).inner_text()
        found.idle_button = page.locator(BUTTON).inner_text()
        _start(page, found)
        _pick(page, found, lab.sandbox)
        page.click(BUTTON)
        page.wait_for_selector(f"{STATE}:has-text('down')")
        found.stopped_state = page.locator(STATE).inner_text()
        found.calls_after_stop = logged_calls(lab.sandbox)
        page.wait_for_selector(START_OFFERED)
        page.click(BUTTON)
        page.wait_for_selector(APP_LINK)
        page.evaluate("() => { location.hash = '#/' }")
        found.calls_after_leaving = eventually(lambda: logged_calls(lab.sandbox), _stopped_twice)
        browser.close()
    return found


def _start(page: Any, found: Seen) -> None:
    page.click(BUTTON)
    page.wait_for_selector(APP_LINK)
    page.wait_for_selector(f"{LOG}:has-text('{APP_LINE}')")
    found.ready_state = page.locator(STATE).inner_text()
    found.app_url = page.locator(APP_LINK).get_attribute("href") or ""
    found.log = page.locator(LOG).inner_text()
    found.room_choices = page.locator(f"{ROOM_VENDOR} option").all_inner_texts()
    found.annex_choices = page.locator(f"{ANNEX_VENDOR} option").all_inner_texts()


def _pick(page: Any, found: Seen, sandbox: Path) -> None:
    page.select_option(ROOM_VENDOR, "outage")
    eventually(lambda: logged_calls(sandbox), lambda calls: "scenario room-vendor outage" in calls)
    page.wait_for_function(f"document.querySelector('{ROOM_VENDOR}').value === 'outage'")
    found.picked = page.locator(ROOM_VENDOR).input_value()


def _stopped_twice(calls: list[str]) -> bool:
    return sum(call.startswith("stop cstudy-d-") for call in calls) >= 2


def test_nothing_starts_until_asked(seen):
    assert "not running" in seen.idle_state
    assert seen.idle_button == "Start dev stack"


def test_a_started_stack_is_ready_with_its_startup_apart(seen):
    assert "ready after" in seen.ready_state


def test_it_shows_where_the_app_answers_on_this_machine(seen):
    assert seen.app_url.startswith("http://127.0.0.1:")


def test_it_shows_what_the_app_prints(seen):
    assert APP_LINE in seen.log


def test_the_pickers_offer_visible_scenarios_only(seen):
    assert seen.room_choices == ["no scenario", "outage", "rate_limited", "slow"]
    assert seen.annex_choices == ["no scenario", "maintenance", "busy"]


def test_a_pick_switches_the_scenario_live(seen):
    assert seen.picked == "outage"


def test_stop_brings_the_stack_down(seen):
    assert "down" in seen.stopped_state
    assert any(call.startswith("stop cstudy-d-") for call in seen.calls_after_stop)


def test_leaving_the_view_stops_a_stack_the_tab_started(seen):
    assert _stopped_twice(seen.calls_after_leaving)


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []
