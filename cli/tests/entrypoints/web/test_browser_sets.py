"""The sets in a real browser (docs/specs/web-ui.md#sets-view), in each engine of
`tests/browsers.py`, on a scratch workspace: a set made from the view and another from a row of the
Problems view, one problem in both, the same rows in the same order in `cstudy list --set`, in the
open set and under the Set filter, the Next card following the filter, reordering by the keyboard
with the focus kept, a refusal with its suggestion, rename and delete with their dialogs, and a
broken `sets.yaml` shown as an error and left as it is, stopping nothing but the sets.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
LOOP = "backend-loop"
OTHER = "data-loop"
FIRST = "two-sum"
SECOND = "lru-cache"
ITEM = "url-shortener"
ROWS = "table.problems tbody tr"
SHEET = "dialog.sheet[open]"
COMMAND = ".command-text"
BROKEN = "sets: [unclosed\n"
ROW_LINKS = "table.problems tbody .slug"
REFUSALS = ("status of 409", "status of 422", "status of 503")
"""What a browser logs for the question of Delete, the refused slug and the broken file."""


@dataclass
class Seen:
    tab_names: list[str] = field(default_factory=list[str])
    view_by_shortcut: str = ""
    empty_says: str = ""
    list_command: str = ""
    list_fills_the_page: bool = False
    open_set_fills_the_page: bool = False
    name_issue: str = ""
    after_create: str = ""
    open_command: str = ""
    control_alone: str = ""
    control_words: str = ""
    control_in_two: str = ""
    control_focused_after_escape: bool = False
    dialog_command: str = ""
    problem_view_sets: list[str] = field(default_factory=list[str])
    refusal: str = ""
    rows_after_adding: list[str] = field(default_factory=list[str])
    rows_after_moving: list[str] = field(default_factory=list[str])
    focus_after_moving: str = ""
    moved_said: str = ""
    cli_rows: list[str] = field(default_factory=list[str])
    filter_rows: list[str] = field(default_factory=list[str])
    filter_command: str = ""
    next_under_filter: str = ""
    next_in_the_set: str = ""
    standing: str = ""
    start_dialog: bool = False
    resume_link: str = ""
    rows_after_removing: list[str] = field(default_factory=list[str])
    focus_after_removing: str = ""
    list_of_sets: list[str] = field(default_factory=list[str])
    after_rename: str = ""
    delete_question: str = ""
    delete_command: str = ""
    after_delete: str = ""
    file_after_delete: str = ""
    broken_view: str = ""
    broken_controls: int = -1
    broken_problems_rows: int = 0
    broken_problems_error: str = ""
    broken_file: str = ""
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"sets-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


def cstudy(workspace: Path, *arguments: str) -> str:
    return subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        text=True,
    ).stdout


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector(ROWS)
        _navigation(page, found)
        _create(page, found)
        _control(page, found)
        _problem_view(page, found)
        _add_in_the_set(page, found)
        _reorder(page, found)
        _agree(page, workspace, found)
        _practise(page, workspace, found)
        _remove(page, found)
        _rename_and_delete(page, workspace, found)
        _broken_file(page, workspace, found)
        browser.close()
    return found


def _open(page: Any, route: str, shown: str) -> None:
    page.evaluate("route => { location.hash = route }", route)
    page.wait_for_selector(shown)


def _fills_the_page(page: Any, view: str) -> bool:
    """Whether the view is as wide as `main` inside its padding, as Problems and Progress are."""
    return page.evaluate(
        """view => {
            const main = document.querySelector("main");
            const { paddingLeft, paddingRight } = getComputedStyle(main);
            const room = main.clientWidth - parseFloat(paddingLeft) - parseFloat(paddingRight);
            return document.querySelector(view).getBoundingClientRect().width === room;
        }""",
        view,
    )


def _navigation(page: Any, found: Seen) -> None:
    found.tab_names = page.locator(".topbar nav a").all_inner_texts()
    page.keyboard.press("Alt+2")
    page.wait_for_function("() => location.hash === '#/sets'")
    found.view_by_shortcut = page.evaluate("location.hash")
    page.wait_for_selector(".sets .state-empty")
    found.empty_says = page.locator(".sets .state-empty").inner_text()
    found.list_command = page.locator(COMMAND).inner_text()
    found.list_fills_the_page = _fills_the_page(page, ".sets")


def _create(page: Any, found: Seen) -> None:
    page.click("button:has-text('New set')")
    page.wait_for_selector(SHEET)
    page.locator(f"{SHEET} input").first.fill("Not A Slug")
    found.name_issue = page.locator(f"{SHEET} .dialog-issue").inner_text()
    page.locator(f"{SHEET} input").first.fill(LOOP)
    page.locator(f"{SHEET} input").nth(1).fill("The backend loop on the 12th")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(f".set-open h1:has-text('{LOOP}')")
    found.after_create = page.evaluate("location.hash")
    found.open_command = page.locator(COMMAND).inner_text()
    found.open_set_fills_the_page = _fills_the_page(page, ".set-open")


def _row_control(slug: str) -> str:
    return f"table.problems tr:has(a[href='#/problems/{slug}']) .set-control"


def _control(page: Any, found: Seen) -> None:
    _open(page, "#/", ROWS)
    control = _row_control(FIRST)
    found.control_alone = page.locator(control).inner_text()
    found.control_words = page.locator(control).get_attribute("aria-label") or ""
    page.click(control)
    page.wait_for_selector(f"{SHEET} input[type=checkbox]")
    page.check(f"{SHEET} input[type=checkbox]")
    page.wait_for_selector(f"{SHEET} .set-said:has-text('add {LOOP}')")
    found.dialog_command = page.locator(f"{SHEET} .set-said").inner_text()
    page.fill("#set-new-name", OTHER)
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(f"{SHEET} label:has-text('{OTHER}')")
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    found.control_in_two = page.locator(control).inner_text()
    found.control_focused_after_escape = page.evaluate(
        "() => document.activeElement?.classList.contains('set-control')"
    )


def _problem_view(page: Any, found: Seen) -> None:
    _open(page, f"#/problems/{FIRST}", ".problem-side .set-control")
    found.problem_view_sets = page.locator(
        ".problem-side section:has(#sets-heading) li"
    ).all_inner_texts()


def _rows(page: Any) -> list[str]:
    return page.locator(ROW_LINKS).all_inner_texts()


def _add_in_the_set(page: Any, found: Seen) -> None:
    _open(page, f"#/sets/{LOOP}", "#set-add-slug")
    page.fill("#set-add-slug", "two-summ")
    page.keyboard.press("Enter")
    page.wait_for_selector("#set-add-issue:has-text('did you mean')")
    found.refusal = page.locator("#set-add-issue").inner_text()
    for slug in (SECOND, ITEM):
        page.fill("#set-add-slug", slug)
        page.keyboard.press("Enter")
        page.wait_for_selector(f"{ROW_LINKS}:has-text('{slug}')")
    found.rows_after_adding = _rows(page)


def _reorder(page: Any, found: Seen) -> None:
    page.focus(f"button[data-slug='{FIRST}'][data-action='down']")
    page.keyboard.press("Enter")
    page.wait_for_function(
        "first => document.querySelector('table.problems tbody .slug')?.textContent !== first",
        arg=FIRST,
    )
    found.rows_after_moving = _rows(page)
    page.wait_for_function(
        "slug => document.activeElement?.dataset.slug === slug",
        arg=FIRST,
    )
    found.focus_after_moving = page.evaluate("document.activeElement?.getAttribute('aria-label')")
    page.wait_for_function(
        "() => document.querySelector('[aria-live=polite][role=status]')?.textContent !== ''"
    )
    found.moved_said = page.locator(".sr-only[aria-live=polite]").first.inner_text()


def _agree(page: Any, workspace: Path, found: Seen) -> None:
    document = json.loads(cstudy(workspace, "list", "--set", LOOP, "--json"))
    found.cli_rows = [entry["slug"] for entry in document["entries"]]
    found.next_in_the_set = page.locator(".next-card").inner_text()
    found.standing = page.locator(".set-facts .num").inner_text()
    page.click("a:has-text('filter the Problems view')")
    page.wait_for_selector(_row_control(FIRST))
    found.filter_rows = _rows(page)
    found.filter_command = page.locator(COMMAND).inner_text()
    found.next_under_filter = page.locator(".next-card").inner_text()


def _practise(page: Any, workspace: Path, found: Seen) -> None:
    _open(page, f"#/sets/{LOOP}", "#set-add-slug")
    page.click(f"button[aria-label='Start {SECOND}']")
    page.wait_for_selector(SHEET)
    found.start_dialog = page.locator(SHEET).is_visible()
    page.keyboard.press("Escape")
    page.wait_for_selector(SHEET, state="detached")
    cstudy(workspace, "start", SECOND, "--lang", "python", "--no-open")
    page.reload()
    page.wait_for_selector(f"table.problems tr:has(a[href='#/problems/{SECOND}']) .resume-link")
    found.resume_link = page.locator(".set-open table .resume-link").inner_text()
    cstudy(workspace, "abort", SECOND, "--yes")


def _remove(page: Any, found: Seen) -> None:
    _open(page, f"#/sets/{LOOP}", "#set-add-slug")
    page.click(f"button[aria-label='Remove {SECOND}']")
    page.wait_for_function(
        "slug => ![...document.querySelectorAll('table.problems tbody .slug')]"
        ".some((found) => found.textContent === slug)",
        arg=SECOND,
    )
    found.rows_after_removing = _rows(page)
    page.wait_for_function("() => document.activeElement?.dataset?.action === 'remove'")
    found.focus_after_removing = page.evaluate("document.activeElement?.dataset.slug")


def _rename_and_delete(page: Any, workspace: Path, found: Seen) -> None:
    page.click("button:has-text('Rename')")
    page.wait_for_selector(SHEET)
    page.locator(f"{SHEET} input").first.fill("platform-loop")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(".set-open h1:has-text('platform-loop')")
    found.after_rename = page.evaluate("location.hash")
    page.click("button:has-text('Delete')")
    page.wait_for_selector(f"{SHEET} .question")
    found.delete_question = page.locator(f"{SHEET} .question").inner_text()
    found.delete_command = " ".join(page.locator(f"{SHEET} .sheet-command").inner_text().split())
    page.click(f"{SHEET} button.danger")
    page.wait_for_function("() => location.hash === '#/sets'")
    page.wait_for_selector(".set-list")
    found.after_delete = page.locator(".set-list").inner_text()
    found.list_of_sets = page.locator(".set-list .set-name").all_inner_texts()
    found.file_after_delete = (workspace / "sets.yaml").read_text()


def _broken_file(page: Any, workspace: Path, found: Seen) -> None:
    file = workspace / "sets.yaml"
    file.write_text(BROKEN)
    page.evaluate("location.hash = '#/'")
    page.wait_for_selector(".listing .state-error")
    found.broken_problems_rows = page.locator(ROWS).count()
    found.broken_problems_error = page.locator(".listing .state-error").inner_text()
    _open(page, "#/sets", ".sets .state-error")
    found.broken_view = page.locator(".sets .state-error").inner_text()
    found.broken_controls = page.locator(".sets button:not(:disabled)").count()
    found.broken_file = file.read_text()


def test_the_views_are_numbered_with_sets_second(seen):
    assert [name.split(":")[0] for name in seen.tab_names] == ["1", "2", "3", "4", "5", "6", "7"]


def test_the_view_after_problems_is_sets(seen):
    assert "sets" in seen.tab_names[1]


def test_the_list_of_sets_fills_the_page(seen):
    assert seen.list_fills_the_page


def test_an_open_set_fills_the_page(seen):
    assert seen.open_set_fills_the_page


def test_alt_2_opens_the_sets(seen):
    assert seen.view_by_shortcut == "#/sets"


def test_with_no_sets_the_view_says_so(seen):
    assert "no sets yet" in seen.empty_says


def test_the_command_line_shows_the_list_of_sets(seen):
    assert seen.list_command == "cstudy set list"


def test_a_bad_name_is_refused_as_it_is_typed(seen):
    assert "such as backend-loop" in seen.name_issue


def test_a_new_set_opens(seen):
    assert seen.after_create == f"#/sets/{LOOP}"


def test_the_command_line_shows_the_open_set(seen):
    assert seen.open_command == f"cstudy set show {LOOP}"


def test_a_problem_in_no_set_offers_to_join_one(seen):
    assert (seen.control_alone, seen.control_words) == (
        "+ set",
        f"{FIRST} is in no set: add it to one",
    )


def test_the_dialog_names_the_command(seen):
    assert seen.dialog_command == f"cstudy set add {LOOP} {FIRST}"


def test_a_problem_can_be_in_two_sets_and_the_row_says_so(seen):
    assert seen.control_in_two == f"{LOOP} +1"


def test_escape_gives_the_focus_back_to_the_control(seen):
    assert seen.control_focused_after_escape is True


def test_the_problem_view_lists_each_set_it_is_in(seen):
    assert seen.problem_view_sets == [LOOP, OTHER]


def test_an_unknown_slug_is_refused_with_a_suggestion(seen):
    assert seen.refusal == 'unknown problem "two-summ"; did you mean two-sum?'


def test_problems_and_items_join_in_the_order_added(seen):
    assert seen.rows_after_adding == [FIRST, SECOND, ITEM]


def test_a_row_moves_by_the_keyboard(seen):
    assert seen.rows_after_moving == [SECOND, FIRST, ITEM]


def test_the_focus_stays_on_the_row_that_moved(seen):
    assert seen.focus_after_moving == f"Move {FIRST} down"


def test_a_move_is_read_out(seen):
    assert seen.moved_said == f"moved {FIRST} to 2"


def test_the_rows_match_cstudy_list_set(seen):
    assert seen.cli_rows == seen.rows_after_moving


def test_the_set_filter_shows_the_same_rows_in_the_same_order(seen):
    assert seen.filter_rows == seen.rows_after_moving


def test_the_filter_names_its_flag(seen):
    assert seen.filter_command == f"cstudy list --set {LOOP}"


def test_the_next_card_follows_the_filter(seen):
    assert f"next in {LOOP}, 1 of 3" in seen.next_under_filter


def test_the_open_set_shows_its_pick(seen):
    assert f"next in {LOOP}, 1 of 3" in seen.next_in_the_set


def test_the_open_set_shows_passed_of_total(seen):
    assert seen.standing == "0 of 3 passed"


def test_a_row_starts_with_the_start_dialog(seen):
    assert seen.start_dialog is True


def test_a_row_with_an_open_attempt_resumes_it(seen):
    assert seen.resume_link == "Resume python"


def test_remove_takes_the_row_out(seen):
    assert seen.rows_after_removing == [FIRST, ITEM]


def test_the_focus_moves_to_the_row_that_follows(seen):
    assert seen.focus_after_removing == FIRST


def test_a_rename_opens_the_set_by_its_new_name(seen):
    assert seen.after_rename == "#/sets/platform-loop"


def test_delete_asks_and_says_progress_stays(seen):
    assert "Your progress stays" in seen.delete_question


def test_the_question_names_the_command(seen):
    assert seen.delete_command == "as cstudy set delete platform-loop"


def test_delete_leaves_the_other_set(seen):
    assert seen.list_of_sets == [OTHER]


def test_the_list_shows_passed_of_total(seen):
    assert "0 of 1 passed" in seen.after_delete


def test_the_file_holds_the_other_set(seen):
    assert (OTHER in seen.file_after_delete, "platform-loop" in seen.file_after_delete) == (
        True,
        False,
    )


def test_a_broken_file_shows_as_an_error_in_the_view(seen):
    assert "sets.yaml: line 2" in seen.broken_view


def test_a_broken_file_offers_no_way_to_change_it(seen):
    assert seen.broken_controls == 0


def test_a_broken_file_stays_as_it_is(seen):
    assert seen.broken_file == BROKEN


def test_a_broken_file_does_not_stop_the_problems_view(seen):
    assert seen.broken_problems_rows > 0


def test_the_problems_view_says_what_is_wrong_with_the_file(seen):
    assert "sets.yaml" in seen.broken_problems_error


def test_only_what_the_server_refused_on_purpose_reached_the_console(seen):
    assert [line for line in seen.logged if not any(code in line for code in REFUSALS)] == []
