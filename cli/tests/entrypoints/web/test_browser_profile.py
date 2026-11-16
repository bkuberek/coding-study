"""The learner profile in the Problems, Guides and Mock views and the Start dialog, in a real
browser, in each engine of `tests/browsers.py` (docs/specs/web-ui.md#filter-component): the profile
is the default filter and shows one quiet chip with its counts (`120 of 400 · your profile: python,
go · backend`), a button named `Show all 400: …` that widens in the route, followed by `edit
profile`; the rows are those of the command above the view; widening survives a reload and the
route's query; the Start dialog disables a language the workspace does not list. A profile that
hides nothing shows no chip.

The workspaces are bare ones over the catalog of the checkout, nothing is run. Playwright and its
engines are set up as `tests/browsers.py` says; without them the test is skipped.
"""

import json
import re
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
CLOSE = " \N{MULTIPLICATION SIGN}"
LANGUAGES = ("python", "go")
ROLE = "backend"
DOMAINS = ("security", "backend")
PROFILE = f"{', '.join(LANGUAGES)} · {ROLE} · {', '.join(DOMAINS)}"
LABELS = f"{ROLE} · {', '.join(DOMAINS)}"
WIDENED = ["language: any", "role: any", "domain: any"]
LABEL_CHIPS = ["role: any", "domain: any"]
LISTED = ".listing:not([aria-busy]) table.problems"
SLUGS = "table.problems tbody tr .slug"
COMMAND = ".command-text"
CHIP = "#chip-profile"
EDIT = ".filter-summary a.edit-profile"
COUNT = ".filter-summary .filter-count"
GUIDE_ROWS = "ul.guide-list > li"
PATH_CARDS = "ul.path-cards > li"
MOCK_FORM = "form.mock-form"
MOCK_COMMAND_IS = (
    "expected => document.querySelector('form.mock-form .cmd')?.textContent === expected"
)
COMMAND_IS = "expected => document.querySelector('.command-text')?.textContent === expected"
FOCUSED = "document.activeElement?.id"


