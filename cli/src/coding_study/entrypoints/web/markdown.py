"""Markdown as the page shows it: rendered on the server, raw HTML left as text, code blocks
highlighted by Pygments with classes the page's stylesheet colours (docs/specs/web-ui.md#security,
docs/specs/web-ui.md#front-end-assets). Nothing in the output carries a `style` attribute, which
the page's Content Security Policy would refuse.

The documentation a language server sends (docs/specs/web-ui.md#documentation) is rendered the
same way, except that an image is its alt text, only a web link stays a link, and a link to a
library file that the caller accepts becomes a button the page opens it with.
"""

from collections.abc import Callable, Sequence
from typing import cast

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
LIBRARY_LINKS = "library_links"
"""The key of the render environment that holds the `LibraryLinks` of a rendering."""
LIBRARY_LINK_CLASS = "cs-library-link"
"""The class of the button a link to a library file becomes, which the page opens in a library
tab at the line its `data-uri` names."""
BUTTON = "button"

type LibraryLinks = Callable[[str], bool]
"""Whether a link that is no web link, such as gopls's `file:` links into GOROOT, opens a library
file; the broker's own records the file as one the page may read."""


def no_library(_href: str) -> bool:
    return False


def render_markdown(text: str) -> str:
    return _RENDERER.render(text)


def render_documentation_markdown(text: str, opens_library: LibraryLinks = no_library) -> str:
    """`opens_library` says which links that are no web links become buttons that open a library
    file (docs/specs/web-ui.md#hover); every other one is its text."""
    return _DOCUMENTATION.render(text, {LIBRARY_LINKS: opens_library})


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
    """An image becomes its alt text, a web link opens elsewhere, a link the environment's
    `LIBRARY_LINKS` accepts becomes a button, and any other link its text. Needs `validateLink`
    to accept every link, or markdown would leave the ones it refuses (`file:`, `javascript:`)
    as the source text."""
    opens_library = cast(LibraryLinks, state.env.get(LIBRARY_LINKS, no_library))
    for block in state.tokens:
        if block.type == "inline" and block.children is not None:
            block.children = _without_unsafe_links(block.children, opens_library)


def _without_unsafe_links(tokens: Sequence[Token], opens_library: LibraryLinks) -> list[Token]:
    kept: list[Token] = []
    closing: list[str | None] = []
    """For each open link, the tag that closes it; None for a link that became its text."""
    for token in tokens:
        if token.type == "link_open":
            tag = _rewritten_link(token, opens_library)
            closing.append(tag)
            if tag is not None:
                kept.append(token)
        elif token.type == "link_close":
            tag = closing.pop()
            if tag is not None:
                token.tag = tag
                kept.append(token)
        elif token.type == "image":
            kept.append(_alt_text(token))
        else:
            kept.append(token)
    return kept


def _rewritten_link(link: Token, opens_library: LibraryLinks) -> str | None:
    """Rewrites the opening token of a link that is kept: a web link opens elsewhere, and a link
    to a library file becomes a button naming it in `data-uri`. The tag that closes the link;
    None for a link that becomes its text."""
    href = link.attrGet("href")
    if not isinstance(href, str):
        return None
    if href.lower().startswith(WEB_LINKS):
        link.attrs.update(OPENS_ELSEWHERE)
        return link.tag
    if not opens_library(href):
        return None
    link.tag = BUTTON
    link.attrs = {"type": BUTTON, "class": LIBRARY_LINK_CLASS, "data-uri": href}
    return BUTTON


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
