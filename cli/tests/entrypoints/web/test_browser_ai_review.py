"""AI review in the page (docs/specs/web-ui.md#ai-review-in-the-page) in a real browser, in each
engine of `tests/browsers.py`, against a real `cstudy serve` whose child `cstudy` reaches the fake
provider of `tests/fake_ai_provider.py`: the panel before any review; unsaved notes refused; the
consent question asked, which Cancel and Escape answer with nothing sent and Send answers by
starting the review; the review shown with its verdicts, quotes, gaps, summary and usage; Review
again without a second question; Dismiss and the earlier reviews; `notes changed since this
review`; a review made in the terminal; History's line and dialog; the Checked by column and
filter; and, with AI off, no AI control while History still reads the stored reviews. Text a model
wrote, markup included, is shown as text.

No test calls a real provider. Playwright and its engines are set up as `tests/browsers.py` says;
without them the test is skipped.
"""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.ai import Provider
from tests.ai_review_workspace import (
    ANSWER,
    CRITERIA,
    HACK,
    SLUG,
    notes_path,
    review_answer,
    review_workspace,
)
from tests.ai_workspace import CONFIG, MODEL, SENTINEL_KEY, config_path
from tests.browsers import launched, watched
from tests.fake_ai_provider import FakeAiProvider, Route
from tests.serve_process import running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
WIDE = {"width": 1440, "height": 900}
PANEL = "section[aria-label='AI review']"
BUTTON = "button[title^='cstudy ai review']"
AGAIN = f"{PANEL} button:has-text('Review again')"
DISMISS = f"{PANEL} button:has-text('Dismiss')"
RESULT = f"{PANEL} .ai-review-result"
WORKING = f"{PANEL} .ai-review-working"
CANCEL = f"{PANEL} button.job-cancel"
EARLIER = f"{PANEL} details.ai-earlier"
SHEET = "dialog.sheet[open]"
EDITOR = ".panel:not([hidden]) .cm-content"
STATUS_LINE = ".sr-only[aria-live=polite]"
LINE = ".ai-review-line"
FIRST = "18 met · 6 partly · 4 missed of 28"
SECOND = "10 met · 10 partly · 8 missed of 28"
THIRD = "5 met · 5 partly · 18 missed of 28"
NOTICE = "The same answer can get a different review. It changes no grade and no schedule."
CONFLICT = "status of 409"


@dataclass
class Seen:
    """What the page said and did, step by step."""

    button_title: str = ""
    intro: str = ""
    buttons_before: list[str] = field(default_factory=list[str])
    unsaved_says: str = ""
    sent_after_unsaved: int = -1
    consent_title: str = ""
    consent_text: str = ""
    consent_buttons: list[str] = field(default_factory=list[str])
    consent_focus: str = ""
    sent_after_cancel: int = -1
    focus_after_cancel: str = ""
    sent_after_escape: int = -1
    working: str = ""
    cancel_shown: bool = False
    result: str = ""
    heading: str = ""
    model_line: str = ""
    notice: str = ""
    areas: int = 0
    verdicts: list[str] = field(default_factory=list[str])
    first_quote: str = ""
    gap: str = ""
    summary: str = ""
    usage: str = ""
    images: int = 0
    links: int = 0
    pwned: bool = False
    text_shows_markup: bool = False
    page_after: str = ""
    consents: list[Any] = field(default_factory=list[Any])
    announced_ready: str = ""
    sent_after_send: int = 0
    dialogs_after_again: int = -1
    second_result: str = ""
    earlier_label: str = ""
    sent_after_again: int = 0
    dismissed_result: str = ""
    earlier_after_dismiss: str = ""
    earlier_listed: list[str] = field(default_factory=list[str])
    focus_after_dismiss: str = ""
    dismissed_in_api: list[bool] = field(default_factory=list[bool])
    changed_before: int = -1
    changed_after: str = ""
    terminal_result: str = ""
    history_line: str = ""
    history_dialog_title: str = ""
    history_dialog_text: str = ""
    history_entries: list[str] = field(default_factory=list[str])
    history_open_entries: int = 0
    focus_after_history: str = ""
    checked_cell: str = ""
    checked_choices: list[str] = field(default_factory=list[str])
    checked_rows: list[str] = field(default_factory=list[str])
    off_buttons: int = -1
    off_panels: int = -1
    off_results: str = ""
    off_line: str = ""
    off_dialog_entries: int = 0
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def fake() -> Iterator[FakeAiProvider]:
    with FakeAiProvider() as provider:
        provider.script(
            Provider.ANTHROPIC, Route.COMPLETE, review_answer(delay_s=1.5), review_answer(10, 10)
        )
        provider.script(Provider.ANTHROPIC, Route.COMPLETE, review_answer(5, 5, summary="Third."))
        yield provider


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return review_workspace(tmp_path_factory.mktemp(f"ai-review-{engine}"), consented=False)


