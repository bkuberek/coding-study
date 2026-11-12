"""The Guides view in a real browser (docs/specs/web-ui.md#guides-view), in each engine of
`tests/browsers.py`, over the catalog's real guides and the path "hashing": the top bar's Guides
entry; the list with the path's progress; the login landing on a guide, as
`cstudy learn <guide> --open` does; each diagram shown as the `<img>` of its SVG drawing in the
page's theme, with the diagram's `accTitle` as alt text and its `accDescr` as caption, and the
other theme's drawing when the system or the page's theme changes; no text drawing and no Mermaid
source shown; every request to the server alone; a code example highlighted; Mark as read kept
through a reload and agreeing with `cstudy learn --path hashing`; the path's steps with their
done state and level targets; and the Problem view linking to its guides. The CSP holds and
nothing is logged.

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

from coding_study.domain.guide_markdown import GuideMarkdown, diagram_text
from tests.browsers import launched, watched
from tests.helpers import REPOSITORY_ROOT, mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

WAIT_MS = 60_000
GUIDE = "hash-maps-and-sets"
GUIDE_TITLE = "Hash maps and sets"
PATH = "hashing"
STEPS = 22
GUIDES_LINK = ".topbar nav a[data-view='guides']"
THEME_BUTTON = ".statusbar button:has-text('theme')"
PATH_CARD = ".path-card"
SHOWN = "figure.diagram img"
MARK_READ = "button:has-text('Mark as read')"
READ_ON = ".guide-read .read-mark.is-read"
DRAWINGS = f"/api/v1/guides/{GUIDE}/diagrams/"
SHOWN_IMAGES = """[...figure.querySelectorAll("img")]
    .filter((image) => getComputedStyle(image).display !== "none")"""
"""The images of a figure that the stylesheet shows."""
FIGURES_PROBE = """() => [...document.querySelectorAll("figure.diagram")].map((figure) => {
  const shown = SHOWN_IMAGES;
  return {
    shown: shown.map((image) => image.className),
    loaded: shown.every((image) => image.complete && image.naturalWidth > 0),
    alt: shown.map((image) => image.alt),
    caption: figure.querySelector("figcaption")?.textContent ?? null,
    text_drawings: figure.querySelectorAll(".diagram-text").length,
  };
})""".replace("SHOWN_IMAGES", SHOWN_IMAGES)
ALL_SHOWN = """theme => [...document.querySelectorAll("figure.diagram")].every((figure) => {
  const shown = SHOWN_IMAGES;
  return shown.length === 1 && shown[0].classList.contains(`diagram-${theme}`)
    && shown[0].complete && shown[0].naturalWidth > 0;
})""".replace("SHOWN_IMAGES", SHOWN_IMAGES)


@dataclass
class Seen:
    nav_href: str = ""
    nav_current: str | None = None
    path_card: str = ""
    drawings_on_list: bool = True
    landed_hash: str = ""
    heading: str = ""
    figures: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    shown_by_theme: dict[str, list[list[str]]] = field(default_factory=dict[str, list[list[str]]])
    source_shown: bool = True
    highlighted: int = 0
    drawings_requested: list[str] = field(default_factory=list[str])
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
        found.path_card = page.inner_text(f"{PATH_CARD}:has(a[href='#/paths/{PATH}'])")
        found.drawings_on_list = any("/diagrams/" in url for url in requests)
        _read_the_guide(page, found, server)
        _switch_themes(page, found)
        found.drawings_requested = sorted(
            {url.split(DRAWINGS)[1] for url in requests if DRAWINGS in url}
        )
        _mark_read(page, found)
        _read_the_path(page, found)
        _read_the_problem(page, found)
        found.other_sites = [url for url in requests if not url.startswith(server.address)]
        browser.close()
    return found


def _read_the_guide(page: Any, found: Seen, server: RunningServer) -> None:
    """Lands on the guide as `cstudy learn <guide> --open` does: the login names its view."""
    page.goto(f"{server.login_url}&view=/guides/{GUIDE}")
    page.wait_for_selector(SHOWN)
    page.wait_for_function(ALL_SHOWN, arg="light")
    found.landed_hash = page.evaluate("location.hash")
    found.heading = page.inner_text("main h1")
    found.figures = page.evaluate(FIGURES_PROBE)
    found.source_shown = "accTitle" in page.inner_text("main")
    found.highlighted = page.locator(".guide-body pre code .tok-k").count()


def _switch_themes(page: Any, found: Seen) -> None:
    """The system turns dark while the page follows it; then the page's own theme, light then
    dark, overrides the system's, and goes back to following it."""
    shown = lambda: [figure["shown"] for figure in page.evaluate(FIGURES_PROBE)]  # noqa: E731
    page.emulate_media(color_scheme="dark")
    page.wait_for_function(ALL_SHOWN, arg="dark")
    found.shown_by_theme["system dark"] = shown()
    for theme in ("light", "dark", "system"):
        page.click(THEME_BUTTON)
        page.wait_for_function(
            "theme => document.documentElement.dataset.theme === theme", arg=theme
        )
        if theme != "system":
            page.wait_for_function(ALL_SHOWN, arg=theme)
            found.shown_by_theme[f"page {theme}"] = shown()
    page.emulate_media(color_scheme="light")
    page.wait_for_function(ALL_SHOWN, arg="light")


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


def _diagram_texts() -> list[tuple[str, str]]:
    """Each diagram's `accTitle` and `accDescr`, from the guide's own guide.md."""
    markdown = (REPOSITORY_ROOT / "guides" / GUIDE / "guide.md").read_text()
    texts = [diagram_text(fence.content) for fence in GuideMarkdown(markdown).mermaid_fences()]
    return [(text.title, text.description) for text in texts]


def test_the_top_bar_has_a_guides_entry(seen: Seen):
    assert (seen.nav_href, seen.nav_current) == ("#/guides", "page")


def test_the_list_shows_the_path_with_its_progress(seen: Seen):
    assert (
        "Hashing" in seen.path_card,
        f"0 of {STEPS} steps done" in seen.path_card,
        seen.drawings_on_list,
    ) == (True, True, False)


def test_the_login_lands_on_the_guide_it_names(seen: Seen):
    assert (seen.landed_hash, seen.heading) == (f"#/guides/{GUIDE}", GUIDE_TITLE)


def test_each_diagram_shows_its_light_drawing_with_its_alt_text_and_caption(seen: Seen):
    expected = [
        {
            "shown": ["diagram-image diagram-light"],
            "loaded": True,
            "alt": [title],
            "caption": description,
            "text_drawings": 0,
        }
        for title, description in _diagram_texts()
    ]
    assert (len(expected) >= 1, seen.figures) == (True, expected)


def test_the_theme_shows_the_other_drawing(seen: Seen):
    count = len(_diagram_texts())
    light, dark = (
        [["diagram-image diagram-light"]] * count,
        [["diagram-image diagram-dark"]] * count,
    )
    assert seen.shown_by_theme == {"system dark": dark, "page light": light, "page dark": dark}


def test_the_drawings_come_from_the_server_and_nothing_from_another_site(seen: Seen):
    count = len(_diagram_texts())
    drawn = sorted(f"{n}-{theme}.svg" for n in range(1, count + 1) for theme in ("light", "dark"))
    assert (seen.drawings_requested, seen.other_sites) == (drawn, [])


def test_the_mermaid_source_is_not_shown(seen: Seen):
    assert seen.source_shown is False


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
    assert seen.problem_guides == ["#/guides/your-first-problem", f"#/guides/{GUIDE}"]


def test_nothing_is_logged(seen: Seen):
    assert seen.logged == []
