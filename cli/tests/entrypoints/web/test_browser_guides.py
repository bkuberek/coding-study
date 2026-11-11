"""The Guides view in a real browser (docs/specs/web-ui.md#guides-view), in each engine of
`tests/browsers.py`, over the catalog's real guides and the path "hashing": the top bar's Guides
entry; the list with the path's progress; the login landing on a guide, as
`cstudy learn <guide> --open` does; each `mermaid` block drawn as an SVG named and described by its
`accTitle` and `accDescr`, its text drawing hidden, by Mermaid chunks fetched only once a guide
with a diagram opens, from this server alone, in the light theme and again in the dark one; a
code example highlighted; Mark as read kept through a reload and agreeing with
`cstudy learn --path hashing`; the path's steps with their done state and level targets; and the
Problem view linking to its guides. The CSP holds and nothing is logged.

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
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
GUIDE = "hash-maps-and-sets"
GUIDE_TITLE = "Hash maps and sets"
PATH = "hashing"
STEPS = 21
GUIDES_LINK = ".topbar nav a[data-view='guides']"
PATH_CARD = ".path-card"
DRAWN = "figure.diagram > svg"
MARK_READ = "button:has-text('Mark as read')"
READ_ON = ".guide-read .read-mark.is-read"
DIAGRAMS_CHUNK = "/assets/chunks/diagrams-"
ALL_DARK = """() => [...document.querySelectorAll("figure.diagram")]
  .every((figure) => figure.dataset.drawn === "dark")"""
FIGURES_PROBE = """() => [...document.querySelectorAll("figure.diagram")].map((figure) => {
  const svg = figure.querySelector(":scope > svg");
  const text = figure.querySelector(".diagram-text");
  const named = (attribute) => {
    const id = svg?.getAttribute(attribute);
    return id ? document.getElementById(id)?.textContent ?? null : null;
  };
  return {
    svg: svg !== null,
    drawn: figure.dataset.drawn ?? null,
    title: svg?.querySelector("title")?.textContent ?? null,
    labelled: named("aria-labelledby"),
    described: named("aria-describedby"),
    text_hidden: text !== null && text.hidden && text.getClientRects().length === 0,
    source: figure.dataset.mermaid ?? "",
  };
})"""


@dataclass
class Seen:
    nav_href: str = ""
    nav_current: str | None = None
    path_card: str = ""
    diagrams_fetched_on_list: bool = True
    landed_hash: str = ""
    heading: str = ""
    figures: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    dark_figures: list[str | None] = field(default_factory=list[str | None])
    highlighted: int = 0
    diagrams_fetched: bool = False
    other_sites: list[str] = field(default_factory=list[str])
    read_after_reload: str = ""
    button_after_reload: int = -1
    path_standing: str = ""
    step_classes: list[str] = field(default_factory=list[str])
    step_targets: list[str] = field(default_factory=list[str])
    next_href: str = ""
    problem_guides: list[str] = field(default_factory=list[str])
    logged: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def workspace(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(mark_workspace(tmp_path_factory.mktemp(f"guides-{engine}") / "workspace"))


@pytest.fixture(scope="module")
def server(workspace: Path) -> Iterator[RunningServer]:
    with running_server(workspace) as running:
        yield running


@pytest.fixture(scope="module")
def seen(engine: str, server: RunningServer) -> Seen:
    found = Seen()
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = watched(browser.new_context(color_scheme="light").new_page(), found.logged)
        page.set_default_timeout(WAIT_MS)
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        page.click(GUIDES_LINK)
        page.wait_for_selector(PATH_CARD)
        found.nav_href = page.get_attribute(GUIDES_LINK, "href") or ""
        found.nav_current = page.get_attribute(GUIDES_LINK, "aria-current")
        found.path_card = page.inner_text(PATH_CARD)
        found.diagrams_fetched_on_list = any(DIAGRAMS_CHUNK in url for url in requests)
        _read_the_guide(page, found, server, requests)
        _mark_read(page, found)
        _read_the_path(page, found)
        _read_the_problem(page, found)
        found.other_sites = [url for url in requests if not url.startswith(server.address)]
        browser.close()
    return found


def _read_the_guide(page: Any, found: Seen, server: RunningServer, requests: list[str]) -> None:
    """Lands on the guide as `cstudy learn <guide> --open` does: the login names its view."""
    page.goto(f"{server.login_url}&view=/guides/{GUIDE}")
    page.wait_for_selector(DRAWN)
    page.wait_for_function("() => !document.querySelector('figure.diagram[aria-busy]')")
    found.landed_hash = page.evaluate("location.hash")
    found.heading = page.inner_text("main h1")
    found.figures = page.evaluate(FIGURES_PROBE)
    found.highlighted = page.locator(".guide-body pre code .tok-k").count()
    found.diagrams_fetched = any(DIAGRAMS_CHUNK in url for url in requests)
    page.emulate_media(color_scheme="dark")
    page.wait_for_function(ALL_DARK)
    found.dark_figures = [figure["drawn"] for figure in page.evaluate(FIGURES_PROBE)]
    page.emulate_media(color_scheme="light")


def _mark_read(page: Any, found: Seen) -> None:
    page.click(MARK_READ)
    page.wait_for_selector(READ_ON)
    page.reload()
    page.wait_for_selector(READ_ON)
    found.read_after_reload = page.inner_text(READ_ON)
    found.button_after_reload = page.locator(MARK_READ).count()


def _read_the_path(page: Any, found: Seen) -> None:
    page.goto(page.url.split("#")[0] + f"#/paths/{PATH}")
    page.wait_for_selector(".path-steps li")
    found.path_standing = page.inner_text(".guide-head .path-standing")
    found.step_classes = page.eval_on_selector_all(
        ".path-steps > li", "steps => steps.map(step => step.className)"
    )
    found.step_targets = page.eval_on_selector_all(
        ".path-steps .step-target", "targets => targets.map(target => target.textContent)"
    )
    found.next_href = page.get_attribute(".path-next a", "href") or ""


def _read_the_problem(page: Any, found: Seen) -> None:
    page.goto(page.url.split("#")[0] + "#/problems/two-sum")
    page.wait_for_selector(".problem-guides a")
    found.problem_guides = page.eval_on_selector_all(
        ".problem-guides a", "links => links.map(link => link.getAttribute('href'))"
    )


def test_the_top_bar_has_a_guides_entry(seen: Seen):
    assert (seen.nav_href, seen.nav_current) == ("#/guides", "page")


def test_the_list_shows_the_path_with_its_progress(seen: Seen):
    assert (
        "Hashing" in seen.path_card,
        f"0 of {STEPS} steps done" in seen.path_card,
        seen.diagrams_fetched_on_list,
    ) == (True, True, False)


def test_the_login_lands_on_the_guide_it_names(seen: Seen):
    assert (seen.landed_hash, seen.heading) == (f"#/guides/{GUIDE}", GUIDE_TITLE)


def test_each_diagram_is_an_svg_named_and_described_by_its_accessibility_lines(seen: Seen):
    expected = [
        (True, "light", _line(figure["source"], "accTitle"), _line(figure["source"], "accDescr"))
        for figure in seen.figures
    ]
    drawn = [
        (figure["svg"], figure["drawn"], figure["labelled"], figure["described"])
        for figure in seen.figures
    ]
    assert (len(seen.figures) >= 1, drawn) == (True, expected)


def test_every_text_drawing_is_hidden(seen: Seen):
    assert [figure["text_hidden"] for figure in seen.figures] == [True] * len(seen.figures)


def test_the_diagrams_follow_the_dark_theme(seen: Seen):
    assert seen.dark_figures == ["dark"] * len(seen.figures)


def test_mermaid_comes_from_this_server_once_a_guide_has_a_diagram(seen: Seen):
    assert (seen.diagrams_fetched, seen.other_sites) == (True, [])


def test_the_code_examples_are_highlighted(seen: Seen):
    assert seen.highlighted > 0


def test_mark_as_read_is_kept_through_a_reload(seen: Seen):
    assert (seen.read_after_reload.startswith("✓ read on"), seen.button_after_reload) == (True, 0)


def test_the_terminal_agrees_the_guide_is_read(seen: Seen, server: RunningServer):
    command = [sys.executable, "-m", "coding_study", "learn", "--path", PATH, "--json"]
    result = subprocess.run(
        command, capture_output=True, text=True, env=server.environment, check=True
    )
    steps = json.loads(result.stdout)["steps"]
    assert [step["status"] for step in steps[:2]] == ["not read", "read"]


def test_the_path_shows_its_steps_their_done_state_and_level_targets(seen: Seen):
    assert (
        f"1 of {STEPS} steps done" in seen.path_standing,
        len(seen.step_classes),
        seen.step_classes[:2],
        seen.step_targets,
        seen.next_href,
    ) == (
        True,
        STEPS,
        ["path-step", "path-step is-done"],
        ["through level 2"],
        "#/guides/hash-functions",
    )


def test_the_problem_view_links_to_its_guides(seen: Seen):
    assert seen.problem_guides == [f"#/guides/{GUIDE}"]


def test_nothing_is_logged(seen: Seen):
    assert seen.logged == []


def _line(source: str, key: str) -> str:
    """The text of a diagram's `accTitle:` or `accDescr:` line."""
    prefix = f"{key}:"
    return next(
        line.strip().removeprefix(prefix).strip()
        for line in source.splitlines()
        if line.strip().startswith(prefix)
    )
