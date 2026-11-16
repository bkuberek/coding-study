"""The Settings view's Profile section in a real browser (docs/specs/web-ui.md#settings-view), in
each engine of `tests/browsers.py`: roles and domains stage as checkboxes and reach `config.toml`
(a group with every box unchecked is refused in the page, tied to its message), languages stage an
add or a removal, name the command Save runs and reach the marker through `POST /api/v1/languages`
with the folder kept, the last language cannot be unchecked, a workspace that chose none reads `all
six (none chosen)`, and `edit profile` leads to `#/settings/profile`, which a reload and a new tab
land on too.

The workspaces are made by `cstudy init` or bare ones, nothing is run. Playwright and its engines
are set up as `tests/browsers.py` says; without them the test is skipped.
"""

import json
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coding_study.domain.taxonomy import DOMAINS, PROFILE_JOB_ROLES
from tests.browsers import launched, watched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server, served_environment

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
SAVE = ".settings-bar button[type=submit]"
STATUS = ".settings-bar p[role=status]"
COUNT = ".settings-count"
RESET = ".settings-bar button:has-text('Reset')"
COMMANDS = ".profile-commands"
ROLE = "#config-profile-job_roles"
DOMAIN = "#config-profile-domains"
LANGUAGE = "#profile-lang-"
KEPT_ROLE = "backend"
KEPT_DOMAINS = ("backend", "security")
LISTED = ".listing:not([aria-busy]) table.problems"


