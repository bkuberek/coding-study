"""Markdown as the page shows it: rendered on the server, raw HTML left as text, code blocks
highlighted by Pygments with classes the page's stylesheet colours (docs/specs/web-ui.md#security,
docs/specs/web-ui.md#front-end-assets). Nothing in the output carries a `style` attribute, which
the page's Content Security Policy would refuse.

The documentation a language server sends (docs/specs/web-ui.md#documentation) is rendered the
same way, except that an image is its alt text and only a web link stays a link.
"""

from collections.abc import Sequence

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
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
WEB_LINKS = ("http://", "https://")
OPENS_ELSEWHERE = {"rel": "noopener noreferrer", "target": "_blank"}
"""What a web link in documentation carries, so the practice page stays where it is and sends no
referrer."""


def render_markdown(text: str) -> str:
    return _RENDERER.render(text)


def render_documentation_markdown(text: str) -> str:
    return _DOCUMENTATION.render(text)


def render_code_block(code: str, language: str) -> str:
    """A fenced block in `language`, as markdown renders one; the code cannot close it."""
    fence = Token("fence", "code", 0, info=language, content=f"{code}\n")
    return _DOCUMENTATION.renderer.render([fence], _DOCUMENTATION.options, {})


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


def _plain_links_and_images(state: StateCore) -> None:
    """An image becomes its alt text, a link that is not a web link its text, and a web link
    opens elsewhere. Needs `validateLink` to accept every link, or markdown would leave the ones
    it refuses (`file:`, `javascript:`) as the source text."""
    for block in state.tokens:
        if block.type == "inline" and block.children is not None:
            block.children = _without_unsafe_links(block.children)


def _without_unsafe_links(tokens: Sequence[Token]) -> list[Token]:
    kept: list[Token] = []
    dropped: list[bool] = []
    for token in tokens:
        if token.type == "link_open":
            href = token.attrGet("href")
            is_web = isinstance(href, str) and href.lower().startswith(WEB_LINKS)
            dropped.append(not is_web)
            if is_web:
                token.attrs.update(OPENS_ELSEWHERE)
                kept.append(token)
        elif token.type == "link_close":
            if not dropped.pop():
                kept.append(token)
        elif token.type == "image":
            kept.append(_alt_text(token))
        else:
            kept.append(token)
    return kept


def _alt_text(image: Token) -> Token:
    text = Token("text", "", 0)
    parts = image.children or []
    text.content = "".join(part.content if part.type != "softbreak" else " " for part in parts)
    return text


def _accept_every_link(url: str) -> bool:
    return True


_RENDERER = MarkdownIt("commonmark", {"html": False, "highlight": _highlighted}).enable(
    ["table", "strikethrough"]
)
_RENDERER.core.ruler.push("alignment_classes", _alignment_classes)
_DOCUMENTATION = MarkdownIt("commonmark", {"html": False, "highlight": _highlighted}).enable(
    ["table", "strikethrough"]
)
_DOCUMENTATION.validateLink = _accept_every_link
_DOCUMENTATION.core.ruler.push("alignment_classes", _alignment_classes)
_DOCUMENTATION.core.ruler.push("plain_links_and_images", _plain_links_and_images)
