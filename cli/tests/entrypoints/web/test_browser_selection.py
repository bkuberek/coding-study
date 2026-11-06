"""A selection on the line of the cursor shows in a real browser
(docs/specs/web-ui.md#editor), in each engine of `tests/browsers.py`, in both themes, in a focused
and an unfocused editor. `drawSelection` paints the selection behind the text, under the line's own
background, so the proof is in the pixels: a clipped screenshot of the active line, with and
without the selection, whose most common colour must differ by what an eye can see, and the active
line alone must look as it did when its colour was opaque.

Playwright and its engines are set up as `tests/browsers.py` says; without them the test is
skipped.
"""

import json
import struct
import zlib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.browsers import launched
from tests.helpers import mark_workspace
from tests.serve_process import RunningServer, running_server

pytestmark = pytest.mark.slow
sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

PROBLEM = "two-sum"
PREFERENCES = Path(".cs") / "serve" / "preferences.json"
WAIT_MS = 60_000
SHEET = "dialog.sheet[open]"
EDITOR = ".panel:not([hidden]) .cm-editor"
CONTENT = f"{EDITOR} .cm-content"
ACTIVE_LINE = f"{CONTENT} .cm-activeLine"
CARET_MARGIN = 6
"""What a clip leaves out at each end of the text, where the caret may blink."""
VISIBLE_DISTANCE = 20
"""The least sum of the three channels' differences that a selection must make: the themes' own
selection colours differ from their lines by far more."""
SAME_LOOK = 3
"""How far the translucent active line may land from the opaque colour it replaced, per channel."""
ACTIVE_LINE_LOOK = {"light": (0xF3, 0xED, 0xE1), "dark": (0x1E, 0x22, 0x28)}
SIGNATURE = (8, b"\x89PNG\r\n\x1a\n")
CHANNELS = {2: 3, 6: 4}
"""PNG's colour types that hold no palette: truecolour, with and without alpha."""

type Colour = tuple[int, int, int]


@dataclass
class Selection:
    """The most common colour of the active line in one theme, at each step."""

    bare: Colour = (0, 0, 0)
    selected: Colour = (0, 0, 0)
    across_lines: Colour = (0, 0, 0)
    unfocused: Colour = (0, 0, 0)


def most_common_colour(png: bytes) -> Colour:
    width, height, channels, rows = _rows(png)
    pixels = Counter(
        tuple(row[column : column + 3])
        for row in rows
        for column in range(0, width * channels, channels)
    )
    assert height > 0
    return pixels.most_common(1)[0][0]  # type: ignore[return-value]


def _rows(png: bytes) -> tuple[int, int, int, list[bytes]]:
    """Decodes an 8-bit, non-interlaced PNG, as Chromium writes a screenshot."""
    length, signature = SIGNATURE
    assert png[:length] == signature
    position, header, data = length, b"", b""
    while position < len(png):
        size, kind = struct.unpack(">I4s", png[position : position + 8])
        body = png[position + 8 : position + 8 + size]
        position += 12 + size
        if kind == b"IHDR":
            header = body
        elif kind == b"IDAT":
            data += body
    width, height, depth, colour_type, _, _, interlace = struct.unpack(">IIBBBBB", header)
    assert (depth, interlace) == (8, 0)
    channels = CHANNELS[colour_type]
    return width, height, channels, _unfiltered(zlib.decompress(data), width * channels, channels)


def _unfiltered(raw: bytes, stride: int, channels: int) -> list[bytes]:
    rows: list[bytes] = []
    previous = bytes(stride)
    for start in range(0, len(raw), stride + 1):
        kind, line = raw[start], bytearray(raw[start + 1 : start + 1 + stride])
        for index, value in enumerate(line):
            left = line[index - channels] if index >= channels else 0
            up = previous[index]
            corner = previous[index - channels] if index >= channels else 0
            line[index] = (value + _predicted(kind, left, up, corner)) & 0xFF
        previous = bytes(line)
        rows.append(previous)
    return rows


def _predicted(kind: int, left: int, up: int, corner: int) -> int:
    match kind:
        case 0:
            return 0
        case 1:
            return left
        case 2:
            return up
        case 3:
            return (left + up) // 2
        case _:
            estimate = left + up - corner
            return min((left, up, corner), key=lambda near: abs(estimate - near))