def _expected(message: Any) -> bool:
    return CONFLICT in message.text


@pytest.fixture(scope="module")
def seen(engine: str, workspace: Path, fake: FakeAiProvider) -> Seen:
    found = Seen()
    variables = {"CSTUDY_AI_ENDPOINT": fake.endpoint}
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        with running_server(workspace, variables=variables) as server:
            page = watched(browser.new_page(viewport=WIDE), found.logged, _expected)
            page.set_default_timeout(WAIT_MS)
            page.goto(server.login_url)
            page.wait_for_selector("table.problems tbody tr")
            attempt = _attempt_id(page)
            _open_attempt(page, attempt)
            _before(page, fake, found)
            _consent(page, fake, found)
            _first_review(page, fake, found)
            _again(page, fake, found)
            _dismiss(page, found)
            _notes_changed(page, workspace, found)
            _terminal(page, workspace, fake, found)
            _history(page, found)
            _checked_by(page, found)
            page.close()
        _ai_off(browser, workspace, attempt, found)
        browser.close()
    return found


def _text(page: Any, selector: str) -> str:
    return " ".join(page.locator(selector).first.inner_text().split())


def _attempt_id(page: Any) -> int:
    return page.evaluate(
        f"fetch('/api/v1/problems/{SLUG}').then(r => r.json())"
        ".then(p => p.in_progress[0].attempt_id)"
    )


def _open_attempt(page: Any, attempt: int) -> None:
    page.evaluate("route => { location.hash = route }", f"#/attempts/{attempt}")
    page.wait_for_selector(f"{PANEL} .ai-review-intro")
    page.wait_for_selector(EDITOR)


def _sent(fake: FakeAiProvider) -> int:
    return len(fake.requests_to(Provider.ANTHROPIC, Route.COMPLETE))


