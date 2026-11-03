"""The header at the top of a starter file: the problem's title, its statement and the command
that runs it, wrapped so that no line passes 100 columns
(docs/specs/runners.md#stub-generation).

A header that fits stays on one line. Otherwise it breaks between its three sentences, filling
each line; only a title too long for a line of its own breaks between words. The statement's
path and the run command are never split.
"""

from coding_study.domain.layout import statement_path

COLUMN_LIMIT = 100
LINE_COMMENT = "// "


def sentences(title: str, slug: str) -> tuple[str, str, str]:
    """The title (which ends its sentence), the statement and the run command."""
    return title, f"Statement: {statement_path(slug)}.", f"Run: cstudy test {slug}"


def comment_header(title: str, slug: str) -> list[str]:
    """`// ` comment lines, each within the column limit."""
    width = COLUMN_LIMIT - len(LINE_COMMENT)
    return [f"{LINE_COMMENT}{line}" for line in wrapped(sentences(title, slug), width)]


def wrapped(parts: tuple[str, ...], width: int) -> list[str]:
    """`parts` joined by spaces on one line when that fits `width`, else packed line by line."""
    if len(" ".join(parts)) <= width:
        return [" ".join(parts)]
    lines: list[str] = []
    for unit in _units(parts, width):
        if lines and len(lines[-1]) + 1 + len(unit) <= width:
            lines[-1] += f" {unit}"
        else:
            lines.append(unit)
    return lines


def _units(parts: tuple[str, ...], width: int) -> list[str]:
    """Each part whole, except a part wider than `width` that has spaces, which gives its words."""
    return [unit for part in parts for unit in (part.split() if len(part) > width else [part])]
