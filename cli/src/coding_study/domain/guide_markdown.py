"""How a guide.md reads (docs/specs/guides.md#guidemd): its fenced blocks, the examples and their
outputs, the Mermaid diagrams and their text drawings, and the text `cstudy learn` shows.

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
_OPENING = re.compile(r"(?P<marker>`{3,}|~{3,})(?P<info>.*)")
_MARKER = re.compile(r"<!-- text-of-mermaid sha256:(?P<digest>[0-9a-f]{64}) -->")


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
