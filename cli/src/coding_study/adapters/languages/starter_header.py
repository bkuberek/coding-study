"""The header at the top of a starter file (docs/specs/problem-format.md#starter-header): the
problem's title, a short summary of it, the statement's path and the command that runs it.

It is written over several lines so that no line needs horizontal scrolling: the title and the
summary wrap between words at `TEXT_WIDTH` characters, and the statement's path and the run
command each take a line of their own and are never split.
"""

import textwrap

from coding_study.domain.layout import statement_path
from coding_study.domain.problem import ProblemMeta

TEXT_WIDTH = 68
"""Characters of text in a line, so a line with its `// ` marker stays under 72 columns."""
LINE_COMMENT = "//"
SENTENCE_ENDINGS = (".", "?", "!")


def header_text(meta: ProblemMeta) -> list[str]:
    """The header's lines without a comment marker, the paragraphs set apart by empty lines."""
    paragraphs = [_wrapped(_titled(meta.title))]
    if meta.summary:
        paragraphs.append(_wrapped(meta.summary))
    paragraphs.append([f"Statement: {statement_path(meta.slug)}", f"Run: cstudy test {meta.slug}"])
    lines = [line for paragraph in paragraphs for line in (*paragraph, "")]
    return lines[:-1]


def comment_header(meta: ProblemMeta) -> list[str]:
    """`//` comment lines; an empty line of the header is a bare marker."""
    return [f"{LINE_COMMENT} {line}" if line else LINE_COMMENT for line in header_text(meta)]


def _titled(title: str) -> str:
    return title if title.endswith(SENTENCE_ENDINGS) else f"{title}."


def _wrapped(text: str) -> list[str]:
    return textwrap.wrap(text, TEXT_WIDTH, break_long_words=False, break_on_hyphens=False)
