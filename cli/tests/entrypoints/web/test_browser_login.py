"""`cstudy serve --open` in a real browser (docs/specs/web-ui.md#security), in each engine of
`tests/browsers.py`: the browser opens the redirect file the server wrote, follows it to the
printed URL, and shows the page logged in, without the token in the address bar.

The redirect file is a `file:` page, so the login is a navigation that another site started:
after it, a browser withholds a `SameSite=Strict` cookie from a redirect the login answers with,
and only a navigation the server's own page starts sends it. The server's `--open` would open
the default browser, so `BROWSER=true` makes it open nothing and the test opens the file instead.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.browsers import launched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
OPENS_NOTHING = {"BROWSER": "true"}
LANDED = "table.problems tbody tr, body > p"
"""The problem list once logged in, or the paragraph of the page that says there is no session."""


@dataclass
class Landing:
    logged_in: bool = False
    address: str = ""


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"open-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace, "--open", variables=OPENS_NOTHING) as running:
        yield running


@pytest.fixture(scope="module")
def landing(engine: str, server: RunningServer, workspace: Path) -> Landing:
    redirect = workspace / ".cs" / "serve" / f"{server.port}.html"
    found = Landing()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page()
        page.set_default_timeout(WAIT_MS)
        page.goto(redirect.as_uri())
        page.wait_for_url(f"{server.address}/")
        found.logged_in = page.wait_for_selector(LANDED).evaluate("node => node.tagName") == "TR"
        found.address = page.url
        browser.close()
    return found


def test_the_redirect_file_opens_the_page_logged_in(landing):
    assert landing.logged_in


def test_the_address_bar_keeps_no_token(landing, server):
    assert landing.address == f"{server.address}/"
