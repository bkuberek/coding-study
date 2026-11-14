"""The user docs (docs/specs/user-docs.md): how to use `cstudy`, one Markdown page per topic in
`user-docs/`, each with front matter, read with `cstudy docs` and in the web UI's Docs view.

Not to be confused with the concept guides of `domain/concept_guides.py`, which teach an idea.
"""

import difflib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from coding_study.domain.markdown import MarkdownDocument

DOCS_DIRECTORY = "user-docs"
PAGE_SUFFIX = ".md"
FRONT_MATTER_FENCE = "---"
PAGE_HEADINGS = (2, 3)
"""The heading levels a page lists and the search reads: `##` and `###`."""
_SUGGESTIONS = 3
_SUGGESTION_CUTOFF = 0.6
_LINK = re.compile(r"!?\[(?P<text>[^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"\*\*|\*|~~")
_NOT_IN_ID = re.compile(r"[^\w\- ]")
"""What GitHub leaves out of a heading's id: anything but letters, digits, `_`, `-` and spaces."""
_FENCE = re.compile(r"\s*(```|~~~)")
_TABLE_RULE = re.compile(r"\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*")
_DROPPED_MARKS = re.compile(r"[`*]|~~")
_SPACED_MARKS = re.compile(r"[|>#]")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class DocHeading:
    id: str
    """GitHub's id of the heading, which a deep link names (`nodejs-and-pnpm`)."""
    title: str
    """Its text without Markdown's marks."""
    level: int


@dataclass(frozen=True, slots=True)
class DocPassage:
    """A part of a page the Docs view's search reads: the opening, or one section."""

    id: str
    """The heading's id; empty for the opening."""
    title: str
    text: str
    """Plain text, without Markdown's marks."""


@dataclass(frozen=True, slots=True)
class DocPage:
    slug: str
    """The file's name without `.md`."""
    title: str
    summary: str
    section: str
    order: int
    markdown: str
    """The page after its front matter."""
    first_line: int = 0
    """How many lines of the file come before `markdown`, for line numbers."""

    @property
    def headings(self) -> tuple[DocHeading, ...]:
        """The `##` and `###` headings, in order."""
        return tuple(
            heading for heading in heading_ids(self.markdown) if heading.level in PAGE_HEADINGS
        )

    @property
    def passages(self) -> tuple[DocPassage, ...]:
        """The opening, with the summary, then each `##` and `###` section without its own
        subsections."""
        opening, sections = _split_at_headings(self.markdown)
        first = DocPassage("", self.title, _plain(f"{self.summary}\n{opening}"))
        rest = (DocPassage(heading.id, heading.title, _plain(text)) for heading, text in sections)
        return (first, *rest)


def split_front_matter(text: str) -> tuple[str, str, int] | None:
    """The YAML between the opening and closing `---`, the page after it, and how many lines come
    before the page; None when the file does not start with front matter that closes."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != FRONT_MATTER_FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == FRONT_MATTER_FENCE:
            return "".join(lines[1:index]), "".join(lines[index + 1 :]), index + 1
    return None


def heading_id(title: str) -> str:
    """GitHub's id of a heading: its text in lower case, without the characters that are not
    letters, digits, spaces, hyphens or underscores, its spaces turned into hyphens."""
    return _NOT_IN_ID.sub("", heading_title(title).lower()).replace(" ", "-")


def heading_title(source: str) -> str:
    """A heading's text without Markdown's marks: a link's text, code without its backticks."""
    text = _LINK.sub(lambda link: link["text"], source)
    return _EMPHASIS.sub("", text.replace("`", "")).strip()


def heading_ids(markdown: str) -> tuple[DocHeading, ...]:
    """Every heading outside code, of every level, in order, with its id; a repeated id gets
    `-1`, `-2`, as on GitHub."""
    return tuple(heading for _index, heading in _numbered_headings(markdown))


def in_sections(pages: Iterable[DocPage]) -> tuple[tuple[str, tuple[DocPage, ...]], ...]:
    """The pages by `order`, grouped by section, each section where its first page is."""
    grouped: dict[str, list[DocPage]] = {}
    for page in sorted(pages, key=lambda page: page.order):
        grouped.setdefault(page.section, []).append(page)
    return tuple((section, tuple(members)) for section, members in grouped.items())


def unknown_topic_message(slug: str, known: Iterable[str]) -> str:
    """`unknown topic "x"; did you mean y?`, or where to find the list."""
    near = difflib.get_close_matches(slug, list(known), _SUGGESTIONS, _SUGGESTION_CUTOFF)
    hint = f"did you mean {', '.join(near)}?" if near else "cstudy docs lists the topics"
    return f'unknown topic "{slug}"; {hint}'


def _numbered_headings(markdown: str) -> list[tuple[int, DocHeading]]:
    """Each heading outside code with the index of its line, in order."""
    document = MarkdownDocument(markdown)
    lines = sorted(
        (section.start, level, section.title)
        for level in range(1, 7)
        for section in document.sections(level)
    )
    seen: dict[str, int] = {}
    found: list[tuple[int, DocHeading]] = []
    for index, level, source in lines:
        base = heading_id(source)
        count = seen.get(base, 0)
        seen[base] = count + 1
        heading = DocHeading(
            base if count == 0 else f"{base}-{count}", heading_title(source), level
        )
        found.append((index, heading))
    return found


def _split_at_headings(markdown: str) -> tuple[str, list[tuple[DocHeading, str]]]:
    """The text after the `# ` title and before the first `##` or `###`, then each of those
    headings with its text up to the next one."""
    lines = markdown.splitlines()
    numbered = _numbered_headings(markdown)
    starts = [(index, heading) for index, heading in numbered if heading.level in PAGE_HEADINGS]
    title_end = next((index + 1 for index, heading in numbered if heading.level == 1), 0)
    first = starts[0][0] if starts else len(lines)
    parts: list[tuple[DocHeading, str]] = []
    for position, (index, heading) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        parts.append((heading, "\n".join(lines[index + 1 : end])))
    return "\n".join(lines[title_end:first]), parts


def _plain(markdown: str) -> str:
    """Text without fences, table rules, links' addresses or Markdown's marks, its spaces
    collapsed."""
    kept = [
        line
        for line in markdown.splitlines()
        if not _FENCE.match(line) and not _TABLE_RULE.fullmatch(line)
    ]
    text = _LINK.sub(lambda link: link["text"], "\n".join(kept))
    text = _SPACED_MARKS.sub(" ", _DROPPED_MARKS.sub("", text))
    return _SPACES.sub(" ", text).strip()
