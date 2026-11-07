"""The Settings view's one Save in a real browser (docs/specs/web-ui.md#settings-view), in each
engine of `tests/browsers.py`: a bar under the top bar that stays on screen, every change staged
with its count and a Reset that undoes it, the theme previewed, a question before leaving, a Save
that writes each store and says which one failed, and `progress_db`'s question within it.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
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
POLL_MS = 50
WIDE = {"width": 1440, "height": 900}
NARROW = {"width": 390, "height": 844}
SMALLEST = {"width": 320, "height": 640}
CONFIG_TEXT = """\
# My settings: keep this line
[schedule]
max_interval_days = 90 # three months

[next]
tracks = ["lld", "dsa"]

[bench]
reps = 9
"""
PREFERENCES = Path(".cs") / "serve" / "preferences.json"
READY = "ul.languages .language-name"
BAR = ".settings-bar"
TOP_BAR = ".topbar"
SAVE = f"{BAR} button[type=submit]"
RESET = f"{BAR} button:has-text('Reset')"
COUNT = f"{BAR} .settings-count"
STATUS = f"{BAR} p[role=status]"
VIM = "#pref-vim"
TYPECHECK = "#pref-typecheck"
DARK = "#theme-dark"
MAX_INTERVAL = "#config-schedule-max_interval_days"
REPS = "#config-bench-reps"
PROGRESS_DB = "#config-progress_db"
SHEET = "dialog.sheet[open]"
QUESTION = f"{SHEET} .question"
VIM_TOGGLE = "button.toggle:has-text('vim')"
LEAVE_LINK = ".topbar nav a[data-view='problems']"
CHROMIUM = "chromium"
THEME_SHOWN = "document.documentElement.dataset.theme"
REFUSED_KEY = "bench.reps: expected a positive integer"


@dataclass
class Bar:
    """Where the bar and what it holds are, after scrolling to the foot of the page."""

    top: float
    top_bar_bottom: float
    left: float
    width: float
    window: float
    title_on_screen: bool
    save_on_screen: bool


@dataclass
class State:
    """What the bar shows and what the page's controls and files hold at a moment."""

    count_visible: bool
    count: str
    reset_visible: bool
    save_disabled: bool


@dataclass
class Seen:
    untouched: State | None = None
    bar_wide: Bar | None = None
    bar_narrow: Bar | None = None
    bar_narrow_with_a_change: Bar | None = None
    bar_smallest: Bar | None = None
    save_moved_wide: bool = True
    save_moved_narrow: bool = True
    field_clear_wide: bool = False
    field_clear_smallest: bool = False
    one_change: State | None = None
    two_changes: State | None = None
    row_marked: bool = False
    untouched_row_marked: bool = True
    stored_while_staged: str = ""
    file_while_staged: str = ""
    previewed: str = ""
    status_bar_previewed: str = ""
    three_changes: State | None = None
    after_reset: State | None = None
    vim_after_reset: bool = True
    interval_after_reset: str = ""
    theme_after_reset: str = ""
    reset_says: str = ""
    focus_after_reset: str = ""
    question: str = ""
    kept_after_declining: tuple[str, bool] = ("", False)
    left_after_agreeing: str = ""
    vim_after_coming_back: bool = True
    theme_after_leaving: str = ""
    left_with_no_changes_asked: bool = True
    unload_prevented_with_no_changes: bool = True
    unload_prevented_with_changes: bool = False
    unload_dialog: str = ""
    saved_says: str = ""
    saved_preferences: dict[str, object] = field(default_factory=dict[str, object])
    saved_file: str = ""
    after_save: State | None = None
    focus_after_save: str = ""
    config_refused_says: str = ""
    config_refused_ink: str = ""
    fail_ink: str = ""
    config_refused_preferences: dict[str, object] = field(default_factory=dict[str, object])
    config_refused_file: str = ""
    config_refused_state: State | None = None
    preferences_failed_says: str = ""
    preferences_failed_file: str = ""
    preferences_failed_state: State | None = None
    file_after_enter: str = ""
    focus_after_enter: str = ""
    question_in_save: str = ""
    declined_says: str = ""
    declined_preferences: dict[str, object] = field(default_factory=dict[str, object])
    declined_file: str = ""
    declined_state: State | None = None
    confirmed_preferences: dict[str, object] = field(default_factory=dict[str, object])
    confirmed_file: str = ""
    followed_toggle: bool = False
    toggle_kept_the_preview: str = ""
    toggle_state: State | None = None
    broken_fields_disabled: bool = False
    broken_says: str = ""
    broken_saved_preferences: dict[str, object] = field(default_factory=dict[str, object])
    logged: list[str] = field(default_factory=list[str])
    errors_before_the_failures: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"settings-save-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def config_file(workspace: Path) -> Path:
    path = workspace.parent / "config" / "coding-study" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(CONFIG_TEXT)
    return path


