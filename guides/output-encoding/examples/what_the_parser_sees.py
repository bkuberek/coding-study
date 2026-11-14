"""What a parser makes of untrusted text: written raw, encoded for one place, and encoded for its place."""

import html
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlsplit


class Tokens(HTMLParser):
    """Collects the tags, attributes and text that an HTML parser finds in a page."""

    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.found.append(f"<{tag}> {dict(attrs)}")

    def handle_data(self, data: str) -> None:
        self.found.append(f"text {data!r}")


def html_tokens(page: str) -> list[str]:
    parser = Tokens()
    parser.feed(page)
    parser.close()
    return parser.found


name = "Ann<img src=x onerror=steal()>"
print("text, raw:          ", html_tokens(f"<p>{name}</p>"))
print("text, encoded:      ", html_tokens(f"<p>{html.escape(name)}</p>"))

title = "Ann onmouseover=steal()"
print("unquoted, encoded:  ", html_tokens(f"<a title={html.escape(title)}>"))
print("quoted, encoded:    ", html_tokens(f'<a title="{html.escape(title)}">'))

term = "fish & chips #1"
glued = urlsplit("/search?q=" + html.escape(term) + "&page=2")
print("query, HTML-encoded:", parse_qs(glued.query), "fragment:", repr(glued.fragment))
built = urlsplit("/search?" + urlencode({"q": term, "page": 2}))
print("query, URL-encoded: ", parse_qs(built.query), "as sent:", built.query)
