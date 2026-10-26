"""rubric.md: criteria for self-review after `cstudy done` (docs/specs/authoring.md#rubricmd).

A rubric is a Markdown file whose `##` sections are either checklists of `- [ ] <criterion>`
items or prose. Low-level design problems require `LLD_RUBRIC_SECTIONS` (`rubric_issues`);
non-autograded items (docs/specs/content.md) name their own areas, every one a checklist, under
a fixed title (`item_rubric_issues`).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from coding_study.domain.markdown import MarkdownDocument

PLACEHOLDER = "TODO"
RUBRIC_TITLE_SUFFIX = ": Rubric"
"""Every rubric is titled `# <title>: Rubric`."""
AREA_LEVEL = 2
_CRITERION = re.compile(r"\s*- \[ \] (?P<text>\S.*)")
_FENCE_MARKERS = ("```", "~~~")


@dataclass(frozen=True, slots=True)
class RubricSection:
    title: str
    checklist: bool = True
    """Checklist sections need a `- [ ] <criterion>` item; prose sections need any text."""


LLD_RUBRIC_SECTIONS = (
    RubricSection("Responsibilities"),
    RubricSection("Extension points"),
    RubricSection("Patterns"),
    RubricSection("Testability"),
    RubricSection("Reference design", checklist=False),
)
"""Design criteria for self-review, then the reference design `cstudy solution` reveals."""


@dataclass(frozen=True, slots=True)
class RubricArea:
    title: str
    criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Rubric:
    title: str | None
    areas: tuple[RubricArea, ...]

    @property
    def criteria_count(self) -> int:
        return sum(len(area.criteria) for area in self.areas)


def parse_rubric(markdown: str) -> Rubric:
    document = MarkdownDocument(markdown)
    areas = tuple(
        RubricArea(section.title, _criteria(section.body))
        for section in document.sections(AREA_LEVEL)
    )
    return Rubric(document.title, areas)


def rubric_issues(text: str, sections: Sequence[RubricSection]) -> tuple[str, ...]:
    """Missing, empty, out-of-order or placeholder sections, in `sections` order.

    Other `##` sections are allowed anywhere.
    """
    found = {section.title: section for section in MarkdownDocument(text).sections(AREA_LEVEL)}
    issues: list[str] = []
    for required in sections:
        section = found.get(required.title)
        if section is None:
            issues.append(f'missing "## {required.title}"')
        elif required.checklist and not _criteria(section.body):
            issues.append(f'"## {required.title}" needs at least one "- [ ] <criterion>" item')
        elif not section.text:
            issues.append(f'"## {required.title}" is empty')
        elif PLACEHOLDER in section.text:
            issues.append(f'"## {required.title}" contains {PLACEHOLDER}')
    positions = [
        (required.title, found[required.title].start)
        for required in sections
        if required.title in found
    ]
    for (title, start), (later_title, later_start) in pairwise(positions):
        if later_start < start:
            issues.append(f'"## {title}" must come before "## {later_title}"')
    return tuple(issues)


def rubric_skeleton(title: str, sections: Sequence[RubricSection]) -> str:
    """A rubric.md for `cstudy new`: `sections` in order, each with a `PLACEHOLDER` to replace."""
    parts = [f"# {title}{RUBRIC_TITLE_SUFFIX}"]
    for section in sections:
        body = (
            f"- [ ] {PLACEHOLDER}: a criterion a reviewer can tick against their own code."
            if section.checklist
            else f"{PLACEHOLDER}: the reference design, in prose."
        )
        parts += [f"## {section.title}", body]
    return "\n\n".join(parts) + "\n"


def item_rubric_issues(text: str, title: str) -> tuple[str, ...]:
    """Why `text` is not an item rubric titled `title`: any areas, each with a criterion."""
    rubric = parse_rubric(text)
    issues: list[str] = []
    if rubric.title != title:
        issues.append(f'title "{rubric.title}" must be "{title}"')
    if not rubric.areas:
        issues.append('needs at least one "## <area>" section with "- [ ] <criterion>" lines')
    issues += [
        f'"## {area.title}" has no "- [ ] <criterion>" line'
        for area in rubric.areas
        if not area.criteria
    ]
    return tuple(issues)


def _criteria(lines: Sequence[str]) -> tuple[str, ...]:
    """The `- [ ] <criterion>` texts outside code fences."""
    criteria: list[str] = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith(_FENCE_MARKERS):
            in_fence = not in_fence
        criterion = None if in_fence else _CRITERION.fullmatch(line)
        if criterion:
            criteria.append(criterion["text"].strip())
    return tuple(criteria)
