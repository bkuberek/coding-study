"""Hints: the `### Hint <n>` subsections of `## Hints` in problem.md (docs/specs/authoring.md).

They never appear in the rendered statement; `cstudy hint` reveals them one at a time.
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
