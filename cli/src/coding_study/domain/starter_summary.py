"""The short summary in a starter's header (docs/specs/problem-format.md#starter-header).

It is the `summary` of `meta.yaml` when the problem has one; otherwise the opening of the
statement: the sentences of its first paragraph that fit a character cap, with the Markdown
taken out. A sentence is never cut: a first sentence over the cap, a paragraph that introduces a
list and a statement that opens with one give no summary, and the header then goes without.
"""

import re

from coding_study.domain.markdown import MarkdownDocument
from coding_study.domain.problem import ProblemMeta

SUMMARY_LIMIT = 200
"""Characters; at most three lines of the header."""
STATEMENT_SECTION = "Statement"
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_NOT_PROSE = re.compile(r"\s*(?:[-*+]\s|>|\||#|<|\d+[.)]\s|```|~~~)")
_SENTENCE_BREAK = re.compile(r"(?<=[.?!])\s+")
_SENTENCE_END = re.compile(r"[.?!][\"')\]]*$")
_ABBREVIATIONS = ("e.g.", "i.e.", "vs.", "approx.")
_HELD = re.compile(r"\x00(\d+)\x00")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|<>])")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_OR_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = (
    re.compile(r"\*\*(.+?)\*\*"),
    re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"),
    re.compile(r"(?<!\w)__(.+?)__(?!\w)"),
    re.compile(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)"),
)
_TAG = re.compile(r"</?[A-Za-z][^>]*>")


def starter_summary(meta: ProblemMeta, problem_markdown: str) -> str | None:
    """`meta.summary`, else the opening of the statement in `problem_markdown`."""
    if meta.summary is not None:
        return " ".join(meta.summary.split())
    return statement_summary(problem_markdown)


def statement_summary(problem_markdown: str, limit: int = SUMMARY_LIMIT) -> str | None:
    """The first paragraph of `## Statement` as far as whole sentences fit `limit` characters;
    None when not even the first does."""
    section = MarkdownDocument(problem_markdown).section(STATEMENT_SECTION)
    if section is None:
        return None
    chosen: list[str] = []
    for sentence in _sentences(section.intro):
        if len(" ".join([*chosen, sentence])) > limit:
            break
        chosen.append(sentence)
    return " ".join(chosen) or None


def _sentences(intro: str) -> list[str]:
    """The complete sentences of the first paragraph; none when it is not prose."""
    paragraph = _PARAGRAPH_BREAK.split(intro.strip())[0]
    if _NOT_PROSE.match(paragraph):
        return []
    sentences: list[str] = []
    for piece in _SENTENCE_BREAK.split(_plain(paragraph)):
        if sentences and sentences[-1].endswith(_ABBREVIATIONS):
            sentences[-1] += f" {piece}"
        else:
            sentences.append(piece)
    return [sentence for sentence in sentences if _SENTENCE_END.search(sentence)]


def _plain(markdown: str) -> str:
    """`markdown` as one line of plain words. Code spans and escaped characters are held aside
    while the rest is stripped, so a `*` or `_` inside them is never taken for emphasis."""
    held: list[str] = []

    def hold(text: str) -> str:
        held.append(text)
        return f"\x00{len(held) - 1}\x00"

    text = _CODE_SPAN.sub(lambda found: hold(found[2]), markdown)
    text = _ESCAPE.sub(lambda found: hold(found[1]), text)
    text = _IMAGE_OR_LINK.sub(r"\1", _COMMENT.sub("", text))
    for emphasis in _EMPHASIS:
        text = emphasis.sub(r"\1", text)
    text = _TAG.sub("", text)
    return " ".join(_HELD.sub(lambda found: held[int(found[1])], text).split())
