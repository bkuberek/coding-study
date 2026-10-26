"""What `cstudy start` writes for a non-autograded item: the rendered prompt and the notes file.

The statement (`.statements/<slug>.md`) is prompt.md with a metadata line, followed by
the change under review for code review items and the study guides found under the user's
study-guides root. The notes file is the item's template.md with a header comment, like the
header of a generated stub.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from coding_study.domain.attempts import Rating
from coding_study.domain.items import GuideLink, ItemMeta
from coding_study.domain.layout import statement_path

STATEMENT_FOOTER = (
    "<!-- Rendered by cstudy from the item's prompt.md; edits here are overwritten. -->"
)
CHANGE_SECTION = "## Change"
FILES_SECTION = "## Files"
GUIDES_SECTION = "## Study guides"
DIFF_FENCE = "diff"
PLAIN_FENCE = "text"
_RATINGS = "|".join(Rating)


@dataclass(frozen=True, slots=True)
class ChangeFile:
    name: str
    """Relative to the item's `files/` directory."""
    text: str


@dataclass(frozen=True, slots=True)
class Change:
    """A code review item's change: `change.diff`, or the files in `files/`."""

    diff: str | None = None
    files: tuple[ChangeFile, ...] = ()


@dataclass(frozen=True, slots=True)
class ItemStatementParts:
    """What the statement shows besides the item's metadata."""

    prompt: str | None = None
    """prompt.md; None when the item has none."""
    change: Change = Change()
    guides: tuple[GuideLink, ...] = ()
    """Only the study guides found under the user's study-guides root."""


def render_item_statement(meta: ItemMeta, parts: ItemStatementParts) -> str:
    lines = [
        *_prompt_lines(meta, parts.prompt or ""),
        *_change_lines(parts.change),
        *_guide_lines(parts.guides),
    ]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join((*lines, "", STATEMENT_FOOTER)) + "\n"


def notes_text(meta: ItemMeta, template: str) -> str:
    """The new notes file: a header comment, then the template."""
    header = (
        f"<!-- {meta.title}. Prompt: {statement_path(meta.slug)}. "
        f"Then: cstudy solution {meta.slug}, cstudy done --rating {_RATINGS} -->"
    )
    return f"{header}\n\n{template}"


def metadata_line(meta: ItemMeta) -> str:
    return f"{meta.difficulty} · {meta.track} · {meta.estimate_minutes} min"


def _prompt_lines(meta: ItemMeta, prompt: str) -> Iterator[str]:
    lines = prompt.splitlines()
    titled = bool(lines) and lines[0].startswith("# ")
    if titled:
        yield lines.pop(0)
    else:
        yield f"# {meta.title}"
    yield from ("", metadata_line(meta))
    if lines and lines[0].strip():
        yield ""
    yield from lines


def _change_lines(change: Change) -> Iterator[str]:
    if change.diff is not None:
        yield from ("", CHANGE_SECTION, "", *_fenced(DIFF_FENCE, change.diff))
    if change.files:
        yield from ("", FILES_SECTION)
    for file in change.files:
        yield from ("", f"### {file.name}", "", *_fenced(_fence_of(file.name), file.text))


def _guide_lines(guides: tuple[GuideLink, ...]) -> Iterator[str]:
    if guides:
        yield from ("", GUIDES_SECTION, "")
    for guide in guides:
        yield f"- [{guide.reference}]({guide.target})"


def _fenced(info: str, text: str) -> tuple[str, ...]:
    return (f"```{info}", *text.rstrip("\n").splitlines(), "```")


def _fence_of(name: str) -> str:
    """The extension names the code block's language; files without one are plain text."""
    _, dot, extension = name.rpartition(".")
    return extension if dot and extension else PLAIN_FENCE
