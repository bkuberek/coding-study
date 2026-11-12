"""How a guide.md reads (docs/specs/guides.md#guidemd): its fenced blocks, the examples and their
outputs, the Mermaid diagrams with their text and SVG drawings, and the text `cstudy learn` shows.

Fences are read line by line, as the renderer of `tools/guides/` reads them: a fence opens with
three or more backticks or tildes at the start of a line and closes with a line of at least as
many of the same character and nothing else.
"""

import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass

MERMAID = "mermaid"
TEXT = "text"
OUTPUT = "output"
EXAMPLES_PREFIX = "examples/"
SVG_THEMES = ("light", "dark")
"""The SVG drawings of each diagram, one per theme of the web UI."""
_OPENING = re.compile(r"(?P<marker>`{3,}|~{3,})(?P<info>.*)")
_MARKER = re.compile(r"<!-- text-of-mermaid sha256:(?P<digest>[0-9a-f]{64}) -->")
_SVG_MARKER = re.compile(r"<!-- svg-of-mermaid sha256:(?P<digest>[0-9a-f]{64}) -->")
_SVG_FILE = re.compile(r"[1-9][0-9]*-(?:light|dark)\.svg")
_SVG_SIZE = re.compile(r'<svg\b[^>]*?\swidth="(?P<width>\d+)"[^>]*?\sheight="(?P<height>\d+)"')
_TITLE = re.compile(r"\s*accTitle\s*:\s*(?P<text>\S.*)")
_DESCRIPTION = re.compile(r"\s*accDescr\s*:\s*(?P<text>\S.*)")
_DESCRIPTION_BLOCK = re.compile(r"\s*accDescr\s*\{(?P<text>.*)")
_BLOCK_END = "}"


@dataclass(frozen=True, slots=True)
class DiagramText:
    """What a diagram's `accTitle` and `accDescr` say; empty for a line it lacks."""

    title: str
    description: str


def svg_file(position: int, theme: str) -> str:
    """The SVG drawing of the guide's `position`-th diagram, from 1, in `theme`: `1-light.svg`."""
    return f"{position}-{theme}.svg"


def is_svg_file(name: str) -> bool:
    return _SVG_FILE.fullmatch(name) is not None


def svg_marker(source: str) -> str:
    return f"<!-- svg-of-mermaid sha256:{mermaid_digest(source)} -->"


def svg_digest(svg: str) -> str | None:
    """The hash on an SVG drawing's first line; None without the marker."""
    first = svg.split("\n", 1)[0]
    marker = _SVG_MARKER.fullmatch(first.strip())
    return marker["digest"] if marker else None


def svg_size(svg: str) -> tuple[int, int] | None:
    """The width and height of an SVG drawing's root element, in pixels."""
    found = _SVG_SIZE.search(svg)
    return (int(found["width"]), int(found["height"])) if found else None


def diagram_text(source: str) -> DiagramText:
    """`accTitle: …`, and `accDescr: …` or a `accDescr { … }` block, joined into one line."""
    title = ""
    description: list[str] = []
    inside = False
    for line in source.splitlines():
        if inside:
            text, closed = line.split(_BLOCK_END, 1)[0], _BLOCK_END in line
            description.append(text.strip())
            inside = not closed
        elif found := _TITLE.fullmatch(line):
            title = found["text"].strip()
        elif found := _DESCRIPTION.fullmatch(line):
            description = [found["text"].strip()]
        elif found := _DESCRIPTION_BLOCK.fullmatch(line):
            rest = found["text"]
            description = [rest.split(_BLOCK_END, 1)[0].strip()]
            inside = _BLOCK_END not in rest
    return DiagramText(title, " ".join(part for part in description if part))


@dataclass(frozen=True, slots=True)
class Fence:
    start: int
    """Line index of the opening fence."""
    end: int
    """Line index of the closing fence; the number of lines when it never closes."""
    info: str
    lines: tuple[str, ...]
    closed: bool = True

    @property
    def language(self) -> str:
        words = self.info.split()
        return words[0] if words else ""

    @property
    def argument(self) -> str | None:
        """The word after the language: an example's path."""
        words = self.info.split()
        return words[1] if len(words) > 1 else None

    @property
    def content(self) -> str:
        """The lines between the fences, each ended by a line feed."""
        return "".join(f"{line}\n" for line in self.lines)


