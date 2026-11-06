"""The Health view's Fix buttons in a real browser (docs/specs/web-ui.md#health-view), in each
engine of `tests/browsers.py`: a row whose fix is exactly `cstudy doctor --fix` has a Fix button
that names the row and starts the job the main Fix starts, with its question; while a job runs
every Fix button is disabled; any other hint stays text that does not look clickable, with its
link still a link.

The server is a real one over a bare workspace, but the page's `doctor` document and its job are
fakes that Playwright answers, so no tool is installed: the job's start, its question, its stream
and its end are what the page is shown. Playwright and its engines are set up as
`tests/browsers.py` says; without them the test is skipped.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
FIX = "cstudy doctor --fix"
QUESTION = "Run cstudy doctor --fix? It writes missing workspace files and runs uv sync."
JOB_ID = "0123456789abcdef"
JDK_GUIDE = "https://example.org/toolchains#jdk"
CHECKS = [
    {"name": "python", "status": "ok", "detail": "3.13.2", "fix": None},
    {"name": "python/.venv", "status": "fail", "detail": "missing", "fix": FIX},
    {"name": "code intelligence python", "status": "warn", "detail": "not installed", "fix": FIX},
    {
        "name": "java",
        "status": "fail",
        "detail": "java not found",
        "fix": f"install JDK 25: {JDK_GUIDE}",
    },
    {"name": "go", "status": "warn", "detail": "go not found", "fix": "install Go 1.25 or newer"},
    {"name": "venv", "status": "warn", "detail": "moved", "fix": f"rm -rf python/.venv && {FIX}"},
]
AFTER_THE_FIX = [
    {**check, "status": "ok", "fix": None} if check["name"] == "python/.venv" else check
    for check in CHECKS
]
TABLE = "table.checks"
ROW_BUTTONS = f"{TABLE} button"
MAIN_BUTTON = ".health-fix button"
HINTS = f"{TABLE} .fix-hint"
DIALOG = "dialog[open]"
RUN = f"{DIALOG} button:has-text('Run')"
CANCEL = f"{DIALOG} button:has-text('Cancel')"
CONFLICT = "status of 409"
QUESTION_PATH = "/api/v1/jobs"
JOB = ".health > .job"
JOB_STATE = f"{JOB} .job-state"
PAUSED_FOR_RECONNECT_MS = 50


@dataclass
class Fake:
    """What the page asked the fake server for, and whether its job has ended."""

    posts: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    rechecks: int = 0
    ended: bool = False


@dataclass
class Visit:
    summary: str = ""
    names: list[str] = field(default_factory=list[str])
    labels: list[str] = field(default_factory=list[str])
    rows_with_a_button: list[str] = field(default_factory=list[str])
    hints: list[str] = field(default_factory=list[str])
    hint_links: list[str] = field(default_factory=list[str])
    hint_looks_clickable: list[bool] = field(default_factory=list[bool])
    question: str = ""
    backdrop_covers_the_bar: bool = False
    posts_after_a_no: int = 0
    disabled_after_a_no: list[bool] = field(default_factory=list[bool])
    posts_after_a_yes: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    job_title: str = ""
    disabled_while_running: list[bool] = field(default_factory=list[bool])
    state_at_the_end: str = ""
    disabled_after_the_job: list[bool] = field(default_factory=list[bool])
    rows_after_the_job: list[str] = field(default_factory=list[str])
    rechecks: int = 0
    problems: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"health-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, server: RunningServer) -> Visit:
    seen, fake = Visit(), Fake()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(
            browser.new_page(viewport={"width": 1440, "height": 900}),
            seen.problems,
            expected=_asks_its_question,
        )
        page.set_default_timeout(WAIT_MS)
        _answer_as_a_fake(page, fake)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("location.hash = '#/health'")
        page.wait_for_selector(ROW_BUTTONS)
        _read_the_rows(page, seen)
        _answer_the_question_no(page, seen, fake)
        _answer_the_question_yes(page, seen, fake)
        _watch_the_job_end(page, seen, fake)
        seen.rechecks = fake.rechecks
        browser.close()
    return seen


def _asks_its_question(message: Any) -> bool:
    """The browser logs every 409 answer, so also the `confirmation_required` of the job, which
    the page answers by asking (docs/specs/web-ui.md#jobs)."""
    return CONFLICT in message.text and message.location.get("url", "").endswith(QUESTION_PATH)


def _answer_as_a_fake(page: Any, fake: Fake) -> None:
    """Answers the page's `doctor` document and the job it starts, its question and its stream."""

    def doctor(route: Any) -> None:
        fake.rechecks += 1
        checks = AFTER_THE_FIX if fake.ended else CHECKS
        route.fulfill(json={"workspace": "/w", "passed": False, "checks": checks})

    def jobs(route: Any) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        body = route.request.post_data_json
        fake.posts.append(body)
        if body.get("confirm"):
            route.fulfill(status=202, json={"id": JOB_ID})
        else:
            error = {"code": "confirmation_required", "message": QUESTION}
            route.fulfill(status=409, json={"error": error})

    def events(route: Any) -> None:
        line = {"stream": "stdout", "text": "ok    workspace"}
        body = f"retry: {PAUSED_FOR_RECONNECT_MS}\nevent: line\ndata: {json.dumps(line)}\n\n"
        if fake.ended:
            closed = {"exit_code": 0, "signal": None, "stderr": []}
            body += f"event: closed\ndata: {json.dumps(closed)}\n\n"
        route.fulfill(content_type="text/event-stream", body=body)

    page.route("**/api/v1/doctor", doctor)
    page.route("**/api/v1/jobs", jobs)
    page.route(f"**/api/v1/jobs/{JOB_ID}/events", events)


def _read_the_rows(page: Any, seen: Visit) -> None:
    seen.summary = page.locator(".health-fix .quiet").inner_text().strip()
    buttons = page.locator(ROW_BUTTONS)
    seen.names = buttons.evaluate_all("buttons => buttons.map(button => button.textContent)")
    seen.labels = buttons.evaluate_all(
        "buttons => buttons.map(button => button.getAttribute('aria-label'))"
    )
    seen.rows_with_a_button = page.locator(
        f"{TABLE} tbody tr:has(button) .check-name"
    ).all_inner_texts()
    seen.hints = page.locator(HINTS).all_inner_texts()
    seen.hint_links = page.locator(f"{HINTS} a[target=_blank]").evaluate_all(
        "links => links.map(link => link.href)"
    )
    seen.hint_looks_clickable = page.locator(HINTS).evaluate_all(
        """hints => hints.map((hint) => {
          const style = getComputedStyle(hint);
          return style.backgroundColor !== 'rgba(0, 0, 0, 0)' || style.borderTopWidth !== '0px';
        })"""
    )


def _all_fix_buttons_disabled(page: Any) -> list[bool]:
    return page.locator(f"{ROW_BUTTONS}, {MAIN_BUTTON}").evaluate_all(
        "buttons => buttons.map(button => button.disabled)"
    )


def _answer_the_question_no(page: Any, seen: Visit, fake: Fake) -> None:
    page.click(f"{ROW_BUTTONS} >> nth=0")
    page.wait_for_selector(DIALOG)
    seen.question = page.locator(f"{DIALOG} p").first.inner_text()
    seen.backdrop_covers_the_bar = page.evaluate(
        "document.elementFromPoint(window.innerWidth / 2, 10)?.tagName === 'DIALOG'"
    )
    page.click(CANCEL)
    page.wait_for_selector(DIALOG, state="detached")
    seen.posts_after_a_no = len(fake.posts)
    seen.disabled_after_a_no = _all_fix_buttons_disabled(page)


def _answer_the_question_yes(page: Any, seen: Visit, fake: Fake) -> None:
    page.click(f"{ROW_BUTTONS} >> nth=1")
    page.wait_for_selector(DIALOG)
    page.click(RUN)
    page.wait_for_selector(f"{JOB_STATE} .badge:has-text('running')")
    seen.posts_after_a_yes = list(fake.posts)
    seen.job_title = page.locator(f"{JOB} .job-title").inner_text()
    seen.disabled_while_running = _all_fix_buttons_disabled(page)


def _watch_the_job_end(page: Any, seen: Visit, fake: Fake) -> None:
    fake.ended = True
    page.wait_for_selector(f"{JOB_STATE} .badge:has-text('exit 0')")
    sync_api.expect(page.locator(ROW_BUTTONS)).to_have_count(1)
    seen.state_at_the_end = page.locator(JOB_STATE).inner_text()
    seen.disabled_after_the_job = _all_fix_buttons_disabled(page)
    seen.rows_after_the_job = page.locator(
        f"{TABLE} tbody tr:has(button) .check-name"
    ).all_inner_texts()


def test_the_main_fix_says_it_repairs_what_fails_or_warns(visit):
    assert visit.summary.startswith("repairs what fails or warns")


def test_a_row_whose_fix_is_the_command_has_a_fix_button(visit):
    assert visit.rows_with_a_button == ["python/.venv", "code intelligence python"]


def test_each_row_button_says_fix(visit):
    assert visit.names == ["Fix", "Fix"]


def test_each_row_button_is_named_for_what_it_fixes(visit):
    assert visit.labels == ["Fix python/.venv", "Fix code intelligence python"]


def test_the_other_hints_stay_text(visit):
    assert visit.hints == [
        f"install JDK 25: {JDK_GUIDE}",
        "install Go 1.25 or newer",
        f"rm -rf python/.venv && {FIX}",
    ]


def test_a_link_in_a_hint_stays_a_link(visit):
    assert visit.hint_links == [JDK_GUIDE]


def test_a_text_hint_does_not_look_clickable(visit):
    assert visit.hint_looks_clickable == [False, False, False]


def test_a_row_fix_asks_the_question_of_the_main_fix(visit):
    assert visit.question == QUESTION


def test_the_questions_backdrop_covers_the_top_bar(visit):
    assert visit.backdrop_covers_the_bar


def test_a_no_starts_nothing_more(visit):
    assert visit.posts_after_a_no == 1


def test_a_no_leaves_every_fix_enabled(visit):
    assert visit.disabled_after_a_no == [False, False, False]


def test_a_yes_starts_the_job_the_main_fix_starts(visit):
    assert visit.posts_after_a_yes == [
        {"command": "doctor_fix"},
        {"command": "doctor_fix"},
        {"command": "doctor_fix", "confirm": True},
    ]


def test_the_job_is_titled_with_its_command(visit):
    assert visit.job_title == FIX


def test_every_fix_is_disabled_while_the_job_runs(visit):
    assert visit.disabled_while_running == [True, True, True]


def test_the_job_ends_with_its_exit_code(visit):
    assert "exit 0" in visit.state_at_the_end


def test_every_fix_is_enabled_again_once_the_job_ended(visit):
    assert visit.disabled_after_the_job == [False, False]


def test_the_checks_are_read_again_after_the_job(visit):
    assert (visit.rechecks, visit.rows_after_the_job) == (2, ["code intelligence python"])


def test_the_page_logs_no_problem(visit):
    assert visit.problems == []