@dataclass
class Visit:
    """What the CLI listed, and what the browser showed, for the narrowed profile."""

    cli_shown: int = 0
    cli_hidden: int = 0
    cli_widened: int = 0
    cli_guides: int = 0
    cli_guides_hidden: int = 0
    cli_guides_wide: int = 0
    cli_paths: int = 0
    cli_paths_hidden: int = 0
    rust_slug: str = ""
    # The Problems view.
    chip_text: str = ""
    chip_name: str = ""
    chip_tag: str = ""
    edit_href: str = ""
    count: str = ""
    command: str = ""
    lang_options: list[str] = field(default_factory=list[str])
    role_options: list[str] = field(default_factory=list[str])
    domain_options: list[str] = field(default_factory=list[str])
    rows: int = 0
    tab_reaches_chip: bool = False
    fragment_widened: str = ""
    command_widened: str = ""
    rows_widened: int = 0
    chip_after_widening: int = -1
    widened_chips: list[str] = field(default_factory=list[str])
    focus_after_widening: str = ""
    reloaded_fragment: str = ""
    reloaded_rows: int = 0
    reloaded_widened_chips: list[str] = field(default_factory=list[str])
    back_fragment: str = ""
    command_after_removal: str = ""
    chip_after_removal: str = ""
    lang_after_choosing_any: str = ""
    fragment_after_choosing_any: str = ""
    fragment_after_clear: str = ""
    chip_after_clear: int = 0
    # The Guides view.
    guides_chip_text: str = ""
    guides_chip_name: str = ""
    guides_rows: int = 0
    guides_command: str = ""
    guides_widened_fragment: str = ""
    guides_widened_command: str = ""
    guides_widened_rows: int = 0
    guides_widened_chips: list[str] = field(default_factory=list[str])
    guides_chip_after: int = -1
    # The Mock view.
    mock_chip_text: str = ""
    mock_chip_name: str = ""
    mock_command: str = ""
    mock_command_widened: str = ""
    mock_widened_chips: list[str] = field(default_factory=list[str])
    mock_chip_after: int = -1
    mock_languages: list[str] = field(default_factory=list[str])
    # The Start dialog.
    start_options: list[str] = field(default_factory=list[str])
    start_disabled: list[str] = field(default_factory=list[str])
    start_language: str = ""
    start_note: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def narrowed(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A workspace that practices python and go and prepares for the backend role."""
    workspace = Path(mark_workspace(tmp_path_factory.mktemp(f"profile-{engine}") / "workspace"))
    marker = workspace / ".cs" / "workspace.toml"
    marker.write_text(marker.read_text() + f"languages = {json.dumps(list(LANGUAGES))}\n")
    config = workspace.parent / "config" / "coding-study" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        f"[profile]\njob_roles = {json.dumps([ROLE])}\ndomains = {json.dumps(list(DOMAINS))}\n"
    )
    return workspace


@pytest.fixture(scope="module")
def plain(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A workspace whose profile narrows nothing."""
    return Path(mark_workspace(tmp_path_factory.mktemp(f"plain-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(narrowed: Path) -> Iterator[RunningServer]:
    with running_server(narrowed) as running:
        yield running


@pytest.fixture(scope="module")
def plain_server(plain: Path) -> Iterator[RunningServer]:
    with running_server(plain) as running:
        yield running


def _cstudy(workspace: Path, *arguments: str) -> Any:
    """The JSON document of a `cstudy` command run as the server runs, in the same checkout."""
    done = subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments, "--json"],
        env=served_environment(workspace),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)


def _read_the_cli(workspace: Path, seen: Visit) -> None:
    listing = _cstudy(workspace, "list")
    seen.cli_shown = len(listing["entries"])
    seen.cli_hidden = listing["profile"]["hidden"]["problems"]
    wide = _cstudy(workspace, "list", "--widen", "all")
    seen.cli_widened = len(wide["entries"])
    guides = _cstudy(workspace, "learn")
    seen.cli_guides = len(guides["guides"])
    seen.cli_guides_hidden = guides["profile"]["hidden"]["guides"]
    seen.cli_paths = len(guides["paths"])
    seen.cli_paths_hidden = guides["profile"]["hidden"]["paths"]
    seen.cli_guides_wide = len(_cstudy(workspace, "learn", "--widen", "all")["guides"])
    seen.rust_slug = next(
        entry["slug"]
        for entry in wide["entries"]
        if "rust" in entry["languages"] and "python" in entry["languages"]
    )


def _words(text: str) -> str:
    """`text` with its line breaks, which a chip's flex items make, as spaces."""
    return " ".join(text.split())


def _chips(page: Any) -> list[str]:
    return [_words(text) for text in page.locator(".filter-summary .filter-chip").all_inner_texts()]


def _wait_for_command(page: Any, command: str) -> None:
    page.wait_for_function(COMMAND_IS, arg=command)


def _problems(page: Any, seen: Visit) -> None:
    page.wait_for_selector(f"{LISTED} tbody tr")
    page.wait_for_selector(CHIP)
    seen.chip_text = _words(page.locator(CHIP).inner_text())
    seen.chip_name = page.locator(CHIP).get_attribute("aria-label") or ""
    seen.chip_tag = page.locator(CHIP).evaluate("element => element.tagName")
    seen.edit_href = page.locator(EDIT).get_attribute("href") or ""
    seen.count = page.locator(COUNT).inner_text()
    seen.command = page.locator(COMMAND).inner_text()
    seen.rows = page.locator(SLUGS).count()
    for key, attribute in (
        ("lang", "lang_options"),
        ("role", "role_options"),
        ("domain", "domain_options"),
    ):
        options = page.locator(f"#filter-{key} option").all_text_contents()
        setattr(seen, attribute, options[:3])
    page.focus("#filter-search")
    for _ in range(12):
        page.keyboard.press("Tab")
        if page.evaluate(FOCUSED) == "chip-profile":
            seen.tab_reaches_chip = True
            break


def _widen_by_the_chip(page: Any, seen: Visit) -> None:
    page.click(CHIP)
    _wait_for_command(page, "cstudy list --widen all")
    page.wait_for_selector(f"{LISTED} tbody tr")
    seen.fragment_widened = page.evaluate("location.hash")
    seen.command_widened = page.locator(COMMAND).inner_text()
    seen.rows_widened = page.locator(SLUGS).count()
    seen.chip_after_widening = page.locator(CHIP).count()
    seen.widened_chips = _chips(page)
    seen.focus_after_widening = page.evaluate(FOCUSED)


def _reload(page: Any, seen: Visit) -> None:
    page.reload()
    page.wait_for_selector(f"{LISTED} tbody tr")
    seen.reloaded_fragment = page.evaluate("location.hash")
    seen.reloaded_rows = page.locator(SLUGS).count()
    seen.reloaded_widened_chips = _chips(page)
    page.click(f"{SLUGS} >> nth=0")
    page.wait_for_function("() => location.hash.startsWith('#/problems/')")
    page.go_back()
    page.wait_for_selector(f"{LISTED} tbody tr")
    seen.back_fragment = page.evaluate("location.hash")


def _give_the_profile_back(page: Any, seen: Visit) -> None:
    page.click("#chip-widen-lang")
    _wait_for_command(page, "cstudy list --widen role --widen domain")
    page.wait_for_selector(f"{LISTED} tbody tr")
    seen.command_after_removal = page.locator(COMMAND).inner_text()
    seen.chip_after_removal = _words(page.locator(CHIP).inner_text())
    page.select_option("#filter-lang", "any")
    _wait_for_command(page, "cstudy list --widen all")
    seen.lang_after_choosing_any = page.locator("#filter-lang").input_value()
    seen.fragment_after_choosing_any = page.evaluate("location.hash")
    page.click("#filter-clear")
    _wait_for_command(page, "cstudy list")
    page.wait_for_selector(CHIP)
    seen.fragment_after_clear = page.evaluate("location.hash")
    seen.chip_after_clear = page.locator(CHIP).count()


def _guides(page: Any, base: str, seen: Visit) -> None:
    page.goto(f"{base}/#/guides")
    page.wait_for_selector(f"{GUIDE_ROWS}, {PATH_CARDS}")
    page.wait_for_selector(CHIP)
    seen.guides_chip_text = _words(page.locator(CHIP).inner_text())
    seen.guides_chip_name = page.locator(CHIP).get_attribute("aria-label") or ""
    seen.guides_rows = page.locator(GUIDE_ROWS).count()
    seen.guides_command = page.locator(COMMAND).inner_text()
    page.click(CHIP)
    _wait_for_command(page, "cstudy learn --widen all")
    page.wait_for_function(
        "wanted => document.querySelectorAll('ul.guide-list > li').length === wanted",
        arg=seen.cli_guides_wide,
    )
    seen.guides_widened_fragment = page.evaluate("location.hash")
    seen.guides_widened_command = page.locator(COMMAND).inner_text()
    seen.guides_widened_rows = page.locator(GUIDE_ROWS).count()
    seen.guides_widened_chips = _chips(page)
    seen.guides_chip_after = page.locator(CHIP).count()


def _mock(page: Any, base: str, seen: Visit) -> None:
    page.goto(f"{base}/#/mock")
    page.wait_for_selector(MOCK_FORM)
    page.wait_for_selector(CHIP)
    seen.mock_chip_text = _words(page.locator(CHIP).inner_text())
    seen.mock_chip_name = page.locator(CHIP).get_attribute("aria-label") or ""
    seen.mock_command = page.locator("form.mock-form .cmd").inner_text()
    seen.mock_languages = page.locator("#mock-language option").all_inner_texts()
    page.click(CHIP)
    page.wait_for_function(MOCK_COMMAND_IS, arg="cstudy mock --widen all")
    seen.mock_command_widened = page.locator("form.mock-form .cmd").inner_text()
    seen.mock_widened_chips = _chips(page)
    seen.mock_chip_after = page.locator(CHIP).count()


def _start_dialog(page: Any, base: str, seen: Visit) -> None:
    page.goto(f"{base}/#/problems/{seen.rust_slug}")
    page.click("button:has-text('Start…')")
    page.wait_for_selector("#start-language")
    seen.start_options = page.locator("#start-language option").all_inner_texts()
    seen.start_disabled = page.locator("#start-language option:disabled").all_inner_texts()
    seen.start_language = page.locator("#start-language").input_value()
    seen.start_note = page.locator("#start-jdk-note").inner_text()


@pytest.fixture(scope="module")
def visit(engine: str, narrowed: Path, server: RunningServer) -> Visit:
    seen = Visit()
    _read_the_cli(narrowed, seen)
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        _problems(page, seen)
        _widen_by_the_chip(page, seen)
        _reload(page, seen)
        _give_the_profile_back(page, seen)
        _guides(page, server.address, seen)
        _mock(page, server.address, seen)
        _start_dialog(page, server.address, seen)
        browser.close()
    return seen


@dataclass
class Plain:
    """What a profile that narrows nothing shows."""

    chips: dict[str, int] = field(default_factory=dict[str, int])
    summary_hidden: bool = False
    lang_first: str = ""
    errors: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def unfiltered(engine: str, plain_server: RunningServer) -> Plain:
    seen = Plain()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_page(), seen.errors)
        page.set_default_timeout(WAIT_MS)
        page.goto(plain_server.login_url)
        page.wait_for_selector(f"{LISTED} tbody tr")
        seen.chips["problems"] = page.locator(CHIP).count()
        seen.summary_hidden = not page.locator(".filter-summary").is_visible()
        seen.lang_first = page.locator("#filter-lang option").first.inner_text()
        page.goto(f"{plain_server.address}/#/guides")
        page.wait_for_selector(GUIDE_ROWS)
        seen.chips["guides"] = page.locator(CHIP).count()
        page.goto(f"{plain_server.address}/#/mock")
        page.wait_for_selector(MOCK_FORM)
        seen.chips["mock"] = page.locator(CHIP).count() + page.locator(EDIT).count()
        browser.close()
    return seen


def test_the_problems_view_shows_one_chip_with_the_counts_of_the_command(visit):
    assert visit.cli_hidden > 0
    total = visit.cli_shown + visit.cli_hidden
    assert visit.chip_text == f"{visit.cli_shown} of {total} · your profile: {PROFILE}{CLOSE}"


def test_the_chip_is_a_button_named_for_what_it_shows_all_of(visit):
    total = visit.cli_shown + visit.cli_hidden
    assert visit.chip_tag == "BUTTON"
    assert visit.chip_name == (
        f"Show all {total}: your profile shows {visit.cli_shown}, "
        f"languages {', '.join(LANGUAGES)}; roles {ROLE} and general; "
        f"domains {', '.join(DOMAINS)}"
    )


def test_the_chip_is_reached_by_tab(visit):
    assert visit.tab_reaches_chip


def test_edit_profile_follows_the_chip_to_settings(visit):
    assert visit.edit_href == "#/settings/profile"


def test_the_rows_and_the_count_are_those_of_the_command_above_the_view(visit):
    total = visit.cli_shown + visit.cli_hidden
    assert (visit.command, visit.rows) == ("cstudy list", visit.cli_shown)
    assert visit.count == f"{visit.cli_shown} of {total}"


def test_a_dimension_the_profile_narrows_offers_your_profile_then_any(visit):
    assert visit.lang_options[:2] == ["your profile", "any"]
    assert visit.role_options[:2] == ["your profile", "any"]
    assert visit.domain_options[:2] == ["your profile", "any"]


def test_the_chip_widens_each_dimension_it_names_in_the_route(visit):
    assert visit.fragment_widened == "#/?widen=lang,role,domain"
    assert visit.command_widened == "cstudy list --widen all"


def test_widening_shows_the_rows_of_the_widened_command(visit):
    assert visit.rows_widened == visit.cli_widened


def test_widening_leaves_no_profile_chip_but_a_chip_per_widened_dimension(visit):
    assert visit.chip_after_widening == 0
    assert [chip.strip(CLOSE) for chip in visit.widened_chips] == WIDENED


def test_the_focus_moves_to_the_neighbor_of_the_chip_that_widened(visit):
    assert visit.focus_after_widening == "chip-widen-lang"


def test_widening_survives_a_reload_and_back(visit):
    assert visit.reloaded_fragment == "#/?widen=lang,role,domain"
    assert visit.reloaded_rows == visit.cli_widened
    assert [chip.strip(CLOSE) for chip in visit.reloaded_widened_chips] == WIDENED
    assert visit.back_fragment == "#/?widen=lang,role,domain"


def test_removing_a_widened_chip_gives_the_dimension_back_to_the_profile(visit):
    assert visit.command_after_removal == "cstudy list --widen role --widen domain"
    assert f"your profile: {', '.join(LANGUAGES)}{CLOSE}" in visit.chip_after_removal


def test_choosing_any_in_a_profile_list_widens_that_dimension(visit):
    assert visit.lang_after_choosing_any == "any"
    assert visit.fragment_after_choosing_any == "#/?widen=lang,role,domain"


def test_clear_empties_the_route_so_the_profile_applies_again(visit):
    assert (visit.fragment_after_clear, visit.chip_after_clear) == ("#/", 1)


def test_the_guides_view_shows_the_counts_of_cstudy_learn(visit):
    guides = f"{visit.cli_guides} of {visit.cli_guides + visit.cli_guides_hidden} guides"
    paths = f"{visit.cli_paths} of {visit.cli_paths + visit.cli_paths_hidden} paths"
    assert visit.guides_chip_text == f"{guides} · {paths} · your profile: {LABELS}{CLOSE}"
    assert visit.guides_rows == visit.cli_guides
    assert visit.guides_command == "cstudy learn"


def test_the_guides_chip_is_named_for_all_it_would_show(visit):
    wanted = (
        f"Show all {visit.cli_guides + visit.cli_guides_hidden} guides and "
        f"{visit.cli_paths + visit.cli_paths_hidden} paths: your profile shows "
        f"{visit.cli_guides} guides and {visit.cli_paths} paths, roles {ROLE} and general; "
        f"domains {', '.join(DOMAINS)}"
    )
    assert visit.guides_chip_name == wanted


def test_widening_the_guides_keeps_it_in_the_route_and_the_command(visit):
    assert visit.guides_widened_fragment == "#/guides?widen=role,domain"
    assert visit.guides_widened_command == "cstudy learn --widen all"
    assert visit.guides_widened_rows == visit.cli_guides_wide
    assert visit.guides_chip_after == 0
    assert [chip.strip(CLOSE) for chip in visit.guides_widened_chips] == LABEL_CHIPS


def test_the_mock_view_shows_the_chip_of_its_scope(visit):
    assert re.fullmatch(rf"\d+ of \d+ · your profile: {LABELS}{CLOSE}", visit.mock_chip_text), (
        visit.mock_chip_text
    )
    assert visit.mock_chip_name.startswith("Show all ")
    assert visit.mock_chip_name.endswith(f"roles {ROLE} and general; domains {', '.join(DOMAINS)}")
    assert visit.mock_command == "cstudy mock"


def test_the_mock_chip_widens_the_picks_for_this_start(visit):
    assert visit.mock_command_widened == "cstudy mock --widen all"
    assert visit.mock_chip_after == 0
    assert [chip.strip(CLOSE) for chip in visit.mock_widened_chips] == LABEL_CHIPS


def test_the_mock_form_offers_the_workspaces_languages_only(visit):
    assert visit.mock_languages == list(LANGUAGES)


def test_the_start_dialog_disables_a_language_the_workspace_does_not_list(visit):
    assert "rust" in visit.start_options
    assert set(visit.start_disabled) == set(visit.start_options) - set(LANGUAGES)
    assert "rust" in visit.start_disabled
    assert visit.start_language == "python"
    assert "not in this workspace: cstudy lang add rust" in visit.start_note


def test_a_profile_that_hides_nothing_shows_no_chip_and_no_line(unfiltered):
    assert unfiltered.chips == {"problems": 0, "guides": 0, "mock": 0}
    assert unfiltered.summary_hidden


def test_a_profile_that_narrows_nothing_leaves_the_lists_ordinary(unfiltered):
    assert unfiltered.lang_first == "lang"


def test_the_views_log_no_error_or_warning(visit, unfiltered):
    assert [*visit.errors, *unfiltered.errors] == []
