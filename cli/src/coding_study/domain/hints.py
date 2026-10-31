"""Hints: the `### Hint <n>` subsections of `## Hints` in problem.md (docs/specs/authoring.md).

They never appear in the rendered statement; `cstudy hint` reveals them one at a time. A project
problem's hints open with its levels: they spread evenly over the levels in order, so hint 1 is
open from the start and the last hint opens no later than the last level.
"""

from coding_study.domain.markdown import MarkdownDocument
from coding_study.domain.static_checks import HINTS_SECTION


def problem_hints(problem_markdown: str) -> tuple[str, ...]:
    """Every hint's text, most general first; `cstudy verify` checks the numbering."""
    document = MarkdownDocument(problem_markdown)
    section = document.section(HINTS_SECTION)
    if section is None:
        return ()
    return tuple(hint.text for hint in document.sections(section.level + 1, section))


def hint_level(number: int, hint_count: int, level_count: int) -> int:
    """The level whose opening reveals hint `number` (from 1) of `hint_count`."""
    return (number - 1) * level_count // hint_count + 1
