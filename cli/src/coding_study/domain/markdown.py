"""Sections of the Markdown content files (problem.md, explanation.md).

Only ATX headings (`## Title`) count; headings inside fenced code blocks are ignored.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_HEADING = re.compile(r"(?P<hashes>#{1,6})[ \t]+(?P<title>.*?)[ \t#]*")
_FENCE_MARKERS = ("```", "~~~")


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    title: str
    level: int
    start: int
    """Line index of the heading."""
    end: int
    """Line index after the section: the next heading of the same or a higher level."""
    body: tuple[str, ...]
    """The lines after the heading, including subsections."""

    @property
    def text(self) -> str:
        return "\n".join(self.body).strip()

    @property
    def intro(self) -> str:
        """The text before the first subsection."""
        lines: list[str] = []
        for line in _outside_fences(self.body):
            if line.heading_level:
                break
            lines.append(line.text)
        return "\n".join(lines).strip()


@dataclass(frozen=True, slots=True)
class _Line:
    index: int
    text: str
    heading_level: int
    title: str


class MarkdownDocument:
    def __init__(self, text: str) -> None:
        self.lines = tuple(text.splitlines())
        self._headings = tuple(line for line in _outside_fences(self.lines) if line.heading_level)

    @property
    def title(self) -> str | None:
        return next((line.title for line in self._headings if line.heading_level == 1), None)

    def sections(
        self, level: int, parent: MarkdownSection | None = None
    ) -> tuple[MarkdownSection, ...]:
        """Sections at `level`, in order, optionally only those inside `parent`."""
        start, end = (parent.start + 1, parent.end) if parent else (0, len(self.lines))
        headings = [line for line in self._headings if start <= line.index < end]
        return tuple(
            self._section(heading, headings[position + 1 :], end)
            for position, heading in enumerate(headings)
            if heading.heading_level == level
        )

    def section(self, title: str, parent: MarkdownSection | None = None) -> MarkdownSection | None:
        """The first section titled `title`: level 2, or one level below `parent`."""
        level = parent.level + 1 if parent else 2
        return next(
            (section for section in self.sections(level, parent) if section.title == title), None
        )

    def _section(self, heading: _Line, later: list[_Line], limit: int) -> MarkdownSection:
        end = next(
            (line.index for line in later if line.heading_level <= heading.heading_level), limit
        )
        return MarkdownSection(
            title=heading.title,
            level=heading.heading_level,
            start=heading.index,
            end=end,
            body=self.lines[heading.index + 1 : end],
        )


def _outside_fences(lines: tuple[str, ...]) -> Iterator[_Line]:
    """Every line, with heading information only for headings outside code fences."""
    in_fence = False
    for index, text in enumerate(lines):
        if text.lstrip().startswith(_FENCE_MARKERS):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.fullmatch(text)
        if heading is None:
            yield _Line(index, text, 0, "")
        else:
            yield _Line(index, text, len(heading["hashes"]), heading["title"])