@pytest.fixture(scope="module")
def server(engine: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[RunningServer]:
    workspace = mark_workspace(tmp_path_factory.mktemp(f"selection-{engine}") / "workspace")
    with running_server(Path(workspace)) as running:
        yield running


@pytest.fixture(scope="module")
def selections(engine: str, server: RunningServer) -> dict[str, Selection]:
    workspace = Path(server.environment["CSTUDY_WORKSPACE"])
    seen: dict[str, Selection] = {}
    with sync_api.sync_playwright() as playwright:
        browser = launched(playwright, engine)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("dialog", lambda dialog: dialog.accept())
        page.set_default_timeout(WAIT_MS)
        page.goto(server.login_url)
        page.wait_for_selector("table.problems tbody tr")
        _start(page)
        for theme in ACTIVE_LINE_LOOK:
            _store_theme(workspace, theme)
            page.reload()
            page.wait_for_selector(CONTENT)
            seen[theme] = _selection_steps(page)
        browser.close()
    return seen


def _start(page: Any) -> None:
    page.evaluate(f"location.hash = '#/problems/{PROBLEM}'")
    page.click(".practice-actions button.primary")
    page.click(f"{SHEET} button[type=submit]")
    page.wait_for_selector(CONTENT)


def _store_theme(workspace: Path, theme: str) -> None:
    path = workspace / PREFERENCES
    document = json.loads(path.read_text()) if path.exists() else {"format": 1}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**document, "theme": theme}) + "\n")


def _selection_steps(page: Any) -> Selection:
    seen = Selection()
    page.click(f"{CONTENT} .cm-line:has-text('def ')")
    page.keyboard.press("Home")
    seen.bare = _active_line_colour(page)
    page.keyboard.press("Shift+End")
    seen.selected = _active_line_colour(page)
    page.keyboard.press("Home")
    page.keyboard.press("ArrowUp")
    page.keyboard.press("Home")
    page.keyboard.press("Shift+ArrowDown")
    page.keyboard.press("Shift+End")
    seen.across_lines = _active_line_colour(page)
    page.evaluate("document.activeElement?.blur()")
    page.wait_for_function(
        "selector => !document.querySelector(selector)?.classList.contains('cm-focused')",
        arg=EDITOR,
    )
    seen.unfocused = _active_line_colour(page)
    return seen


def _active_line_colour(page: Any) -> Colour:
    """The most common colour of the text's part of the active line: the line's background, between
    the letters, and the selection's where one shows."""
    box = page.eval_on_selector(
        ACTIVE_LINE,
        """line => {
          const range = document.createRange();
          range.selectNodeContents(line);
          const { x, y, width, height } = range.getBoundingClientRect();
          return { x, y, width, height };
        }""",
    )
    clip = {
        "x": box["x"] + CARET_MARGIN,
        "y": box["y"],
        "width": box["width"] - 2 * CARET_MARGIN,
        "height": box["height"],
    }
    return most_common_colour(page.screenshot(clip=clip, type="png"))


def distance(left: Colour, right: Colour) -> int:
    return sum(abs(one - other) for one, other in zip(left, right, strict=True))


@pytest.mark.parametrize("theme", ACTIVE_LINE_LOOK)
def test_a_selection_on_the_cursor_s_line_shows(selections, theme):
    seen = selections[theme]
    assert distance(seen.selected, seen.bare) >= VISIBLE_DISTANCE


@pytest.mark.parametrize("theme", ACTIVE_LINE_LOOK)
def test_the_part_of_a_longer_selection_on_the_cursor_s_line_shows(selections, theme):
    seen = selections[theme]
    assert distance(seen.across_lines, seen.bare) >= VISIBLE_DISTANCE


@pytest.mark.parametrize("theme", ACTIVE_LINE_LOOK)
def test_a_selection_shows_in_an_editor_without_the_focus(selections, theme):
    seen = selections[theme]
    assert distance(seen.unfocused, seen.bare) >= VISIBLE_DISTANCE


@pytest.mark.parametrize("theme", ACTIVE_LINE_LOOK)
def test_the_active_line_alone_looks_as_it_did(selections, theme):
    looks = zip(selections[theme].bare, ACTIVE_LINE_LOOK[theme], strict=True)
    assert all(abs(seen - wanted) <= SAME_LOOK for seen, wanted in looks), selections[theme].bare
