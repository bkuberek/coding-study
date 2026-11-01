"""The page on a JDK that cannot run the Java and Kotlin of the problems
(docs/specs/web-ui.md#problems-view), in each engine of `tests/browsers.py`: the problem list
marks `java!` and `kt!` with the CLI's reason as the tooltip and as text for assistive
technology, the Start dialog disables the two languages and shows the reason beside them, a
project in Java cannot be started, and a refusal with a `fix:` hint shows the hint, its link a link.

The server selects a fake JDK 27, which cstudy does not support yet, so no toolchain is needed:
the workspace is a bare one, and nothing is built. Playwright and its engines are set up as
`tests/browsers.py` says; without them the test is skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, refusing_starts, watched
from tests.helpers import mark_workspace, selecting_jdk
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
SINGLE_FILE = "two-sum"
PROJECT = "bank-project-java"
ROW = f"tr:has(a.slug[href='#/problems/{SINGLE_FILE}'])"
SHEET = "dialog.sheet[open]"
START = f"{SHEET} button[type=submit]"
NOTE = f"{SHEET} #start-jdk-note"
REFUSAL = (
    "two-sum runs its java version on JDK 21 to 26; "
    "JAVA_HOME selects JDK 27, which cstudy does not support yet"
)
KOTLIN_REFUSAL = REFUSAL.replace("java version", "kotlin version")
GUIDE = "https://example.org/guide#jdk"
FIX = f"select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: {GUIDE}"


@dataclass
class Visit:
    """What the browser saw of a server whose JDK cannot run Java and Kotlin."""

    marks: list[str] = field(default_factory=list[str])
    tooltips: list[str | None] = field(default_factory=list[str | None])
    assistive: list[str] = field(default_factory=list[str])
    refs: str = ""
    options: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    selected: str = ""
    note: list[str] = field(default_factory=list[str])
    start_disabled: bool = True
    project_note: list[str] = field(default_factory=list[str])
    project_start_disabled: bool = False
    refused: list[str] = field(default_factory=list[str])
    refused_links: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"jdk-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    jdk = selecting_jdk(tmp_path_factory.mktemp("jdk-home"), 27)
    with running_server(workspace, variables=jdk) as running:
        yield running


@pytest.fixture(scope="module")
def visit(engine: str, server: RunningServer) -> Visit:
    seen = Visit()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(
            browser.new_page(viewport={"width": 1440, "height": 900}),
            seen.errors,
            _is_the_refusal_logged,
        )
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _read_marks(page, seen)
        _read_start_dialog(page, seen)
        _read_project_dialog(page, seen)
        _read_refused_start(page, seen)
        browser.close()
    return seen


def _lines(text: str) -> list[str]:
    """The lines of rendered text without the blank ones that paragraphs leave."""
    return [line for line in text.splitlines() if line]


def _is_the_refusal_logged(message: Any) -> bool:
    """The browser logs every response of 503, which the test makes the server give."""
    return "status of 503" in message.text


def _read_marks(page: Any, seen: Visit) -> None:
    marks = f"{ROW} td.refs .ref-blocked"
    seen.marks = page.locator(f"{marks} > [aria-hidden]").all_inner_texts()
    seen.tooltips = [
        element.get_attribute("title") for element in page.locator(f"{marks} > [aria-hidden]").all()
    ]
    seen.assistive = page.locator(f"{marks} > .sr-only").all_text_contents()
    seen.refs = page.locator(f"{ROW} td.refs").first.text_content() or ""


def _read_start_dialog(page: Any, seen: Visit) -> None:
    page.goto(page.url.split("#")[0] + f"#/problems/{SINGLE_FILE}")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)
    seen.options = page.locator(f"{SHEET} #start-language option").evaluate_all(
        "options => options.map(option => ({value: option.value, disabled: option.disabled}))"
    )
    seen.selected = page.locator(f"{SHEET} #start-language").input_value()
    seen.note = _lines(page.locator(NOTE).inner_text())
    seen.start_disabled = page.locator(START).is_disabled()


def _read_project_dialog(page: Any, seen: Visit) -> None:
    page.keyboard.press("Escape")
    page.evaluate("slug => { location.hash = `#/problems/${slug}` }", PROJECT)
    page.wait_for_selector(".problem-head h1")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)
    seen.project_note = _lines(page.locator(NOTE).inner_text())
    seen.project_start_disabled = page.locator(START).is_disabled()


def _read_refused_start(page: Any, seen: Visit) -> None:
    """A server that refuses a start with the CLI's `fix:` hint, as one on another JDK would."""
    page.keyboard.press("Escape")
    refusing_starts(page, REFUSAL, FIX)
    page.evaluate("slug => { location.hash = `#/problems/${slug}` }", SINGLE_FILE)
    page.wait_for_selector(".problem-head h1")
    page.click(".practice-actions button.primary")
    page.wait_for_selector(SHEET)
    page.click(START)
    seen.refused = _lines(page.wait_for_selector(f"{SHEET} .state-error").inner_text())
    seen.refused_links = page.locator(f"{SHEET} .state-error a[target=_blank]").evaluate_all(
        "links => links.map(link => link.href)"
    )


def test_the_list_marks_the_languages_the_jdk_cannot_run(visit):
    assert visit.marks == ["java!", "kt!"]


def test_the_list_leaves_the_other_languages_unmarked(visit):
    assert visit.refs.startswith("py ts ")


def test_a_mark_has_the_clis_reason_as_its_tooltip(visit):
    assert visit.tooltips == [REFUSAL, KOTLIN_REFUSAL]


def test_a_mark_has_the_reason_as_text_for_assistive_technology(visit):
    assert visit.assistive == [f"java: {REFUSAL}", f"kt: {KOTLIN_REFUSAL}"]


def test_the_start_dialog_disables_java_and_kotlin(visit):
    disabled = {option["value"] for option in visit.options if option["disabled"]}
    assert disabled == {"java", "kotlin"}


def test_the_start_dialog_keeps_the_other_languages_enabled(visit):
    enabled = {option["value"] for option in visit.options if not option["disabled"]}
    assert enabled == {"python", "typescript", "go", "rust"}


def test_the_start_dialog_starts_in_a_language_the_jdk_can_run(visit):
    assert visit.selected == "python"


def test_the_start_dialog_shows_the_reason_beside_the_languages(visit):
    assert visit.note == [REFUSAL, KOTLIN_REFUSAL]


def test_a_language_the_jdk_can_run_can_be_started(visit):
    assert not visit.start_disabled


def test_a_java_project_cannot_be_started(visit):
    assert visit.project_start_disabled


def test_a_java_project_says_why(visit):
    assert visit.project_note == [REFUSAL.replace("two-sum", PROJECT)]


def test_a_refusal_shows_the_clis_message(visit):
    assert visit.refused[0].endswith(f"error: {REFUSAL}")


def test_a_refusal_shows_the_clis_fix_on_its_own_line(visit):
    assert visit.refused[1] == f"fix: {FIX}"


def test_the_link_of_a_fix_is_a_link(visit):
    assert visit.refused_links == [GUIDE]


def test_the_page_logs_no_error_on_a_jdk_it_cannot_run(visit):
    assert visit.errors == []
