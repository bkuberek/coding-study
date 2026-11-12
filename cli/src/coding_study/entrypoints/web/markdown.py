"""Markdown as the page shows it: rendered on the server, raw HTML left as text, code blocks
highlighted by Pygments with classes the page's stylesheet colours (docs/specs/web-ui.md#security,
docs/specs/web-ui.md#front-end-assets). Nothing in the output carries a `style` attribute, which
the page's Content Security Policy would refuse.

The documentation a language server sends (docs/specs/web-ui.md#documentation) is rendered the
same way, except that an image is its alt text, only a web link stays a link, and a link to a
library file that the caller accepts becomes a button the page opens it with.

A concept guide (docs/specs/web-ui.md#guides-view) is rendered the same way too, except that its
`# ` title is left out, since the view's header shows it, each `mermaid` block becomes a figure of
its SVG drawings, made when the guide was written (docs/specs/guides.md#svg-drawings), and a link
to another guide becomes a link to that guide's view.
"""

import html
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import find_lexer_class_by_name
from pygments.util import ClassNotFound

from coding_study.domain.concept_guides import DIAGRAMS_DIRECTORY
from coding_study.domain.guide_markdown import (
    MERMAID,
    SVG_THEMES,
    TEXT,
    diagram_text,
    is_text_marker,
    mermaid_digest,
    svg_digest,
    svg_file,
    svg_size,
)

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
_GUIDE_LINK = re.compile(r"\.\./(?P<slug>[a-z][a-z0-9-]*)/guide\.md")
"""A link from one guide.md to another, as guides link each other."""
GUIDE_ROUTE = "#/guides/{slug}"
"""The page's route of a guide's view."""
TITLE_TAG = "h1"
TITLE_TOKENS = 3
"""A heading's tokens: its opening, its inline text and its closing."""
DRAWING_SHAPE = ("paragraph_open", "inline", "paragraph_close", "fence")
"""The tokens of a diagram's marker and its text drawing."""
DRAWING_TOKENS = len(DRAWING_SHAPE)
DIAGRAM_IMAGES = "diagram_images"
"""The key of the render environment that holds the `DiagramImages` of a guide."""
FIGURE_HTML = '<figure class="diagram">\n{body}<figcaption>{caption}</figcaption>\n</figure>\n'
IMAGE_HTML = (
    '<img class="diagram-image diagram-{theme}" src="{src}" alt="{alt}" '
    'width="{width}" height="{height}">\n'
)
TEXT_HTML = '<pre class="diagram-text"><code>{text}</code></pre>\n'


@dataclass(frozen=True, slots=True)
class DiagramImages:
    """Where the page asks for a guide's SVG drawings, and the drawings the guide has."""

    url: str
    """`{name}` in it is a drawing's name: `/api/v1/guides/hash-functions/diagrams/{name}`."""
    drawings: Mapping[str, str]
    """The text of each file under the guide's `diagrams/`, by its path relative to the guide."""


NO_IMAGES = DiagramImages("", {})

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


def render_guide_markdown(text: str, images: DiagramImages = NO_IMAGES) -> str:
    """A concept guide's guide.md as the Guides view shows it, each diagram as the `images` of its
    SVG drawings when both are up to date."""
    return _GUIDE.render(text, {DIAGRAM_IMAGES: images})


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
    _rewrite_links(state, lambda link: _rewritten_link(link, opens_library))


def _rewrite_links(state: StateCore, rewritten: Callable[[Token], str | None]) -> None:
    for block in state.tokens:
        if block.type == "inline" and block.children is not None:
            block.children = _without_unsafe_links(block.children, rewritten)


def _without_unsafe_links(
    tokens: Sequence[Token], rewritten: Callable[[Token], str | None]
) -> list[Token]:
    """`rewritten` rewrites a link's opening token and gives the tag that closes it, or None for a
    link that becomes its text."""
    kept: list[Token] = []
    closing: list[str | None] = []
    """For each open link, the tag that closes it; None for a link that became its text."""
    for token in tokens:
        if token.type == "link_open":
            tag = rewritten(token)
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