@dataclass(frozen=True, slots=True)
class TextDrawing:
    marker_line: int
    digest: str
    fence: Fence


def mermaid_digest(source: str) -> str:
    """The SHA-256 of a `mermaid` block's content, in lowercase hex."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def text_marker(source: str) -> str:
    return f"<!-- text-of-mermaid sha256:{mermaid_digest(source)} -->"


def is_text_marker(line: str) -> bool:
    """Whether the line is a text drawing's marker, whatever its hash."""
    return _MARKER.fullmatch(line.strip()) is not None


class GuideMarkdown:
    def __init__(self, text: str) -> None:
        self.lines = tuple(text.splitlines())
        self.fences = tuple(_fences(self.lines))
        self._fence_at = {fence.start: fence for fence in self.fences}

    def example_fences(self) -> tuple[Fence, ...]:
        return tuple(
            fence
            for fence in self.fences
            if fence.language != OUTPUT and _names_example(fence.argument)
        )

    def output_fences(self) -> tuple[Fence, ...]:
        return tuple(
            fence
            for fence in self.fences
            if fence.language == OUTPUT and _names_example(fence.argument)
        )

    def mermaid_fences(self) -> tuple[Fence, ...]:
        return tuple(fence for fence in self.fences if fence.info.strip() == MERMAID)

    def text_drawing(self, diagram: Fence) -> TextDrawing | None:
        """The marker on the next line that is not blank, and the `text` block right after it."""
        index = self._next_non_blank(diagram.end + 1)
        if index is None:
            return None
        marker = _MARKER.fullmatch(self.lines[index].strip())
        drawing = self._fence_at.get(index + 1)
        if marker is None or drawing is None or drawing.info.strip() != TEXT:
            return None
        return TextDrawing(index, marker["digest"], drawing)

    def stray_markers(self) -> tuple[int, ...]:
        """Line indexes of markers, outside fences, that follow no diagram."""
        owned = {
            drawing.marker_line
            for diagram in self.mermaid_fences()
            if (drawing := self.text_drawing(diagram)) is not None
        }
        return tuple(
            index
            for index in self._outside_fences()
            if _MARKER.fullmatch(self.lines[index].strip()) and index not in owned
        )

    def terminal_text(self) -> str:
        """The guide as `cstudy learn` shows it: each diagram that has a text drawing leaves out
        its `mermaid` block, the blank lines after it and its marker."""
        hidden: set[int] = set()
        for diagram in self.mermaid_fences():
            drawing = self.text_drawing(diagram)
            if drawing is not None:
                hidden.update(range(diagram.start, drawing.marker_line + 1))
        return "".join(f"{line}\n" for index, line in enumerate(self.lines) if index not in hidden)

    def _next_non_blank(self, start: int) -> int | None:
        return next(
            (index for index in range(start, len(self.lines)) if self.lines[index].strip()), None
        )

    def _outside_fences(self) -> Iterator[int]:
        inside = {index for fence in self.fences for index in range(fence.start, fence.end + 1)}
        return (index for index in range(len(self.lines)) if index not in inside)


def _names_example(argument: str | None) -> bool:
    return argument is not None and argument.startswith(EXAMPLES_PREFIX)


def _fences(lines: tuple[str, ...]) -> Iterator[Fence]:
    index = 0
    while index < len(lines):
        opening = _OPENING.fullmatch(lines[index])
        if opening is None or (opening["marker"][0] == "`" and "`" in opening["info"]):
            index += 1
            continue
        marker = opening["marker"]
        end = _closing(lines, index + 1, marker)
        stop = len(lines) if end is None else end
        info = opening["info"].strip()
        yield Fence(index, stop, info, lines[index + 1 : stop], closed=end is not None)
        index = stop + 1


def _closing(lines: tuple[str, ...], start: int, marker: str) -> int | None:
    for index in range(start, len(lines)):
        line = lines[index].rstrip()
        if line and set(line) == {marker[0]} and len(line) >= len(marker):
            return index
    return None
