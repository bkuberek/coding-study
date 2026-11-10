"""What a service project depends on, in a real browser
(docs/specs/service-projects.md#where-it-shows), in each engine of `tests/browsers.py`, against a
real `cstudy serve` on the fake Docker of `tests/scripted_sandbox.py`: the Problems view marks the
project `needs docker`, the Problem view and the Start dialog list what it needs before anything
starts, and with Docker missing the Problem view, the Start dialog and the Attempt view say so in
the CLI's words, Start cannot start, and a run ends with the same message. No console error and no
Content Security Policy violation.

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
from coding_study.domain.docker_engine import EngineStatus
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.scripted_sandbox import sandbox_variables, write_script
from tests.serve_page import opened_page
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

SLUG = "coworking-availability-typescript"
ROW = f"table.problems tbody tr:has(a.problem-link[href='#/problems/{SLUG}'])"
NEEDS = ".problem-side .needs .needs-list"
DIALOG = "dialog.sheet[open]"
DIALOG_NEEDS = f"{DIALOG} .needs-list"
DIALOG_SUBMIT = f"{DIALOG} button[type=submit]"
DOCKER_STATE = ".results .docker-state"
RUN = ".run-toolbar .run-button.primary"
SUMMARY = ".results .result-summary-text"
INSTALL_PAGE = "docs.docker.com"
WAIT_MS = 60_000


@dataclass
class Seen:
    marker: str = ""
    needs: str = ""
    dialog_needs: str = ""
    dialog_start_enabled: bool = False
    missing_needs: str = ""
    missing_dialog: str = ""
    missing_start_enabled: bool = True
    docker_state: str = ""
    run_summary: str = ""
    errors: list[str] = field(default_factory=list[str])


@dataclass
class Lab:
    workspace: Path
    sandbox: Path
    variables: dict[str, str]


@pytest.fixture(scope="module")
def lab(engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Lab:
    base = tmp_path_factory.mktemp(f"service-needs-{engine}")
    root = workspace_like(practice_workspace, base / "workspace")
    environment = load_environment(root, served_environment(root), root.parent)
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    sandbox = base / "sandbox"
    return Lab(root, sandbox, sandbox_variables(sandbox, {}))


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
        found.marker = page.locator(f"{ROW} .needs-tag").inner_text()
        page.click(f"{ROW} a.problem-link")
        found.needs = page.locator(NEEDS).inner_text()
        found.dialog_needs, found.dialog_start_enabled = _start_dialog(page)
        write_script(lab.sandbox, {"engine": EngineStatus.NOT_INSTALLED.value})
        page.reload()
        found.missing_needs = page.locator(NEEDS).inner_text()
        found.missing_dialog, found.missing_start_enabled = _start_dialog(page)
        page.evaluate("id => { location.hash = `#/attempts/${id}` }", attempt_id)
        found.docker_state = page.locator(DOCKER_STATE).inner_text()
        page.click(RUN)
        found.run_summary = page.locator(SUMMARY).inner_text()
        browser.close()
    return found


def _start_dialog(page: Any) -> tuple[str, bool]:
    """What the Start dialog lists once it read the needs, and whether it can start."""
    page.click(".practice-actions button.primary")
    text = page.locator(DIALOG_NEEDS).inner_text()
    page.wait_for_selector(f"{DIALOG} .needs-note")
    enabled = page.is_enabled(DIALOG_SUBMIT)
    page.keyboard.press("Escape")
    page.wait_for_selector(DIALOG, state="detached")
    return text, enabled


def test_the_problems_view_marks_the_project_needs_docker(seen):
    assert seen.marker == "needs docker"


def test_the_problem_view_lists_what_the_project_needs(seen):
    for label in ("docker", "language", "packages", "mocks", "total"):
        assert label in seen.needs


def test_the_problem_view_names_sizes_and_memory(seen):
    assert "MB download" in seen.needs
    assert "MB memory" in seen.needs


def test_the_start_dialog_lists_the_needs_before_starting(seen):
    assert "running engine and compose v2" in seen.dialog_needs


def test_the_start_dialog_can_start_when_every_need_is_met(seen):
    assert seen.dialog_start_enabled is True


def test_docker_missing_is_said_in_the_problem_view(seen):
    assert INSTALL_PAGE in seen.missing_needs


def test_docker_missing_is_said_in_the_start_dialog(seen):
    assert INSTALL_PAGE in seen.missing_dialog


def test_docker_missing_keeps_the_start_dialog_from_starting(seen):
    assert seen.missing_start_enabled is False


def test_docker_missing_is_said_in_the_attempt_view_before_any_run(seen):
    assert INSTALL_PAGE in seen.docker_state


def test_docker_missing_ends_a_run_with_the_clis_message(seen):
    assert INSTALL_PAGE in seen.run_summary


def test_the_advice_runs_no_sudo(seen):
    assert "sudo" not in seen.docker_state


def test_no_console_error_or_csp_violation(seen):
    assert seen.errors == []