@pytest.fixture(scope="module")
def server(workspace: Path, config_file: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer, workspace: Path, config_file: Path) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport=WIDE), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _open_settings(page)
        found.untouched = _state(page)
        _bar_stays(page, found)
        _stage(page, workspace, config_file, found)
        _reset(page, found)
        _leave(page, found)
        _unload(page, engine, found)
        _save_both(page, workspace, config_file, found)
        found.errors_before_the_failures = list(found.logged)
        _one_store_refused(page, workspace, config_file, found)
        _preferences_fail(page, config_file, found)
        _enter_saves(page, config_file, found)
        _progress_db(page, workspace, config_file, found)
        _status_bar_toggle(page, workspace, found)
        _broken_file(page, workspace, config_file, found)
        browser.close()
    return found


def _open_settings(page: Any) -> None:
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector(READY)
    page.wait_for_selector(MAX_INTERVAL)


def _state(page: Any) -> State:
    return State(
        page.is_visible(COUNT),
        page.locator(COUNT).inner_text() if page.is_visible(COUNT) else "",
        page.is_visible(RESET),
        page.is_disabled(SAVE),
    )


def _stored(workspace: Path) -> dict[str, object]:
    path = workspace / PREFERENCES
    return json.loads(path.read_text()) if path.exists() else {}


def _focused(page: Any) -> str:
    return page.evaluate("document.activeElement?.id ?? ''")


def _bar_at_the_foot_of_the_page(page: Any) -> Bar:
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    return Bar(
        **page.evaluate(
            f"""() => {{
                const box = (selector) => document.querySelector(selector).getBoundingClientRect();
                const bar = box("{BAR}");
                const room = document.documentElement.clientWidth;
                const onScreen = (b) => b.top >= 0 && b.left >= 0 && b.right <= room;
                return {{
                    top: bar.top,
                    top_bar_bottom: box("{TOP_BAR}").bottom,
                    left: bar.left,
                    width: bar.width,
                    window: room,
                    title_on_screen: onScreen(box("{BAR} h1")),
                    save_on_screen: onScreen(box("{SAVE}")),
                }};
            }}"""
        )
    )


def _save_moves_when_a_change_shows(page: Any) -> bool:
    before = page.locator(SAVE).bounding_box()
    page.check(VIM)
    after = page.locator(SAVE).bounding_box()
    page.uncheck(VIM)
    return before["x"] != after["x"]


def _focused_field_clears_the_bar(page: Any) -> bool:
    """From the foot of the page, the focus scrolls a field back into view, clear of the bar."""
    page.evaluate("document.activeElement.blur()")
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.locator(VIM).focus()
    field = page.locator(VIM).bounding_box()
    bar = page.locator(BAR).bounding_box()
    return field["y"] >= bar["y"] + bar["height"]


def _bar_stays(page: Any, found: Seen) -> None:
    found.bar_wide = _bar_at_the_foot_of_the_page(page)
    found.field_clear_wide = _focused_field_clears_the_bar(page)
    found.save_moved_wide = _save_moves_when_a_change_shows(page)
    page.set_viewport_size(NARROW)
    found.bar_narrow = _bar_at_the_foot_of_the_page(page)
    found.save_moved_narrow = _save_moves_when_a_change_shows(page)
    page.check(VIM)
    found.bar_narrow_with_a_change = _bar_at_the_foot_of_the_page(page)
    page.uncheck(VIM)
    page.set_viewport_size(SMALLEST)
    page.check(VIM)
    found.bar_smallest = _bar_at_the_foot_of_the_page(page)
    found.field_clear_smallest = _focused_field_clears_the_bar(page)
    page.uncheck(VIM)
    page.set_viewport_size(WIDE)
    page.evaluate("window.scrollTo(0, 0)")


