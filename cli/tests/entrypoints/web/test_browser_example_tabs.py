"""The tabs of a guide's examples in several languages in a real browser
(docs/specs/web-ui.md#guides-view, docs/specs/guides.md#the-language-shown), in each engine of
`tests/browsers.py`, over the catalog's real guides: with `default_lang = "java"` in config.toml,
each example of `hash-maps-and-sets` with variants starts on Java and an example in one language
has no tabs; choosing Go on one example shows Go in every one; the arrow keys and End move every
example along with the focus; the terminal guide's examples, which have no Go, start on bash; a
language chosen there holds on the next guide; and a reload starts again from `default_lang`.
The tabs are a labelled tablist, each panel labelled by its tab. The CSP holds and nothing is
logged.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

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
GUIDE = "hash-maps-and-sets"
SHELL_GUIDE = "using-the-terminal"
DEFAULT_LANGUAGE = "java"
GROUPS = ".guide-body .example-tabs"
FIVE = ["Python", "TypeScript", "Java", "Kotlin", "Go"]
TABS_PROBE = """() => [...document.querySelectorAll(".guide-body .example-tabs")].map((group) => {
  const list = group.querySelector("[role=tablist]");
  const tabs = [...list.querySelectorAll("[role=tab]")];
  const shown = [...group.querySelectorAll("[role=tabpanel]")].filter((panel) => !panel.hidden);
  const selected = tabs.filter((tab) => tab.getAttribute("aria-selected") === "true");
  return {
    label: list.getAttribute("aria-label"),
    tabs: tabs.map((tab) => tab.textContent),
    selected: selected.map((tab) => tab.textContent),
    focusable: tabs.filter((tab) => tab.tabIndex === 0).map((tab) => tab.textContent),
    shown: shown.map((panel) => document.getElementById(panel.getAttribute("aria-labelledby"))
      ?.textContent ?? null),
    code: shown.map((panel) => panel.querySelector("code")?.className ?? null),
  };
})"""
SELECTED = """language => {
  const groups = [...document.querySelectorAll(".guide-body .example-tabs")];
  return groups.length > 0 && groups.every((group) => [...group.querySelectorAll("[role=tab]")]
    .some((tab) => tab.textContent === language && tab.getAttribute("aria-selected") === "true"));
}"""

ANNOUNCED = """message => [...document.querySelectorAll(".sr-only[role=status]")]
  .some((region) => region.textContent === message)"""
"""The shell's polite live region, which a screen reader reads, says the message."""


@dataclass
class Seen:
    first: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    examples: int = 0
    single_language_blocks: int = 0
    after_click: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    announced: str = ""
    after_arrow: list[str] = field(default_factory=list[str])
    focused_after_arrow: str = ""
    after_end: list[str] = field(default_factory=list[str])
    shell_first: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    back_after_choice: list[str] = field(default_factory=list[str])
    after_reload: list[str] = field(default_factory=list[str])
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = Path(mark_workspace(tmp_path_factory.mktemp(f"tabs-{engine}") / "workspace"))
    config = workspace.parent / "config" / "coding-study" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(f'default_lang = "{DEFAULT_LANGUAGE}"\n')
    return workspace


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


def _open(page: Any, server: RunningServer, slug: str) -> None:
    page.goto(f"{server.login_url}&view=/guides/{slug}")
    page.wait_for_selector(f"{GROUPS} [role=tab][aria-selected=true]")


def _selected(page: Any) -> list[str]:
    return [group["selected"][0] for group in page.evaluate(TABS_PROBE)]


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_context().new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        _open(page, server, GUIDE)
        found.first = page.evaluate(TABS_PROBE)
        found.examples = page.locator(".guide-body pre code.language-python").count()
        found.single_language_blocks = page.locator(
            ".guide-body > pre code.language-python, .guide-body > pre code.language-java"
        ).count()

        page.locator(f"{GROUPS} >> nth=0").get_by_role("tab", name="Go").click()
        page.wait_for_function(SELECTED, arg="Go")
        found.after_click = page.evaluate(TABS_PROBE)
        page.wait_for_function(ANNOUNCED, arg="Examples in Go")
        found.announced = "Examples in Go"

        page.locator(f"{GROUPS} >> nth=1").get_by_role("tab", name="Go").press("ArrowLeft")
        page.wait_for_function(SELECTED, arg="Kotlin")
        found.after_arrow = _selected(page)
        found.focused_after_arrow = page.evaluate(
            "() => document.activeElement?.closest('.example-tabs') === "
            "document.querySelectorAll('.guide-body .example-tabs')[1] "
            "? document.activeElement.textContent : null"
        )
        page.keyboard.press("End")
        page.wait_for_function(SELECTED, arg="Go")
        found.after_end = _selected(page)

        page.goto(page.url.split("#")[0] + f"#/guides/{SHELL_GUIDE}")
        page.wait_for_selector(f"{GROUPS} [role=tab][aria-selected=true]")
        found.shell_first = page.evaluate(TABS_PROBE)
        page.locator(f"{GROUPS} >> nth=0").get_by_role("tab", name="Python").click()
        page.wait_for_function(SELECTED, arg="Python")
        page.goto(page.url.split("#")[0] + f"#/guides/{GUIDE}")
        page.wait_for_selector(f"{GROUPS} [role=tab][aria-selected=true]")
        found.back_after_choice = _selected(page)

        page.reload()
        page.wait_for_selector(f"{GROUPS} [role=tab][aria-selected=true]")
        found.after_reload = _selected(page)
        browser.close()
    return found


def test_each_example_starts_on_default_lang(seen: Seen):
    group = {
        "label": "Language of the example",
        "tabs": FIVE,
        "selected": ["Java"],
        "focusable": ["Java"],
        "shown": ["Java"],
        "code": ["language-java"],
    }
    assert seen.first == [group, group]


def test_an_example_in_one_language_has_no_tabs(seen: Seen):
    assert (seen.single_language_blocks, seen.examples > 2) == (2, True)


def test_choosing_a_tab_on_one_example_changes_every_example(seen: Seen):
    assert [(group["selected"], group["shown"], group["code"]) for group in seen.after_click] == [
        (["Go"], ["Go"], ["language-go"]),
        (["Go"], ["Go"], ["language-go"]),
    ]


def test_the_change_is_announced(seen: Seen):
    assert seen.announced == "Examples in Go"


def test_the_arrow_keys_move_every_example_and_keep_the_focus_in_its_tablist(seen: Seen):
    assert (seen.after_arrow, seen.focused_after_arrow, seen.after_end) == (
        ["Kotlin", "Kotlin"],
        "Kotlin",
        ["Go", "Go"],
    )


def test_a_shell_guides_examples_start_on_bash_without_the_chosen_language(seen: Seen):
    assert [(group["tabs"], group["selected"]) for group in seen.shell_first] == [
        (["Bash", "Python"], ["Bash"]),
        (["Bash", "Python"], ["Bash"]),
    ]


def test_a_language_chosen_holds_on_the_next_guide(seen: Seen):
    assert seen.back_after_choice == ["Python", "Python"]


def test_a_reload_starts_again_from_default_lang(seen: Seen):
    assert seen.after_reload == ["Java", "Java"]


def test_nothing_is_logged(seen: Seen):
    assert seen.logged == []
