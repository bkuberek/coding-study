"""The Settings view's form of `config.toml` in a real browser
(docs/specs/web-ui.md#settings-view), in each engine of `tests/browsers.py`: every key shows its
value and its default, a saved change reaches the file with the user's comments kept, a value the
CLI refuses is refused by name and writes nothing, and an empty field returns a key to its default.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.adapters.toml_config import CONFIG_KEYS
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
CONFIG_TEXT = """\
# My settings: keep this line
[schedule]
max_interval_days = 90 # three months

[bench]
reps = 9
"""
MAX_INTERVAL = "#config-schedule-max_interval_days"
REPS = "#config-bench-reps"
MEMORY = "#config-bench-memory"
TRACKS = "#config-next-tracks"
RESERVED = "#config-done-auto_commit"
PROGRESS_DB = "#config-progress_db"
SHEET = "dialog.sheet[open]"
QUESTION = f"{SHEET} .question"
SAVE = "form:has(#config-bench-reps) button[type=submit]"
STATUS = "form:has(#config-bench-reps) p[role=status]"


@dataclass
class Seen:
    labels: list[str] = field(default_factory=list[str])
    value: str = ""
    help_text: str = ""
    headings: list[str] = field(default_factory=list[str])
    reserved_disabled: bool = False
    command_strip: str = ""
    saved_file: str = ""
    saved_note: str = ""
    focus_on_save: bool = False
    refusal: str = ""
    refused_file: str = ""
    emptied_file: str = ""
    emptied_shows_default: str = ""
    question: str = ""
    file_after_declining: str = ""
    note_after_declining: str = ""
    file_after_confirming: str = ""
    database_kept: bool = False
    logged: list[str] = field(default_factory=list[str])
    errors_before_the_refusal: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"config-{engine}") / "workspace"))


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
def seen(engine: str, server: RunningServer, config_file: Path, workspace: Path) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), found.logged)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.evaluate("location.hash = '#/settings'")
        page.wait_for_selector(MAX_INTERVAL)
        _read_the_form(page, found)
        _save_a_change(page, config_file, found)
        found.errors_before_the_refusal = list(found.logged)
        _refuse_a_value(page, config_file, found)
        _empty_a_field(page, config_file, found)
        _a_new_database_path_asks_first(page, config_file, workspace, found)
        browser.close()
    return found


def _read_the_form(page: Any, found: Seen) -> None:
    found.labels = page.locator(".config-key > label").all_inner_texts()
    found.value = page.input_value(MAX_INTERVAL)
    found.help_text = page.locator(f"{MAX_INTERVAL} ~ p").inner_text()
    found.headings = page.locator(".settings h2").all_inner_texts()
    found.reserved_disabled = page.is_disabled(RESERVED)
    found.command_strip = page.locator(".command-text").inner_text()


def _saved(page: Any) -> str:
    page.wait_for_selector(f"{STATUS}:has-text('saved')")
    return page.locator(STATUS).inner_text()


def _save_a_change(page: Any, config_file: Path, found: Seen) -> None:
    page.fill(MAX_INTERVAL, "120")
    page.click(SAVE)
    found.saved_note = _saved(page)
    found.saved_file = config_file.read_text()
    found.focus_on_save = page.evaluate("() => document.activeElement?.type === 'submit'")


def _refuse_a_value(page: Any, config_file: Path, found: Seen) -> None:
    """The browser logs the 422 of this save."""
    page.fill(REPS, "many")
    page.click(SAVE)
    page.wait_for_selector(f"{STATUS}:has-text('error')")
    found.refusal = page.locator(STATUS).inner_text()
    found.refused_file = config_file.read_text()


def _empty_a_field(page: Any, config_file: Path, found: Seen) -> None:
    page.fill(REPS, "")
    page.click(SAVE)
    _saved(page)
    found.emptied_file = config_file.read_text()
    found.emptied_shows_default = page.input_value(REPS)


def _a_new_database_path_asks_first(
    page: Any, config_file: Path, workspace: Path, found: Seen
) -> None:
    database = workspace / "progress.db"
    database.write_bytes(database.read_bytes() if database.exists() else b"")
    kept = database.read_bytes()
    page.fill(PROGRESS_DB, "moved/other.db")
    page.click(SAVE)
    page.wait_for_selector(QUESTION)
    found.question = page.locator(QUESTION).inner_text()
    page.click(f"{SHEET} button:has-text('Cancel')")
    page.wait_for_selector(f"{STATUS}:has-text('not saved')")
    found.file_after_declining = config_file.read_text()
    found.note_after_declining = page.locator(STATUS).inner_text()
    page.click(SAVE)
    page.click(f"{SHEET} button:has-text('Change it')")
    page.wait_for_selector(f"{STATUS}:has-text('saved:')")
    found.file_after_confirming = config_file.read_text()
    found.database_kept = database.read_bytes() == kept


def test_the_form_shows_every_key_of_the_file(seen):
    assert seen.labels == [key.name for key in CONFIG_KEYS]


def test_a_key_shows_its_value(seen):
    assert seen.value == "90"


def test_a_key_shows_its_default(seen):
    assert "Default: 180." in seen.help_text


def test_a_review_interval_says_dates_already_set_do_not_move(seen):
    assert "dates already set do not move" in seen.help_text


def test_the_page_tells_the_workspace_from_every_workspace(seen):
    assert seen.headings == ["THIS WORKSPACE", "ALL YOUR WORKSPACES"]


def test_the_reserved_key_cannot_be_changed(seen):
    assert seen.reserved_disabled


def test_the_command_strip_shows_the_command_the_form_mirrors(seen):
    assert seen.command_strip == "cstudy config edit"


def test_a_change_reaches_the_file_and_keeps_its_comments(seen):
    assert seen.saved_file == CONFIG_TEXT.replace("= 90 #", "= 120 #")


def test_the_page_says_when_a_change_applies(seen):
    assert "schedule.max_interval_days applies for reviews scheduled" in seen.saved_note


def test_the_focus_stays_on_save(seen):
    assert seen.focus_on_save


def test_a_value_the_cli_refuses_is_refused_by_its_key(seen):
    assert seen.refusal == "error: bench.reps: expected a positive integer"


def test_a_refused_value_writes_nothing(seen):
    assert "reps = 9" in seen.refused_file


def test_an_empty_field_removes_the_key(seen):
    assert "reps" not in seen.emptied_file


def test_an_empty_field_shows_the_default_again(seen):
    assert seen.emptied_shows_default == "7"


def test_a_new_database_path_says_the_data_does_not_move(seen):
    assert "does not move your data" in seen.question


def test_a_new_database_path_says_whether_a_database_is_there(seen):
    assert "No database exists at moved/other.db" in seen.question


def test_declining_writes_nothing(seen):
    assert (seen.note_after_declining, "moved" in seen.file_after_declining) == ("not saved", False)


def test_confirming_writes_the_path(seen):
    assert 'progress_db = "moved/other.db"' in seen.file_after_confirming


def test_confirming_leaves_the_old_database_where_it_is(seen):
    assert seen.database_kept


def test_the_page_logs_no_error_under_its_content_security_policy(seen):
    assert seen.errors_before_the_refusal == []
