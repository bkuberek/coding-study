"""The Vim switch while an editor is still loading, in a real browser (docs/specs/web-ui.md#editor),
in each engine of `tests/browsers.py`: an editor is in the page before its language has loaded,
and the switch pressed in between reaches it all the same, as it does an editor that is ready.

The page's code chunks are held from the moment the attempt opens, and let go as they are asked
for until the editor is in the page; the ones asked for after that, the file's language, stay held
while the switch is pressed.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
WAIT_MS = 60_000
CHUNKS = "**/chunks/*.js"
EDITOR_IN_PAGE = ".panel:not([hidden]) .cm-editor"
SWITCH_ON = "button.toggle:has-text('vim on')"
TURN_VIM_ON = "button.toggle:has-text('vim off')"
VIM_EDITOR = f"{EDITOR_IN_PAGE} .cm-scroller.cm-vimMode"
POLL_MS = 20


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    root = Path(mark_workspace(tmp_path_factory.mktemp(f"vim-toggle-{engine}") / "workspace"))
    subprocess.run(
        [sys.executable, "-m", "coding_study", "start", PROBLEM, "--no-open"],
        env=served_environment(root),
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    with running_server(root) as running:
        yield running


@pytest.fixture(scope="module")
def editor_has_vim(engine: str, server: RunningServer) -> bool:
    held: list[Any] = []
    holding = False

    def hold(route: Any) -> None:
        if holding:
            held.append(route)
        else:
            route.continue_()

    def release() -> None:
        while held:
            held.pop().continue_()

    problems: list[str] = []
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), problems)
        page.set_default_timeout(WAIT_MS)
        page.route(CHUNKS, hold)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        holding = True
        page.evaluate("location.hash = '#/attempts/1'")
        while page.locator(EDITOR_IN_PAGE).count() == 0:
            release()
            page.wait_for_timeout(POLL_MS)
        page.click(TURN_VIM_ON)
        page.wait_for_selector(SWITCH_ON)
        holding = False
        release()
        try:
            page.wait_for_selector(VIM_EDITOR, timeout=WAIT_MS / 6)
            found = True
        except sync_api.TimeoutError:
            found = False
        browser.close()
    return found


def test_the_switch_pressed_while_an_editor_loads_turns_vim_on_in_it(editor_has_vim):
    assert editor_has_vim
