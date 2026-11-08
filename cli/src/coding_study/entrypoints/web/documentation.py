"""Documentation as the page may insert it (docs/specs/web-ui.md#documentation): the HTML of a
hover's `contents` or of a `documentation` field, which the broker sends as
`{"kind": "cstudy-html", "value": <html>}` in place of the server's value.

Markdown is rendered with raw HTML as text, plain text is escaped, and a value that renders to
nothing is None. Nothing else a server sends is HTML.
"""

import html
from typing import cast

from coding_study.entrypoints.web.markdown import (
    LibraryLinks,
    no_library,
    render_code_block,
    render_documentation_markdown,
)

CSTUDY_HTML = "cstudy-html"
SEPARATOR = "<hr>\n"
MARKDOWN = "markdown"


def hover_html(contents: object, opens_library: LibraryLinks = no_library) -> str | None:
    """A hover's `contents`: a `MarkupContent`, a `MarkedString` (a string, which is markdown, or
    a language and a value, which is code), or a list of them, each rendered in order and
    separated by a rule; None when nothing is left. A markdown link that `opens_library` accepts
    becomes a button that opens the library file (docs/specs/web-ui.md#hover)."""
    parts = cast(list[object], contents) if isinstance(contents, list) else [contents]
    rendered = [found for part in parts if (found := _marked(part, opens_library)) is not None]
    return SEPARATOR.join(rendered) or None


def documentation_html(value: object) -> str | None:
    """A `documentation` field: a string, which is plain text, or a `MarkupContent`, whose links
    to files are their text."""
    if isinstance(value, str):
        return _plain(value)
    fields = _fields(value)
    text = fields.get("value")
    return _markup(fields.get("kind"), text, no_library) if isinstance(text, str) else None


def _marked(part: object, opens_library: LibraryLinks) -> str | None:
    if isinstance(part, str):
        return _markdown(part, opens_library)
    fields = _fields(part)
    text = fields.get("value")
    if not isinstance(text, str):
        return None
    language = fields.get("language")
    if isinstance(language, str):
        return render_code_block(text, language) if text.strip() else None
    return _markup(fields.get("kind"), text, opens_library)


def _markup(kind: object, text: str, opens_library: LibraryLinks) -> str | None:
    """A kind other than markdown is plain text, which cannot do harm."""
    return _markdown(text, opens_library) if kind == MARKDOWN else _plain(text)


def _markdown(text: str, opens_library: LibraryLinks) -> str | None:
    rendered = render_documentation_markdown(text, opens_library)
    return rendered if rendered.strip() else None


def _plain(text: str) -> str | None:
    return f'<pre class="doc-plain">{html.escape(text)}</pre>' if text.strip() else None


def _fields(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}
