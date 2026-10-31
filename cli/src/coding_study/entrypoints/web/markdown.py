"""Markdown as the page shows it: rendered on the server, raw HTML left as text, code blocks
highlighted by Pygments with classes the page's stylesheet colours (docs/specs/web-ui.md#security,
docs/specs/web-ui.md#front-end-assets). Nothing in the output carries a `style` attribute, which
the page's Content Security Policy would refuse."""

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import find_lexer_class_by_name
from pygments.util import ClassNotFound

TOKEN_CLASS_PREFIX = "tok-"
"""`<span class="tok-k">`: the stylesheet colours each Pygments token class under this prefix."""
_FORMATTER: HtmlFormatter[str] = HtmlFormatter(nowrap=True, classprefix=TOKEN_CLASS_PREFIX)
STYLE = "style"
TEXT_ALIGN = "text-align:"
ALIGNED_CELLS = frozenset({"th_open", "td_open"})


def render_markdown(text: str) -> str:
    return _RENDERER.render(text)


def _highlighted(code: str, language: str, _attributes: str) -> str:
    """The highlighted code without its `<pre>`, which markdown-it adds; "" lets markdown-it
    escape a block in a language Pygments does not know."""
    if not language:
        return ""
    try:
        lexer = find_lexer_class_by_name(language)()
    except ClassNotFound:
        return ""
    return highlight(code, lexer, _FORMATTER)


def _alignment_classes(state: StateCore) -> None:
    """A table column's alignment as a class (`align-right`) instead of the `style` attribute
    markdown-it gives it."""
    for token in state.tokens:
        style = token.attrs.pop(STYLE, None)
        if token.type in ALIGNED_CELLS and isinstance(style, str):
            token.attrSet("class", f"align-{style.removeprefix(TEXT_ALIGN)}")


_RENDERER = MarkdownIt("commonmark", {"html": False, "highlight": _highlighted}).enable(
    ["table", "strikethrough"]
)
_RENDERER.core.ruler.push("alignment_classes", _alignment_classes)
