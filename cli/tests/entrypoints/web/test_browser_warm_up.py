"""The warm-up in a real browser, in each engine of `tests/browsers.py`
(docs/specs/web-ui.md#warm-up): `cstudy serve` starts the default language's server, the scripted
fake basedpyright, before the page opens; the Python practice file's session takes it over, so the
status bar says it is ready with no second server started, and the server was initialized once.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.browsers import launched, watched
from tests.intelligence_lab import Lab, intelligence_lab, open_attempt, wait_for_status
from tests.scripted_runs import eventually

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
READY = "python · basedpyright · ready"
SCRIPT = ({"reply": "initialize", "result": {"capabilities": {"hoverProvider": True}}},)


@dataclass
class Seen:
    servers_before_the_page: int = 0
    status: str = ""
    servers_after: int = 0
    initializations: int = 0
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def lab(
    engine: str, practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Lab]:
    base = tmp_path_factory.mktemp(f"warm-up-{engine}")
    with intelligence_lab(practice_workspace, base, SCRIPT, warm_up=True) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, lab: Lab) -> Seen:
    found = Seen(servers_before_the_page=len(eventually(lab.script.calls, bool)))
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(lab.server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        open_attempt(page, lab)
        found.status = wait_for_status(page, READY)
        found.servers_after = len(lab.script.calls())
        found.initializations = lab.script.methods().count("initialize")
        browser.close()
    return found


def test_the_default_languages_server_runs_before_the_page_opens(seen):
    assert seen.servers_before_the_page == 1


def test_the_practice_files_session_is_ready_on_it(seen):
    assert seen.status.startswith(READY)


def test_no_second_server_starts(seen):
    assert seen.servers_after == 1


def test_the_server_is_initialized_once(seen):
    assert seen.initializations == 1


def test_there_is_no_console_error(seen):
    assert seen.errors == []