def _init(workspace: Path, *languages: str) -> Path:
    flags = [flag for language in languages for flag in ("--lang", language)]
    subprocess.run(
        [sys.executable, "-m", "coding_study", "init", str(workspace), *flags],
        env=served_environment(workspace),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return workspace


def _lang_list(workspace: Path) -> str:
    done = subprocess.run(
        [sys.executable, "-m", "coding_study", "lang", "list"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _marker(workspace: Path) -> dict[str, Any]:
    return tomllib.loads((workspace / ".cs" / "workspace.toml").read_text())


def _open_settings(page: Any) -> None:
    page.evaluate("location.hash = '#/settings'")
    page.wait_for_selector(f"{ROLE}-{KEPT_ROLE}")
    page.wait_for_selector(f"{LANGUAGE}python")


def _status(page: Any, text: str) -> str:
    page.wait_for_selector(f"{STATUS}:has-text('{text}')")
    return page.locator(STATUS).inner_text()


def _checked(page: Any, selector: str) -> list[str]:
    return page.locator(f"{selector} input[type=checkbox]:checked").evaluate_all(
        "boxes => boxes.map(box => box.value)"
    )


@dataclass
class Edited:
    """Roles and domains: what the section drew, saved and refused."""

    headings: list[str] = field(default_factory=list[str])
    roles_drawn: list[str] = field(default_factory=list[str])
    domains_drawn: list[str] = field(default_factory=list[str])
    role_note: str = ""
    domain_note: str = ""
    where: str = ""
    changes_text: str = ""
    saved_status: str = ""
    config_after_save: dict[str, Any] = field(default_factory=dict[str, Any])
    marker_kept: bool = False
    reloaded_roles: list[str] = field(default_factory=list[str])
    reloaded_domains: list[str] = field(default_factory=list[str])
    chip_counts: str = ""
    cli_counts: str = ""
    refusal: str = ""
    config_after_refusal: dict[str, Any] = field(default_factory=dict[str, Any])
    roles_after_refusal: list[str] = field(default_factory=list[str])
    reset_status: str = ""
    roles_after_reset: list[str] = field(default_factory=list[str])
    edit_hash: str = ""
    edit_focus: str = ""
    reload_hash: str = ""
    reload_focus: str = ""
    tab_hash: str = ""
    tab_focus: str = ""
    role_message: str = ""
    role_message_visible: bool = False
    role_described_by: str | None = None
    domain_message_visible: bool = True
    role_message_after_check: bool = True
    role_described_after_check: str | None = None
    refusal_focus: str = ""
    count_after_refusal: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def narrowed(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _init(tmp_path_factory.mktemp(f"profile-roles-{engine}") / "workspace", "python", "go")


@pytest.fixture(scope="module")
def narrowed_server(narrowed: Path) -> Iterator[RunningServer]:
    with running_server(narrowed) as running:
        yield running


def _cli_counts(workspace: Path) -> str:
    done = subprocess.run(
        [sys.executable, "-m", "coding_study", "list", "--json"],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    listing = json.loads(done.stdout)
    shown = len(listing["entries"])
    return f"{shown} of {shown + listing['profile']['hidden']['problems']}"


@pytest.fixture(scope="module")
def edited(engine: str, narrowed: Path, narrowed_server: RunningServer) -> Edited:
    seen = Edited()
    config = narrowed.parent / "config" / "coding-study" / "config.toml"
    marker_before = (narrowed / ".cs" / "workspace.toml").read_text()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(narrowed_server.login_url)
        page.wait_for_selector(f"{LISTED} tbody tr")
        _open_settings(page)
        seen.headings = page.locator(".settings-profile h2").all_inner_texts()
        seen.roles_drawn = _checked(page, ROLE)
        seen.domains_drawn = _checked(page, DOMAIN)
        seen.role_note = page.locator(f"{ROLE} p").nth(1).inner_text()
        seen.domain_note = page.locator(f"{DOMAIN} p").nth(1).inner_text()
        seen.where = page.locator(f"{ROLE} p").first.inner_text()
        for role in PROFILE_JOB_ROLES:
            if role != KEPT_ROLE:
                page.uncheck(f"{ROLE}-{role}")
        for domain in DOMAINS:
            if domain not in KEPT_DOMAINS:
                page.uncheck(f"{DOMAIN}-{domain}")
        seen.changes_text = page.locator(COUNT).inner_text()
        page.click(SAVE)
        seen.saved_status = _status(page, "config.toml saved")
        seen.config_after_save = tomllib.loads(config.read_text())
        seen.marker_kept = (narrowed / ".cs" / "workspace.toml").read_text() == marker_before
        page.reload()
        page.wait_for_selector(f"{ROLE}-{KEPT_ROLE}")
        seen.reloaded_roles = _checked(page, ROLE)
        seen.reloaded_domains = _checked(page, DOMAIN)
        # The Problems view uses the saved profile, and `edit profile` leads back to the section.
        page.evaluate("location.hash = '#/'")
        page.wait_for_selector(f"{LISTED} tbody tr")
        page.wait_for_selector("#chip-profile")
        seen.chip_counts = page.locator(".filter-summary .filter-count").inner_text()
        seen.cli_counts = _cli_counts(narrowed)
        page.click(".filter-summary a.edit-profile")
        page.wait_for_selector("#profile-heading")
        page.wait_for_selector("#profile-heading:focus")
        seen.edit_hash = page.evaluate("location.hash")
        seen.edit_focus = page.evaluate("document.activeElement?.id")
        # The route is the landing: a reload and a new tab open on the section too.
        page.reload()
        page.wait_for_selector("#profile-heading:focus")
        seen.reload_hash = page.evaluate("location.hash")
        seen.reload_focus = page.evaluate("document.activeElement?.id")
        tab = browser.new_context(storage_state=page.context.storage_state()).new_page()
        tab.set_default_timeout(WAIT_MS)
        tab.goto(page.url.split("#")[0] + "#/settings/profile")
        tab.wait_for_selector("#profile-heading")
        tab.bring_to_front()
        tab.wait_for_selector("#profile-heading:focus")
        seen.tab_hash = tab.evaluate("location.hash")
        seen.tab_focus = tab.evaluate("document.activeElement?.id")
        tab.close()
        # A group with every box unchecked is refused in the page, before anything is written.
        page.wait_for_selector(f"{ROLE}-{KEPT_ROLE}")
        page.uncheck(f"{ROLE}-{KEPT_ROLE}")
        page.click(SAVE)
        seen.refusal = _status(page, "not saved")
        seen.role_message = page.locator(f"{ROLE}-error").inner_text()
        seen.role_message_visible = page.locator(f"{ROLE}-error").is_visible()
        seen.role_described_by = page.get_attribute(ROLE, "aria-describedby")
        seen.domain_message_visible = page.locator(f"{DOMAIN}-error").is_visible()
        seen.refusal_focus = page.evaluate("document.activeElement?.id")
        seen.count_after_refusal = page.locator(COUNT).inner_text()
        seen.config_after_refusal = tomllib.loads(config.read_text())
        seen.roles_after_refusal = _checked(page, ROLE)
        page.check(f"{ROLE}-{KEPT_ROLE}")
        seen.role_message_after_check = page.locator(f"{ROLE}-error").is_visible()
        seen.role_described_after_check = page.get_attribute(ROLE, "aria-describedby")
        page.uncheck(f"{ROLE}-{KEPT_ROLE}")
        page.click(RESET)
        seen.reset_status = _status(page, "changes undone")
        seen.roles_after_reset = _checked(page, ROLE)
        browser.close()
    return seen


def test_the_profile_heads_the_page_with_its_groups(edited):
    assert edited.headings == ["profile"]
    assert edited.roles_drawn == list(PROFILE_JOB_ROLES)
    assert edited.domains_drawn == list(DOMAINS)


def test_each_group_says_where_it_is_stored_and_its_note(edited):
    assert edited.where == "all your workspaces: config.toml · profile.job_roles"
    assert edited.role_note == "Problems for any engineer (general) always show."
    assert edited.domain_note == "Keep algorithms for the data structures and algorithms problems."


def test_unchecking_boxes_stages_a_change_per_key(edited):
    assert edited.changes_text == "2 changes"


def test_a_save_writes_the_lists_to_config_toml_and_leaves_the_marker(edited):
    assert edited.saved_status.startswith("config.toml saved")
    assert edited.config_after_save["profile"] == {
        "job_roles": [KEPT_ROLE],
        "domains": [domain for domain in DOMAINS if domain in KEPT_DOMAINS],
    }
    assert edited.marker_kept


def test_the_saved_lists_come_back_after_a_reload(edited):
    assert edited.reloaded_roles == [KEPT_ROLE]
    assert edited.reloaded_domains == [domain for domain in DOMAINS if domain in KEPT_DOMAINS]


def test_the_problems_view_after_the_save_counts_as_the_command_does(edited):
    assert edited.chip_counts == edited.cli_counts


def test_edit_profile_leads_to_the_profile_route_and_focuses_its_heading(edited):
    assert (edited.edit_hash, edited.edit_focus) == ("#/settings/profile", "profile-heading")


def test_a_reload_and_a_new_tab_land_on_the_profile_heading_too(edited):
    assert (edited.reload_hash, edited.reload_focus) == ("#/settings/profile", "profile-heading")
    assert (edited.tab_hash, edited.tab_focus) == ("#/settings/profile", "profile-heading")


def test_a_group_with_every_box_unchecked_is_refused_in_the_page_next_to_the_group(edited):
    assert edited.refusal.startswith("not saved")
    assert edited.role_message == "Choose at least one job role."
    assert edited.role_message_visible
    assert edited.role_described_by == "config-profile-job_roles-error"
    assert not edited.domain_message_visible
    assert edited.refusal_focus == f"config-profile-job_roles-{PROFILE_JOB_ROLES[0]}"


def test_a_refused_group_keeps_the_change_staged_and_writes_nothing(edited):
    assert edited.count_after_refusal == "1 change"
    assert edited.config_after_refusal == edited.config_after_save
    assert edited.roles_after_refusal == []


def test_checking_a_box_answers_the_message(edited):
    assert not edited.role_message_after_check
    assert edited.role_described_after_check is None


def test_reset_draws_the_saved_lists_again(edited):
    assert edited.reset_status == "changes undone"
    assert edited.roles_after_reset == [KEPT_ROLE]


def test_the_section_logs_no_error_or_warning_but_the_refusal(edited):
    assert edited.errors == []


@dataclass
class Languaged:
    """Languages: what the boxes staged, Save wrote and the workspace holds."""

    python_disabled: bool = False
    python_described: str = ""
    note: str = ""
    legend: str = ""
    typescript_enabled_after_check: bool = False
    commands_add: str = ""
    changes_add: str = ""
    add_status: str = ""
    health_link: str = ""
    marker_after_add: list[str] = field(default_factory=list[str])
    typescript_folder_written: bool = False
    list_after_add: str = ""
    chip_after_add: str = ""
    commands_remove: str = ""
    remove_status: str = ""
    marker_after_remove: list[str] = field(default_factory=list[str])
    typescript_folder_kept: bool = False
    list_after_remove: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def python_only(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _init(tmp_path_factory.mktemp(f"profile-langs-{engine}") / "workspace", "python")


@pytest.fixture(scope="module")
def python_server(python_only: Path) -> Iterator[RunningServer]:
    with running_server(python_only) as running:
        yield running


@pytest.fixture(scope="module")
def languaged(engine: str, python_only: Path, python_server: RunningServer) -> Languaged:
    seen = Languaged()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(python_server.login_url)
        page.wait_for_selector(f"{LISTED} tbody tr")
        _open_settings(page)
        seen.python_disabled = page.is_disabled(f"{LANGUAGE}python")
        described = page.get_attribute(f"{LANGUAGE}python", "aria-describedby") or ""
        seen.python_described = page.locator(f"#{described}").inner_text() if described else ""
        seen.note = page.locator("#profile-languages-note").inner_text()
        seen.legend = page.locator("#profile-languages legend").inner_text()
        page.check(f"{LANGUAGE}typescript")
        seen.typescript_enabled_after_check = not page.is_disabled(f"{LANGUAGE}python")
        seen.commands_add = page.locator(COMMANDS).inner_text()
        seen.changes_add = page.locator(COUNT).inner_text()
        page.click(SAVE)
        seen.add_status = _status(page, "languages saved")
        seen.health_link = page.locator(f"{STATUS} a").get_attribute("href") or ""
        seen.marker_after_add = _marker(python_only)["languages"]
        seen.typescript_folder_written = (python_only / "typescript").is_dir()
        seen.list_after_add = _lang_list(python_only)
        page.evaluate("location.hash = '#/'")
        page.wait_for_selector(f"{LISTED} tbody tr")
        page.wait_for_selector("#chip-profile")
        seen.chip_after_add = " ".join(page.locator("#chip-profile").inner_text().split())
        _open_settings(page)
        page.uncheck(f"{LANGUAGE}typescript")
        seen.commands_remove = page.locator(COMMANDS).inner_text()
        page.click(SAVE)
        # A removal asks first; keeping the folder is the default.
        page.click("dialog.sheet[open] button:has-text('Keep the folder')")
        seen.remove_status = _status(page, "removed")
        seen.marker_after_remove = _marker(python_only)["languages"]
        seen.typescript_folder_kept = (python_only / "typescript").is_dir()
        seen.list_after_remove = _lang_list(python_only)
        browser.close()
    return seen


def test_the_only_language_is_disabled_with_its_note_tied_by_describedby(languaged):
    assert languaged.python_disabled
    assert languaged.python_described == "a workspace needs at least one language"
    assert languaged.note == "a workspace needs at least one language"


def test_a_workspace_that_chose_its_languages_does_not_say_all_six(languaged):
    assert "all six" not in languaged.legend


def test_checking_a_second_language_frees_the_first_and_names_the_command(languaged):
    assert languaged.typescript_enabled_after_check
    assert languaged.commands_add == "Save runs cstudy lang add typescript"
    assert languaged.changes_add == "1 change"


def test_saving_an_add_says_what_was_added_and_links_to_health(languaged):
    assert languaged.add_status == (
        "languages saved in .cs/workspace.toml: added typescript "
        "· next: Fix in Health installs its toolchain files"
    )
    assert languaged.health_link == "#/health"


def test_the_marker_and_the_folder_follow_the_add_as_the_command_agrees(languaged):
    assert languaged.marker_after_add == ["python", "typescript"]
    assert languaged.typescript_folder_written
    assert "python, typescript" in languaged.list_after_add


def test_the_views_drawn_after_the_save_use_the_new_profile(languaged):
    assert "your profile: python, typescript" in languaged.chip_after_add


def test_removing_a_language_names_its_command_and_keeps_the_folder(languaged):
    assert languaged.commands_remove == "Save runs cstudy lang remove typescript"
    assert languaged.remove_status.endswith("typescript removed: typescript/ stays on disk")
    assert languaged.marker_after_remove == ["python"]
    assert languaged.typescript_folder_kept
    assert "typescript" not in languaged.list_after_remove.splitlines()[0]


def test_the_languages_log_no_error_or_warning(languaged):
    assert languaged.errors == []


@pytest.fixture(scope="module")
def unchosen(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"profile-all-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def unchosen_server(unchosen: Path) -> Iterator[RunningServer]:
    with running_server(unchosen) as running:
        yield running


@dataclass
class AllSix:
    legend: str = ""
    checked: int = 0
    legend_after_uncheck: str = ""
    legend_after_recheck: str = ""
    last_disabled: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def all_six(engine: str, unchosen_server: RunningServer) -> AllSix:
    seen = AllSix()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(viewport={"width": 1440, "height": 900}), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(unchosen_server.login_url)
        page.wait_for_selector(f"{LISTED} tbody tr")
        _open_settings(page)
        legend = page.locator("#profile-languages .profile-chosen")
        seen.legend = legend.inner_text()
        seen.checked = len(_checked(page, "#profile-languages"))
        page.uncheck(f"{LANGUAGE}rust")
        seen.legend_after_uncheck = "shown" if legend.is_visible() else "hidden"
        page.check(f"{LANGUAGE}rust")
        seen.legend_after_recheck = "shown" if legend.is_visible() else "hidden"
        for language in ("typescript", "java", "kotlin", "go", "rust"):
            page.uncheck(f"{LANGUAGE}{language}")
        seen.last_disabled = page.locator("#profile-languages input:disabled").evaluate_all(
            "boxes => boxes.map(box => box.value)"
        )
        browser.close()
    return seen


def test_a_marker_without_languages_checks_all_six_and_says_none_was_chosen(all_six):
    assert (all_six.legend, all_six.checked) == ("all six (none chosen)", 6)


def test_the_words_go_once_a_box_is_unchecked_and_return_with_it(all_six):
    assert (all_six.legend_after_uncheck, all_six.legend_after_recheck) == ("hidden", "shown")


def test_the_last_checked_language_is_the_one_that_is_disabled(all_six):
    assert all_six.last_disabled == ["python"]


def test_the_unchosen_workspace_logs_no_error_or_warning(all_six):
    assert all_six.errors == []