def _stage(page: Any, workspace: Path, config_file: Path, found: Seen) -> None:
    page.check(VIM)
    found.one_change = _state(page)
    found.row_marked = page.locator(".switch:has(#pref-vim).changed").count() == 1
    found.untouched_row_marked = page.locator(".switch:has(#pref-typecheck).changed").count() == 1
    page.fill(MAX_INTERVAL, "120")
    found.two_changes = _state(page)
    found.stored_while_staged = (
        (workspace / PREFERENCES).read_text() if (workspace / PREFERENCES).exists() else ""
    )
    found.file_while_staged = config_file.read_text()
    page.check(DARK)
    found.previewed = page.evaluate(THEME_SHOWN)
    found.status_bar_previewed = page.locator("button.toggle:has-text('theme')").inner_text()
    found.three_changes = _state(page)


def _reset(page: Any, found: Seen) -> None:
    page.click(RESET)
    found.after_reset = _state(page)
    found.vim_after_reset = page.is_checked(VIM)
    found.interval_after_reset = page.input_value(MAX_INTERVAL)
    found.theme_after_reset = page.evaluate(THEME_SHOWN)
    found.reset_says = page.locator(STATUS).inner_text()
    found.focus_after_reset = _focused(page)


def _answered(page: Any, link: str, *, agree: bool) -> str:
    """Clicks `link`, answers the browser's question, and returns the question."""
    asked: list[str] = []

    def answer(dialog: Any) -> None:
        asked.append(dialog.message)
        if agree:
            dialog.accept()
        else:
            dialog.dismiss()

    page.once("dialog", answer)
    page.click(link)
    for _ in range(WAIT_MS // POLL_MS):
        if asked:
            return asked[0]
        page.wait_for_timeout(POLL_MS)
    raise AssertionError("the browser asked nothing")


def _leave(page: Any, found: Seen) -> None:
    page.check(VIM)
    page.check(DARK)
    found.question = _answered(page, LEAVE_LINK, agree=False)
    found.kept_after_declining = (page.evaluate("location.hash"), page.is_checked(VIM))
    _answered(page, LEAVE_LINK, agree=True)
    page.wait_for_selector("table.problems tbody tr")
    found.left_after_agreeing = page.evaluate("location.hash")
    found.theme_after_leaving = page.evaluate(THEME_SHOWN)
    _open_settings(page)
    found.vim_after_coming_back = page.is_checked(VIM)
    asked: list[str] = []

    def note(dialog: Any) -> None:
        asked.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", note)
    page.click(".topbar nav a[data-view='sets']")
    page.wait_for_selector(".sets")
    page.remove_listener("dialog", note)
    found.left_with_no_changes_asked = bool(asked)
    _open_settings(page)


def _unload_prevented(page: Any) -> bool:
    return page.evaluate(
        """() => {
            const unload = new Event("beforeunload", { cancelable: true });
            window.dispatchEvent(unload);
            return unload.defaultPrevented;
        }"""
    )


def _unload(page: Any, engine: str, found: Seen) -> None:
    found.unload_prevented_with_no_changes = _unload_prevented(page)
    page.check(VIM)
    found.unload_prevented_with_changes = _unload_prevented(page)
    kinds: list[str] = []

    def agree(dialog: Any) -> None:
        kinds.append(dialog.type)
        dialog.accept()

    if engine == CHROMIUM:
        page.once("dialog", agree)
        page.reload()
        page.wait_for_selector(MAX_INTERVAL)
        found.unload_dialog = kinds[0] if kinds else ""
    else:
        page.click(RESET)


def _save_both(page: Any, workspace: Path, config_file: Path, found: Seen) -> None:
    page.check(VIM)
    page.fill(MAX_INTERVAL, "120")
    page.click(SAVE)
    page.wait_for_selector(f"{STATUS}:has-text('preferences saved in')")
    found.saved_says = page.locator(STATUS).inner_text()
    found.saved_preferences = _stored(workspace)
    found.saved_file = config_file.read_text()
    found.after_save = _state(page)
    found.focus_after_save = _focused(page)


def _one_store_refused(page: Any, workspace: Path, config_file: Path, found: Seen) -> None:
    """The browser logs the 422 of this save."""
    page.fill(REPS, "many")
    page.uncheck(TYPECHECK)
    page.click(SAVE)
    page.wait_for_selector(f"{STATUS}:has-text('config.toml not saved')")
    found.config_refused_says = page.locator(STATUS).inner_text()
    found.config_refused_ink = page.locator(f"{STATUS} .failed").evaluate(
        "line => getComputedStyle(line).color"
    )
    found.fail_ink = page.evaluate(
        """() => {
            const probe = document.createElement("span");
            probe.style.color = "var(--fail)";
            document.body.append(probe);
            const ink = getComputedStyle(probe).color;
            probe.remove();
            return ink;
        }"""
    )
    found.config_refused_preferences = _stored(workspace)
    found.config_refused_file = config_file.read_text()
    found.config_refused_state = _state(page)
    page.click(RESET)


def _preferences_fail(page: Any, config_file: Path, found: Seen) -> None:
    """The browser logs the 500 of this save."""
    page.route(
        "**/api/v1/preferences",
        lambda route: route.fulfill(status=500, json={"message": "no room"}),
    )
    page.check(TYPECHECK)
    page.fill(REPS, "11")
    page.click(SAVE)
    page.wait_for_selector(f"{STATUS}:has-text('preferences not saved')")
    found.preferences_failed_says = page.locator(STATUS).inner_text()
    found.preferences_failed_file = config_file.read_text()
    found.preferences_failed_state = _state(page)
    page.unroute("**/api/v1/preferences")
    page.click(RESET)


def _enter_saves(page: Any, config_file: Path, found: Seen) -> None:
    page.fill(REPS, "12")
    page.press(REPS, "Enter")
    page.wait_for_selector(f"{STATUS}:has-text('config.toml saved: bench.reps')")
    found.file_after_enter = config_file.read_text()
    found.focus_after_enter = _focused(page)


def _progress_db(page: Any, workspace: Path, config_file: Path, found: Seen) -> None:
    before = _stored(workspace)
    page.check(TYPECHECK)
    page.fill(PROGRESS_DB, "moved/other.db")
    page.click(SAVE)
    page.wait_for_selector(QUESTION)
    found.question_in_save = page.locator(QUESTION).inner_text()
    page.click(f"{SHEET} button:has-text('Cancel')")
    page.wait_for_selector(f"{STATUS}:has-text('not saved')")
    found.declined_says = page.locator(STATUS).inner_text()
    found.declined_preferences = {"same": _stored(workspace) == before}
    found.declined_file = config_file.read_text()
    found.declined_state = _state(page)
    page.click(SAVE)
    page.click(f"{SHEET} button:has-text('Change it')")
    page.wait_for_selector(f"{STATUS}:has-text('preferences saved in')")
    found.confirmed_preferences = _stored(workspace)
    found.confirmed_file = config_file.read_text()


def _status_bar_toggle(page: Any, workspace: Path, found: Seen) -> None:
    """The status bar's switch applies at once, and the form's checkbox follows it."""
    page.check(DARK)
    stored_vim = _stored(workspace)["vim"]
    page.click(VIM_TOGGLE)
    page.wait_for_function(
        "expected => document.querySelector('#pref-vim').checked === expected",
        arg=not stored_vim,
    )
    found.followed_toggle = _stored(workspace)["vim"] == (not stored_vim)
    found.toggle_kept_the_preview = page.evaluate(THEME_SHOWN)
    found.toggle_state = _state(page)
    page.click(RESET)


def _broken_file(page: Any, workspace: Path, config_file: Path, found: Seen) -> None:
    """A page already open reaches Settings: a load of the page itself needs a file that parses."""
    page.evaluate("location.hash = '#/sets'")
    page.wait_for_selector(".sets")
    config_file.write_text("this is not toml\n")
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector(".settings-column .state-error")
    found.broken_fields_disabled = page.is_disabled(REPS)
    page.set_checked(TYPECHECK, not page.is_checked(TYPECHECK))
    page.click(SAVE)
    page.wait_for_selector(f"{STATUS}:has-text('preferences saved in')")
    found.broken_says = page.locator(STATUS).inner_text()
    found.broken_saved_preferences = _stored(workspace)


def test_with_no_changes_save_is_disabled_and_reset_and_the_count_are_hidden(seen):
    assert seen.untouched == State(False, "", False, True)


def test_a_list_in_another_order_than_the_files_is_no_change(seen):
    assert seen.untouched.save_disabled


@pytest.mark.parametrize("width", ["wide", "narrow", "narrow_with_a_change", "smallest"])
def test_the_bar_stays_under_the_top_bar_while_the_page_scrolls(seen, width):
    bar = getattr(seen, f"bar_{width}")
    assert bar.top == bar.top_bar_bottom


@pytest.mark.parametrize("width", ["wide", "narrow"])
def test_the_bar_is_as_wide_as_the_window(seen, width):
    bar = getattr(seen, f"bar_{width}")
    assert (bar.left, bar.width) == (0, bar.window)


@pytest.mark.parametrize("width", ["wide", "narrow", "narrow_with_a_change", "smallest"])
def test_the_title_and_save_stay_on_screen(seen, width):
    bar = getattr(seen, f"bar_{width}")
    assert (bar.title_on_screen, bar.save_on_screen) == (True, True)


@pytest.mark.parametrize("width", ["wide", "narrow"])
def test_a_change_showing_does_not_move_save(seen, width):
    assert not getattr(seen, f"save_moved_{width}")


@pytest.mark.parametrize("width", ["wide", "smallest"])
def test_a_focused_field_stays_clear_of_the_bar(seen, width):
    assert getattr(seen, f"field_clear_{width}")


def test_one_change_shows_its_count_and_reset_and_enables_save(seen):
    assert seen.one_change == State(True, "1 change", True, False)


def test_a_change_to_each_store_counts_together(seen):
    assert seen.two_changes.count == "2 changes"


def test_a_changed_row_is_marked(seen):
    assert seen.row_marked


def test_an_untouched_row_is_not_marked(seen):
    assert not seen.untouched_row_marked


def test_a_preference_stages_until_save(seen):
    assert '"vim": true' not in seen.stored_while_staged


def test_a_config_key_stages_until_save(seen):
    assert seen.file_while_staged == CONFIG_TEXT


def test_the_theme_previews_while_unsaved(seen):
    assert seen.previewed == "dark"


def test_the_status_bar_shows_the_previewed_theme(seen):
    assert seen.status_bar_previewed == "theme dark"


def test_the_preview_counts_as_a_change(seen):
    assert seen.three_changes.count == "3 changes"


def test_reset_hides_itself_and_disables_save(seen):
    assert seen.after_reset == State(False, "", False, True)


def test_reset_undoes_a_preference(seen):
    assert not seen.vim_after_reset


def test_reset_undoes_a_config_key(seen):
    assert seen.interval_after_reset == "90"


def test_reset_puts_the_theme_back(seen):
    assert seen.theme_after_reset == "system"


def test_reset_says_so(seen):
    assert seen.reset_says == "changes undone"


def test_reset_leaves_the_focus_on_the_title(seen):
    assert seen.focus_after_reset == "settings-heading"


def test_leaving_with_changes_asks_first(seen):
    assert seen.question == "Settings has unsaved changes. Leave and lose them?"


def test_declining_keeps_the_view_and_the_changes(seen):
    assert seen.kept_after_declining == ("#/settings", True)


def test_agreeing_leaves(seen):
    assert seen.left_after_agreeing == "#/"


def test_agreeing_drops_the_changes(seen):
    assert not seen.vim_after_coming_back


def test_agreeing_drops_the_previewed_theme(seen):
    assert seen.theme_after_leaving == "system"


def test_leaving_with_no_changes_does_not_ask(seen):
    assert not seen.left_with_no_changes_asked


def test_unloading_with_no_changes_does_not_ask(seen):
    assert not seen.unload_prevented_with_no_changes


def test_unloading_with_changes_asks(seen):
    assert seen.unload_prevented_with_changes


def test_the_browser_shows_its_own_question_on_a_reload(seen, engine):
    if engine != CHROMIUM:
        pytest.skip("the real dialog is read on Chromium, the job's engine")
    assert seen.unload_dialog == "beforeunload"


def test_save_says_when_each_store_applies(seen):
    assert "config.toml saved: schedule.max_interval_days applies for reviews" in seen.saved_says


def test_save_says_the_preferences_are_stored(seen):
    assert "preferences saved in .cs/serve/preferences.json" in seen.saved_says


def test_save_writes_the_preferences(seen):
    assert seen.saved_preferences["vim"] is True


def test_save_writes_the_config_and_keeps_its_comments(seen):
    assert seen.saved_file == CONFIG_TEXT.replace("= 90 #", "= 120 #")


def test_after_a_save_nothing_is_left_to_save(seen):
    assert seen.after_save == State(False, "", False, True)


def test_a_save_that_disables_save_leaves_the_focus_on_the_title(seen):
    assert seen.focus_after_save == "settings-heading"


def test_a_refused_config_says_which_store(seen):
    assert f"config.toml not saved: {REFUSED_KEY}" in seen.config_refused_says


def test_the_store_that_failed_shows_in_the_fail_ink(seen):
    assert seen.config_refused_ink == seen.fail_ink


def test_a_refused_config_says_the_preferences_were_saved(seen):
    assert "preferences saved in" in seen.config_refused_says


def test_a_refused_config_still_writes_the_preferences(seen):
    assert seen.config_refused_preferences["typecheck"] is False


def test_a_refused_config_writes_nothing_to_the_file(seen):
    assert "reps = 9" in seen.config_refused_file


def test_a_refused_config_stays_unsaved_alone(seen):
    assert seen.config_refused_state == State(True, "1 change", True, False)


def test_a_failed_preferences_save_says_which_store(seen):
    assert "preferences not saved" in seen.preferences_failed_says


def test_a_failed_preferences_save_says_the_config_was_saved(seen):
    assert "config.toml saved: bench.reps applies" in seen.preferences_failed_says


def test_a_failed_preferences_save_still_writes_the_config(seen):
    assert "reps = 11" in seen.preferences_failed_file


def test_a_failed_preferences_save_stays_unsaved_alone(seen):
    assert seen.preferences_failed_state == State(True, "1 change", True, False)


def test_enter_in_a_text_field_saves(seen):
    assert "reps = 12" in seen.file_after_enter


def test_enter_leaves_the_focus_in_the_field(seen):
    assert seen.focus_after_enter == "config-bench-reps"


def test_a_new_database_path_asks_inside_save(seen):
    assert "does not move your data" in seen.question_in_save


def test_declining_the_question_saves_neither_store(seen):
    assert (seen.declined_says, seen.declined_preferences["same"]) == ("not saved", True)


def test_declining_the_question_writes_nothing_to_the_file(seen):
    assert "moved" not in seen.declined_file


def test_declining_the_question_keeps_the_changes_staged(seen):
    assert seen.declined_state == State(True, "2 changes", True, False)


def test_confirming_the_question_writes_the_path(seen):
    assert 'progress_db = "moved/other.db"' in seen.confirmed_file


def test_confirming_the_question_writes_the_preferences(seen):
    assert seen.confirmed_preferences["typecheck"] is True


def test_the_status_bar_switch_still_applies_at_once_and_the_form_follows(seen):
    assert seen.followed_toggle


def test_the_status_bar_switch_leaves_a_previewed_theme_alone(seen):
    assert seen.toggle_kept_the_preview == "dark"


def test_the_status_bar_switch_counts_no_change_of_its_own(seen):
    assert seen.toggle_state.count == "1 change"


def test_a_file_that_does_not_parse_disables_its_fields(seen):
    assert seen.broken_fields_disabled


def test_a_file_that_does_not_parse_leaves_the_preferences_savable(seen):
    assert "preferences saved in" in seen.broken_says


def test_the_page_logs_no_error_before_the_failures_it_provokes(seen):
    assert seen.errors_before_the_failures == []