def _before(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    seen.button_title = page.get_attribute(BUTTON, "title") or ""
    seen.intro = _text(page, f"{PANEL} .ai-review-intro")
    seen.buttons_before = [
        name
        for name in ("Review again", "Dismiss")
        if page.locator(f"{PANEL} button:has-text('{name}')").is_visible()
    ]
    page.click(EDITOR)
    page.keyboard.press("ControlOrMeta+End")
    page.keyboard.type("Extra.")
    page.click(BUTTON)
    page.wait_for_selector(f"{PANEL} .state-error")
    seen.unsaved_says = _text(page, f"{PANEL} .state-error")
    seen.sent_after_unsaved = _sent(fake)
    page.keyboard.press("ControlOrMeta+s")
    page.wait_for_selector("[role=tab][aria-label$='unsaved changes']", state="detached")


def _open_consent(page: Any) -> None:
    page.click(BUTTON)
    page.wait_for_selector(SHEET)


def _consent(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    _open_consent(page)
    seen.consent_title = page.locator(f"{SHEET} h2").inner_text()
    seen.consent_text = _text(page, f"{SHEET} .sheet-body")
    seen.consent_buttons = page.locator(f"{SHEET} .sheet-actions button").all_inner_texts()
    seen.consent_focus = page.evaluate("document.activeElement?.textContent")
    page.click(f"{SHEET} button:has-text('Cancel')")
    page.wait_for_selector(SHEET, state="detached")
    seen.sent_after_cancel = _sent(fake)
    seen.focus_after_cancel = page.evaluate("document.activeElement?.textContent")
    _open_consent(page)
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    seen.sent_after_escape = _sent(fake)


def _first_review(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    _open_consent(page)
    page.click(f"{SHEET} button:has-text('Send')")
    page.wait_for_selector(SHEET, state="detached")
    page.wait_for_selector(f"{WORKING}:has-text('reviewing with')")
    seen.working = _text(page, WORKING)
    seen.cancel_shown = page.is_visible(CANCEL)
    page.wait_for_selector(f"{RESULT}:has-text('{FIRST}')")
    seen.result = _text(page, RESULT)
    seen.heading = page.locator(f"{PANEL} h2").first.text_content()
    seen.model_line = _text(page, f"{PANEL} .ai-review-model")
    seen.notice = _text(page, f"{PANEL} .ai-review-notice")
    seen.areas = page.locator(f"{PANEL} .ai-area h3").count()
    seen.verdicts = [
        " ".join(verdict.split())
        for verdict in page.locator(f"{PANEL} .ai-criterion .badge").all_inner_texts()
    ]
    seen.first_quote = _text(page, f"{PANEL} .ai-quote")
    seen.gap = _text(page, f"{PANEL} .ai-gap")
    seen.summary = _text(page, f"{PANEL} .ai-review-summary")
    seen.usage = _text(page, f"{PANEL} .ai-review-usage")
    seen.images = page.locator(f"{PANEL} img").count()
    seen.links = page.locator(f"{PANEL} .ai-review-view a").count()
    seen.pwned = bool(page.evaluate("window.__pwned === 1"))
    seen.text_shows_markup = HACK in page.locator(f"{PANEL} .ai-review-summary").inner_text()
    seen.page_after = page.content()
    seen.consents = page.evaluate(
        "fetch('/api/v1/ai/status').then(response => response.json()).then(s => s.consents)"
    )
    seen.sent_after_send = _sent(fake)
    page.wait_for_selector(f"{STATUS_LINE}:has-text('AI review ready')")
    seen.announced_ready = _text(page, STATUS_LINE)
    page.wait_for_selector(f"{PANEL} section.job", state="hidden")


def _again(page: Any, fake: FakeAiProvider, seen: Seen) -> None:
    page.click(AGAIN)
    page.wait_for_selector(f"{RESULT}:has-text('{SECOND}')")
    seen.dialogs_after_again = page.locator(SHEET).count()
    seen.second_result = _text(page, RESULT)
    seen.earlier_label = _text(page, f"{EARLIER} > summary")
    seen.sent_after_again = _sent(fake)


def _reviews(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(
        f"fetch('/api/v1/problems/{SLUG}/ai-reviews').then(r => r.json()).then(l => l.reviews)"
    )


def _dismiss(page: Any, seen: Seen) -> None:
    page.click(DISMISS)
    page.wait_for_selector(f"{RESULT}:has-text('{FIRST}')")
    seen.dismissed_result = _text(page, RESULT)
    seen.earlier_after_dismiss = _text(page, f"{EARLIER} > summary")
    page.wait_for_function("() => document.activeElement?.id === 'ai-review-heading'")
    seen.focus_after_dismiss = page.evaluate("document.activeElement?.id")
    page.click(f"{EARLIER} > summary")
    seen.earlier_listed = page.locator(f"{EARLIER} > ul > li > details > summary").all_inner_texts()
    seen.dismissed_in_api = [review["dismissed_at"] is not None for review in _reviews(page)]


def _notes_changed(page: Any, workspace: Path, seen: Seen) -> None:
    seen.changed_before = page.locator(f"{PANEL} .ai-review-changed").count()
    notes_path(workspace).write_text(ANSWER + "\nA new paragraph.\n")
    page.reload()
    page.wait_for_selector(f"{RESULT}:has-text('{FIRST}')")
    page.wait_for_selector(f"{PANEL} .ai-review-changed")
    seen.changed_after = _text(page, f"{PANEL} .ai-review-changed")


def _terminal(page: Any, workspace: Path, fake: FakeAiProvider, seen: Seen) -> None:
    environment = {**served_environment(workspace), "CSTUDY_AI_ENDPOINT": fake.endpoint}
    subprocess.run(
        [sys.executable, "-m", "coding_study", "ai", "review", SLUG],
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    page.wait_for_selector(f"{RESULT}:has-text('{THIRD}')")
    seen.terminal_result = _text(page, RESULT)


def _history(page: Any, seen: Seen) -> None:
    page.evaluate("route => { location.hash = route }", f"#/problems/{SLUG}")
    page.click("ol.attempts > li > details > summary")
    page.wait_for_selector(f"{LINE} button")
    seen.history_line = _text(page, LINE)
    page.click(f"{LINE} button")
    page.wait_for_selector(SHEET)
    seen.history_dialog_title = page.locator(f"{SHEET} h2").inner_text()
    seen.history_dialog_text = _text(page, f"{SHEET} .sheet-body")
    seen.history_entries = page.locator(
        f"{SHEET} details.ai-review-entry > summary"
    ).all_inner_texts()
    seen.history_open_entries = page.locator(f"{SHEET} details.ai-review-entry[open]").count()
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    seen.focus_after_history = page.evaluate("document.activeElement?.textContent")


def _checked_by(page: Any, seen: Seen) -> None:
    page.evaluate("route => { location.hash = route }", f"#/?search={SLUG}")
    page.wait_for_selector(f"table.problems tbody tr:has-text('{SLUG}')")
    seen.checked_cell = _text(page, f"table.problems tbody tr:has-text('{SLUG}') td:first-child")
    page.evaluate("route => { location.hash = route }", "#/?checked=ai-review")
    page.wait_for_selector("table.problems tbody tr")
    seen.checked_rows = page.locator("table.problems tbody tr td:first-child").all_inner_texts()
    page.evaluate("route => { location.hash = route }", "#/")
    page.wait_for_selector("table.problems tbody tr")
    seen.checked_choices = page.eval_on_selector_all(
        "#filter-checked option", "options => options.map(option => option.value)"
    )


def _ai_off(browser: Any, workspace: Path, attempt: int, found: Seen) -> None:
    """A second server over the same workspace with AI off: no AI control, and the stored
    reviews still read in History."""
    config_path(workspace).write_text(CONFIG.replace("true", "false"))
    with running_server(workspace) as server:
        page = watched(browser.new_page(viewport=WIDE), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("route => { location.hash = route }", f"#/attempts/{attempt}")
        page.wait_for_selector(EDITOR)
        page.wait_for_selector(".results .quiet:has-text('no runs')")
        found.off_buttons = page.locator(BUTTON).count()
        found.off_panels = page.locator(PANEL).count()
        found.off_results = _text(page, ".results")
        page.evaluate("route => { location.hash = route }", f"#/problems/{SLUG}")
        page.click("ol.attempts > li > details > summary")
        page.wait_for_selector(f"{LINE} button")
        found.off_line = _text(page, LINE)
        page.click(f"{LINE} button")
        page.wait_for_selector(SHEET)
        found.off_dialog_entries = page.locator(f"{SHEET} details.ai-review-entry").count()
        page.close()


def test_the_attempt_header_names_the_command_and_the_panel_explains_before_any_review(seen):
    assert seen.button_title.startswith(f"cstudy ai review {SLUG}")
    assert "reads your notes against this problem's rubric" in seen.intro
    assert "after you agree" in seen.intro
    assert "changes no grade and no schedule" in seen.intro
    assert seen.buttons_before == []


def test_unsaved_notes_are_refused_in_words_and_nothing_is_sent(seen):
    assert "save your notes first: AI review reads them from disk" in seen.unsaved_says
    assert seen.sent_after_unsaved == 0


def test_the_consent_dialog_names_the_model_what_it_sends_and_what_it_costs(seen):
    assert seen.consent_title == f"Send to {MODEL}?"
    for text in (
        "cstudy ai consent",
        "AI review sends, from this machine:",
        "your notes",
        "tokens in, up to",
        "Your anthropic account's terms apply to what it receives.",
        "cstudy asks once for this model and AI review.",
    ):
        assert text in seen.consent_text
    assert seen.consent_buttons == ["Cancel", "Send"]


def test_cancel_holds_the_focus_and_cancel_and_escape_send_nothing(seen):
    assert seen.consent_focus == "Cancel"
    assert seen.sent_after_cancel == 0
    assert seen.focus_after_cancel == "AI review"
    assert seen.sent_after_escape == 0


def test_send_starts_the_review_which_says_the_model_and_can_be_canceled(seen):
    assert seen.working == f"reviewing with {MODEL}…"
    assert seen.cancel_shown
    assert seen.sent_after_send == 1


def test_the_review_shows_the_model_the_notice_and_the_result(seen):
    assert seen.heading == "AI review"
    assert seen.model_line.startswith(MODEL)
    assert seen.notice == NOTICE
    assert seen.result == f"result {FIRST}"
    assert seen.areas == 7
    assert seen.consents[0]["purpose"] == "review"
    assert len(seen.consents) == 1


def test_each_criterion_has_its_verdict_as_a_word_and_a_glyph(seen):
    assert len(seen.verdicts) == CRITERIA
    assert seen.verdicts[0] == "✓ met"
    assert "◐ partly" in seen.verdicts
    assert seen.verdicts[-1] == "✕ missed"


def test_quotes_gaps_summary_and_usage_are_shown(seen):
    assert seen.first_quote.startswith("“Redirects stay fast even when creating links is down.")
    assert seen.gap.startswith("gap: nothing on how fresh click counts must be")
    assert seen.summary.startswith("summary Strong on the redirect path.")
    assert seen.usage == "9,812 tokens in, 2,410 out · cost unknown"


def test_markup_in_a_models_text_is_text_and_makes_no_element(seen):
    assert HACK in seen.gap
    assert seen.text_shows_markup
    assert (seen.images, seen.links, seen.pwned) == (0, 0, False)


def test_no_key_is_in_the_page(seen):
    assert SENTINEL_KEY not in seen.page_after


def test_the_live_region_says_when_the_review_is_ready(seen):
    assert seen.announced_ready == "AI review ready: 18 met, 6 partly, 4 missed"


def test_review_again_sends_without_a_second_question_and_shows_the_newer_review(seen):
    assert seen.dialogs_after_again == 0
    assert seen.second_result == f"result {SECOND}"
    assert seen.earlier_label == "earlier reviews (1)"
    assert seen.sent_after_again == 2


def test_dismiss_shows_the_review_before_it_marks_the_dismissed_one_and_moves_the_focus(seen):
    assert seen.dismissed_result == f"result {FIRST}"
    assert seen.earlier_after_dismiss == "earlier reviews (1)"
    assert seen.earlier_listed[0].endswith(f"{SECOND} · dismissed")
    assert seen.focus_after_dismiss == "ai-review-heading"
    assert seen.dismissed_in_api == [True, False]


def test_notes_changed_since_the_review_is_said_once_the_notes_differ(seen):
    assert seen.changed_before == 0
    assert seen.changed_after == "! notes changed since this review"


def test_a_review_made_in_the_terminal_shows_without_reloading(seen):
    assert seen.terminal_result == f"result {THIRD}"


def test_history_gives_the_latest_review_with_view_and_the_dialog_reads_them_all(seen):
    assert seen.history_line == f"AI review: {THIRD} View"
    assert seen.history_dialog_title.startswith("AI reviews of attempt ")
    assert NOTICE in seen.history_dialog_text
    assert len(seen.history_entries) == 3
    assert seen.history_entries[1].endswith(f"{SECOND} · dismissed")
    assert seen.history_open_entries == 1
    assert seen.focus_after_history == "View"


def test_the_problems_view_says_rubric_plus_ai_review(seen):
    assert seen.checked_cell == "rubric + AI review"
    assert seen.checked_choices == ["", "tests", "rubric", "ai-review"]
    assert seen.checked_rows
    assert set(seen.checked_rows) == {"rubric + AI review"}


def test_with_ai_off_there_is_no_ai_control_and_history_still_reads_the_reviews(seen):
    assert (seen.off_buttons, seen.off_panels) == (0, 0)
    assert "no runs" in seen.off_results
    assert seen.off_line == f"AI review: {THIRD} View"
    assert seen.off_dialog_entries == 3


def test_the_page_logged_no_error_and_no_csp_violation(seen):
    assert seen.logged == []
