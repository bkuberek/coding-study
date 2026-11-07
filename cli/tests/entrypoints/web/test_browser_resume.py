"""The Problems view's Next card resumes first, in a real browser
(docs/specs/web-ui.md#problems-view), in each engine of `tests/browsers.py`: with attempts in
progress the card offers the one used most recently, links to it, and offers the others to pick up
instead; once those are aborted it suggests a new problem again, as `cstudy next` does.

The workspace is a bare one over the catalog of the checkout; the attempts are rows of its progress
database, as `cstudy start` leaves them, and the aborts are `cstudy abort` itself. Playwright and
its engines are set up as `tests/browsers.py` says; without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.domain.attempts import AttemptMode, NewAttempt
from coding_study.domain.config import DEFAULT_PROGRESS_DB
from coding_study.domain.problem import Language
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
OLDER = "two-sum"
NEWER = "valid-anagram"
CARD = ".next-card:not([aria-busy])"
PICK = f"{CARD} .pick"
PICK_LINK = f"{CARD} .next-slug"
ALSO_LINKS = f"{CARD} .next-also a"


@dataclass
class Card:
    """What the Next card said at one point."""

    pick: str = ""
    link: str = ""
    reason: str = ""
    start: str = ""
    also: list[str] = field(default_factory=list[str])
    also_links: list[str] = field(default_factory=list[str])
    text: str = ""


@dataclass
class Visit:
    before: Card = field(default_factory=Card)
    two_open: Card = field(default_factory=Card)
    one_open: Card = field(default_factory=Card)
    none_open: Card = field(default_factory=Card)
    attempts: dict[str, int] = field(default_factory=dict[str, int])
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return mark_workspace(tmp_path_factory.mktemp(f"resume-{engine}") / "workspace")


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, server: RunningServer, workspace: Path) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.problems)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        seen.before = _card(page)
        _open_attempts(workspace, seen)
        page.reload()
        seen.two_open = _card(page)
        _abort(workspace, NEWER)
        page.reload()
        seen.one_open = _card(page)
        _abort(workspace, OLDER)
        page.reload()
        seen.none_open = _card(page)
        browser.close()
    return seen


def _card(page: Any) -> Card:
    page.wait_for_selector(PICK)
    card = page.locator(CARD)
    return Card(
        pick=page.locator(PICK).text_content() or "",
        link=page.locator(PICK_LINK).get_attribute("href") or "",
        reason=card.locator(".next-reason").inner_text(),
        start=card.locator(".next-start .cmd").inner_text(),
        also=page.locator(ALSO_LINKS).all_inner_texts(),
        also_links=[link.get_attribute("href") or "" for link in page.locator(ALSO_LINKS).all()],
        text=card.inner_text(),
    )


def _open_attempts(workspace: Path, seen: Visit) -> None:
    """The older attempt started first; the newer one a minute later, so it was used last."""
    store = SqliteProgressStore(workspace / DEFAULT_PROGRESS_DB)
    started = datetime.now(UTC) - timedelta(hours=1)
    for slug, shift in ((OLDER, 0), (NEWER, 60)):
        attempt = NewAttempt(
            slug, Language.PYTHON, AttemptMode.NEW, started + timedelta(seconds=shift)
        )
        seen.attempts[slug] = store.add_attempt(attempt).id


def _abort(workspace: Path, slug: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", "abort", slug, "--yes"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )


def test_with_nothing_open_the_card_suggests_a_new_problem(visit):
    assert visit.before.pick == "new"


def test_with_attempts_open_the_card_resumes_the_one_used_most_recently(visit):
    assert visit.two_open.pick == "resume"
    assert visit.two_open.link == f"#/attempts/{visit.attempts[NEWER]}"


def test_the_resume_names_its_attempt_and_when_it_was_last_used(visit):
    assert visit.two_open.reason.startswith(
        f"attempt {visit.attempts[NEWER]} in python, last used "
    )


def test_the_resume_shows_the_command_that_cstudy_next_matches(visit):
    assert visit.two_open.start == f"cstudy start {NEWER} --lang python"
    assert "same as cstudy next" in visit.two_open.text


def test_with_several_open_the_card_offers_the_others_to_pick_up(visit):
    assert visit.two_open.also == [f"↻ {OLDER} (python)"]
    assert visit.two_open.also_links == [f"#/attempts/{visit.attempts[OLDER]}"]


def test_with_one_open_the_card_offers_no_other(visit):
    assert (visit.one_open.pick, visit.one_open.also) == ("resume", [])


def test_once_the_newest_is_aborted_the_older_attempt_is_resumed(visit):
    assert visit.one_open.link == f"#/attempts/{visit.attempts[OLDER]}"


def test_once_none_is_open_the_card_suggests_a_new_problem_again(visit):
    assert visit.none_open.pick == "new"
    assert visit.none_open.also == []


def test_the_page_logs_no_problem(visit):
    assert visit.problems == []
