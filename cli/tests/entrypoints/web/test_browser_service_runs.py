"""Runs of a service project in a real browser (docs/specs/web-ui.md#attempt-view), in each engine
of `tests/browsers.py`, against a real `cstudy serve` whose `cstudy` children run on the fake
Docker of `tests/scripted_sandbox.py`: Run tests streams the stack's stages, `commands.test` and the
visible cases into the results panel; Submit grades; Cancel stops a run whose test is under way and
the stack comes down. The run options offer only a level, and no native flag shows anywhere. No
console error and no Content Security Policy violation.

The attempt is started in this process, since `cstudy start` would install the project in Docker.
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
from tests.scripted_sandbox import logged_calls, sandbox_variables, write_script
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SLUG = "coworking-availability-typescript"
TOOLBAR = ".run-toolbar"
RUN = f"{TOOLBAR} .run-button.primary"
SUBMIT = f"{TOOLBAR} .run-button:not(.primary)"
CANCEL = f"{TOOLBAR} .is-cancel"
OPTIONS = f"{TOOLBAR} button:has-text('Run options')"
BENCH = f"{TOOLBAR} button:has-text('Bench')"
DIALOG = "dialog.sheet[open]"
PANEL = ".results"
STACK = f"{PANEL} .result-stack"
SUMMARY = f"{PANEL} .result-summary-text"
RUNNING_TEST = f"{PANEL} .result-running:has-text('commands.test')"
WAIT_MS = 60_000
QUICK = {"start_s": 0.2, "test_s": 0.0, "test_lines": ["ok 1 - rooms"]}
SLOW_TEST = {**QUICK, "test_s": 60.0}


@dataclass
class Ran:
    """One run as the results panel showed it once it ended."""

    stack: str = ""
    rows: list[str] = field(default_factory=list[str])
    summary: str = ""
    panel: str = ""


@dataclass
class Seen:
    bench_shown: bool = True
    options: str = ""
    run_title: str = ""
    test: Ran = field(default_factory=Ran)
    submit: Ran = field(default_factory=Ran)
    cancelled: Ran = field(default_factory=Ran)
    stack_while_running: str = ""
    calls: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@dataclass
class Lab:
    workspace: Path
    sandbox: Path
    variables: dict[str, str]


@pytest.fixture(scope="module")
def lab(engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Lab:
    base = tmp_path_factory.mktemp(f"service-runs-{engine}")
    root = workspace_like(practice_workspace, base / "workspace")
    environment = load_environment(root, served_environment(root), root.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    (root / "projects" / SLUG / "node_modules").mkdir()
    sandbox = base / "sandbox"
    return Lab(root, sandbox, sandbox_variables(sandbox, QUICK))


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
        page.wait_for_selector(RUN)
        found.bench_shown = page.is_visible(BENCH)
        found.run_title = page.get_attribute(RUN, "title") or ""
        page.click(OPTIONS)
        found.options = page.locator("#run-options").inner_text()
        page.click(OPTIONS)
        found.test = _ran(page, RUN)
        found.submit = _ran(page, SUBMIT)
        write_script(lab.sandbox, SLOW_TEST)
        found.cancelled, found.stack_while_running = _cancelled(page)
        browser.close()
    found.calls = logged_calls(lab.sandbox)
    return found


def _ran(page: Any, button: str) -> Ran:
    page.click(button)
    page.wait_for_selector(f"{button}.is-cancel")
    page.wait_for_selector(f"{button}:not(.is-cancel)")
    return _panel(page)


def _cancelled(page: Any) -> tuple[Ran, str]:
    """Starts a run whose `commands.test` takes a minute, and cancels it once the test runs."""
    page.click(RUN)
    page.wait_for_selector(RUNNING_TEST)
    stack = page.locator(STACK).inner_text()
    page.click(CANCEL)
    page.click(f"{DIALOG} button.danger")
    page.wait_for_selector(f"{RUN}:not(.is-cancel)")
    return _panel(page), stack


def _panel(page: Any) -> Ran:
    page.wait_for_selector(SUMMARY)
    rows = page.locator(f"{PANEL} .result-row").all_inner_texts()
    return Ran(
        stack=page.locator(STACK).inner_text(),
        rows=[" ".join(row.split()) for row in rows],
        summary=page.locator(SUMMARY).inner_text(),
        panel=page.locator(PANEL).inner_text(),
    )


def test_run_tests_names_the_command_with_no_flag(seen):
    assert seen.run_title.startswith(f"cstudy test {SLUG} (")


def test_the_run_options_offer_only_a_level(seen):
    assert "level" in seen.options.lower()
    assert "cases" not in seen.options.lower()
    assert "type check" not in seen.options.lower()


def test_the_run_options_name_the_submission_they_change(seen):
    assert f"cstudy submit {SLUG}" in seen.options


def test_bench_is_not_offered(seen):
    assert seen.bench_shown is False


def test_a_test_run_shows_the_stack_down_with_its_startup_apart(seen):
    assert seen.test.stack.startswith("stack")
    assert "down · it was ready after" in seen.test.stack
    assert "not counted" in seen.test.stack


def test_a_test_run_reports_commands_test_as_one_row(seen):
    assert any("PASS commands.test" in row for row in seen.test.rows)


def test_a_test_run_reports_each_visible_case_of_the_open_level(seen):
    cases = [row.split()[2] for row in seen.test.rows if "commands.test" not in row]
    assert cases == ["v1", "v2"]


def test_a_test_run_ends_with_its_summary(seen):
    assert "passed" in seen.test.summary


def test_a_submission_grades_with_the_stack(seen):
    assert "down" in seen.submit.stack
    assert "level 1" in seen.submit.panel


def test_the_stack_is_ready_while_the_test_runs(seen):
    assert "ready after" in seen.stack_while_running


def test_cancel_interrupts_the_run(seen):
    assert seen.cancelled.summary in ("interrupted", "cstudy exited 130")


def test_cancel_brings_the_stack_down(seen):
    assert "down" in seen.cancelled.stack
    last_start = max(i for i, call in enumerate(seen.calls) if call.startswith("start "))
    assert any(call.startswith("stop ") for call in seen.calls[last_start:])


def test_no_native_flag_shows(seen):
    assert "--" not in seen.test.panel


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []
