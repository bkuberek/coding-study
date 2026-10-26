"""The sections of solutions/explanation.md (docs/specs/authoring.md#explanationmd).

Every approach has one `## Approach: <id> (<name>)` section; `## Overview` holds the table.
"""

import re
from dataclasses import dataclass

from coding_study.domain.markdown import MarkdownDocument, MarkdownSection

OVERVIEW_SECTION = "Overview"
_APPROACH_TITLE = re.compile(r"Approach: (?P<id>\S+)(?: \((?P<name>.*)\))?")
_BROKEN_TITLE = re.compile(r"Broken: (?P<id>\S+)(?: \((?P<name>.*)\))?")


@dataclass(frozen=True, slots=True)
class ApproachSection:
    approach_id: str
    name: str | None
    section: MarkdownSection


@dataclass(frozen=True, slots=True)
class BrokenSection:
    """`## Broken: <id> (<name>)`: a concurrent problem's deliberately broken reference."""

    broken_id: str
    name: str | None
    section: MarkdownSection


class Explanation:
    def __init__(self, text: str) -> None:
        self.document = MarkdownDocument(text)

    @property
    def overview(self) -> MarkdownSection | None:
        return self.document.section(OVERVIEW_SECTION)

    def approaches(self) -> tuple[ApproachSection, ...]:
        """Approach sections in file order."""
        return tuple(
            ApproachSection(heading["id"], heading["name"], section)
            for section in self.document.sections(2)
            if (heading := _APPROACH_TITLE.fullmatch(section.title))
        )

    def broken(self) -> tuple[BrokenSection, ...]:
        """Broken-reference sections in file order."""
        return tuple(
            BrokenSection(heading["id"], heading["name"], section)
            for section in self.document.sections(2)
            if (heading := _BROKEN_TITLE.fullmatch(section.title))
        )

    def approach(self, approach_id: str) -> ApproachSection | None:
        return next(
            (found for found in self.approaches() if found.approach_id == approach_id), None
        )

    def section_text(self, section: MarkdownSection) -> str:
        """The section with its heading, as written."""
        return "\n".join(self.document.lines[section.start : section.end]).strip()