def _guide_link(link: Token) -> str | None:
    """A link to another guide's guide.md goes to that guide's view, a web link opens elsewhere,
    and any other link, such as one to an example file, becomes its text."""
    href = link.attrGet("href")
    if not isinstance(href, str):
        return None
    if href.lower().startswith(WEB_LINKS):
        link.attrs.update(OPENS_ELSEWHERE)
        return link.tag
    other_guide = _GUIDE_LINK.fullmatch(href)
    if other_guide is None:
        return None
    link.attrs = {"href": GUIDE_ROUTE.format(slug=other_guide["slug"])}
    return link.tag


def _guide_links(state: StateCore) -> None:
    _rewrite_links(state, _guide_link)


def _without_title(state: StateCore) -> None:
    """The guide's `# ` heading, which the view's header shows."""
    tokens = state.tokens
    if tokens and tokens[0].type == "heading_open" and tokens[0].tag == TITLE_TAG:
        state.tokens = tokens[TITLE_TOKENS:]


def _diagram_figures(state: StateCore) -> None:
    """Each `mermaid` block, with the marker and the text drawing that follow it, becomes one
    figure: its light and dark SVG drawings, of which the page's stylesheet shows the one of its
    theme, with `accTitle` as their alt text and `accDescr` as the caption. A diagram without
    both drawings up to date shows its text drawing instead, as the terminal does."""
    images = cast(DiagramImages, state.env.get(DIAGRAM_IMAGES, NO_IMAGES))
    tokens = state.tokens
    kept: list[Token] = []
    index = 0
    position = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "fence" and token.info.strip() == MERMAID:
            position += 1
            drawing = _drawing_after(tokens, index)
            kept.append(_figure(token, drawing, _images(images, position, token.content)))
            index += 1 + (DRAWING_TOKENS if drawing is not None else 0)
        else:
            kept.append(token)
            index += 1
    state.tokens = kept


def _drawing_after(tokens: Sequence[Token], index: int) -> Token | None:
    """The `text` block after a diagram's marker: the marker is a paragraph of its own, which the
    fence that follows it on the next line closes."""
    following = tokens[index + 1 : index + 1 + DRAWING_TOKENS]
    if [token.type for token in following] != list(DRAWING_SHAPE):
        return None
    marker, drawing = following[1], following[-1]
    if not is_text_marker(marker.content) or drawing.info.strip() != TEXT:
        return None
    return drawing


def _images(images: DiagramImages, position: int, source: str) -> list[tuple[str, str]] | None:
    """Each theme with the `<img>` of the diagram's drawing in it; None unless both drawings
    exist and hold the hash of the source."""
    alt = html.escape(diagram_text(source).title)
    found: list[tuple[str, str]] = []
    for theme in SVG_THEMES:
        name = svg_file(position, theme)
        svg = images.drawings.get(f"{DIAGRAMS_DIRECTORY}/{name}")
        size = None if svg is None else svg_size(svg)
        if svg is None or size is None or svg_digest(svg) != mermaid_digest(source):
            return None
        src = html.escape(images.url.format(name=name))
        width, height = size
        found.append(
            (theme, IMAGE_HTML.format(theme=theme, src=src, alt=alt, width=width, height=height))
        )
    return found


def _figure(diagram: Token, drawing: Token | None, images: list[tuple[str, str]] | None) -> Token:
    if images is not None:
        body = "".join(image for _theme, image in images)
    else:
        text = diagram.content if drawing is None else drawing.content
        body = TEXT_HTML.format(text=html.escape(text))
    caption = html.escape(diagram_text(diagram.content).description)
    figure = Token("html_block", "", 0, block=True, map=diagram.map)
    figure.content = FIGURE_HTML.format(body=body, caption=caption)
    return figure


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
_GUIDE = MarkdownIt("commonmark", {"html": False, "highlight": _highlighted}).enable(
    ["table", "strikethrough"]
)
_GUIDE.core.ruler.push("alignment_classes", _alignment_classes)
_GUIDE.core.ruler.push("without_title", _without_title)
_GUIDE.core.ruler.push("diagram_figures", _diagram_figures)
_GUIDE.core.ruler.push("guide_links", _guide_links)
