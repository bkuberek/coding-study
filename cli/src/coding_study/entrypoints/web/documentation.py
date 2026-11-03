"""Documentation as the page may insert it (docs/specs/web-ui.md#documentation): the HTML of a
hover's `contents` or of a `documentation` field, which the broker sends as
`{"kind": "cstudy-html", "value": <html>}` in place of the server's value.

Markdown is rendered with raw HTML as text, plain text is escaped, and a value that renders to
nothing is None. Nothing else a server sends is HTML.
"""

import html
from typing import cast

from coding_study.entrypoints.web.markdown import render_code_block, render_documentation_markdown

CSTUDY_HTML = "cstudy-html"
SEPARATOR = "<hr>\n"
MARKDOWN = "markdown"


def hover_html(contents: object) -> str | None:
    """A hover's `contents`: a `MarkupContent`, a `MarkedString` (a string, which is markdown, or
    a language and a value, which is code), or a list of them, each rendered in order and
    separated by a rule; None when nothing is left."""
    parts = cast(list[object], contents) if isinstance(contents, list) else [contents]
    rendered = [found for part in parts if (found := _marked(part)) is not None]
    return SEPARATOR.join(rendered) or None


def documentation_html(value: object) -> str | None:
    """A `documentation` field: a string, which is plain text, or a `MarkupContent`."""
    if isinstance(value, str):
        return _plain(value)
    fields = _fields(value)
    text = fields.get("value")
    return _markup(fields.get("kind"), text) if isinstance(text, str) else None


def _marked(part: object) -> str | None:
    if isinstance(part, str):
        return _markdown(part)
    fields = _fields(part)
    text = fields.get("value")
    if not isinstance(text, str):
        return None
    language = fields.get("language")
    if isinstance(language, str):
        return render_code_block(text, language) if text.strip() else None
    return _markup(fields.get("kind"), text)


def _markup(kind: object, text: str) -> str | None:
    """A kind other than markdown is plain text, which cannot do harm."""
    return _markdown(text) if kind == MARKDOWN else _plain(text)


def _markdown(text: str) -> str | None:
    rendered = render_documentation_markdown(text)
    return rendered if rendered.strip() else None


def _plain(text: str) -> str | None:
    return f'<pre class="doc-plain">{html.escape(text)}</pre>' if text.strip() else None


def _fields(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}
