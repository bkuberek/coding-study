"""The documentation a language server sends, rendered to the HTML the page may insert
(docs/specs/web-ui.md#documentation): markdown with raw HTML as text, highlighted code with the
classes of statements, images as their alt text, only web links as links, and no `style`."""

from html.parser import HTMLParser

import pytest

from coding_study.entrypoints.web.documentation import documentation_html, hover_html

PYTHON_CODE = "def sorted(xs): ..."
HIGHLIGHTED = '<span class="tok-k">def</span>'


def markdown(text: str) -> dict[str, str]:
    return {"kind": "markdown", "value": text}


def rendered(text: str) -> str:
    html = hover_html(markdown(text))
    assert html is not None
    return html


# markdown


def test_markdown_is_rendered_to_html():
    assert rendered("Return a new `list`.\n\nSecond.") == (
        "<p>Return a new <code>list</code>.</p>\n<p>Second.</p>\n"
    )


def test_a_fence_in_a_known_language_is_highlighted_with_the_classes_of_statements():
    html = rendered(f"```python\n{PYTHON_CODE}\n```")
    assert (html.startswith('<pre><code class="language-python">'), HIGHLIGHTED in html) == (
        True,
        True,
    )


@pytest.mark.parametrize("fence", ["```\n<b>x</b>\n```", "```no-such-language\n<b>x</b>\n```"])
def test_a_fence_with_no_language_or_an_unknown_one_is_an_escaped_code_block(fence):
    html = rendered(fence)
    assert ("&lt;b&gt;x&lt;/b&gt;" in html, "<b>" in html, "tok-" in html) == (True, False, False)


def test_an_indented_block_is_an_escaped_code_block():
    assert rendered("    <i>x</i>") == "<pre><code>&lt;i&gt;x&lt;/i&gt;\n</code></pre>\n"


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        'text <a href="http://x" onclick="y()">z</a>',
        "<div style='color:red'>x</div>",
    ],
)
def test_raw_html_is_text(text):
    html = rendered(text)
    assert ("<script" in html, "<img" in html, "<div" in html, 'href="http://x"' in html) == (
        False,
        False,
        False,
        False,
    )
    assert "&lt;" in html


class Attributes(HTMLParser):
    """The name of every attribute of every tag in a piece of HTML."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.names: set[str] = set()
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.names.update(name for name, _value in attrs)


def test_nothing_in_the_output_carries_a_style_attribute():
    html = rendered(
        "| a | b |\n|--:|:-:|\n| 1 | 2 |\n\n```python\nx = 1\n```\n\n<p style='x'>y</p>"
    )
    assert ("style" in Attributes(html).names, 'class="align-right"' in html) == (False, True)


def test_markdown_strikethrough_and_lists_work():
    assert (
        rendered("~~old~~\n\n- a\n- b")
        == "<p><s>old</s></p>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n"
    )


# images and links


def test_an_image_is_its_alt_text_so_the_page_requests_nothing():
    assert rendered("![a cat](http://example.com/cat.png)") == "<p>a cat</p>\n"


def test_an_image_in_a_link_leaves_the_link_with_the_alt_text():
    html = rendered("[![logo](http://example.com/logo.png)](https://example.com)")
    assert ("<img" in html, ">logo</a>" in html) == (False, True)


@pytest.mark.parametrize(
    "url", ["http://example.com/a?b=1&c=2", "https://example.com/", "HTTPS://EXAMPLE.COM/"]
)
def test_web_links_stay_links_that_open_elsewhere_without_the_referrer(url):
    html = rendered(f"[docs]({url})")
    assert (
        html.count("<a "),
        'rel="noopener noreferrer"' in html,
        'target="_blank"' in html,
        ">docs</a>" in html,
    ) == (1, True, True, True)


@pytest.mark.parametrize(
    "target",
    [
        "file:///home/me/ws/python/practice/two_sum.py#L3",
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "vbscript:x",
        "data:text/html;base64,PHNjcmlwdD4=",
        "mailto:me@example.com",
        "ftp://example.com/x",
        "jdt://contents/x.class",
        "/absolute/path",
        "relative/path.md",
        "#fragment",
        "//example.com/x",
    ],
)
def test_every_other_link_is_its_text_alone(target):
    assert rendered(f"[some **text**]({target})") == "<p>some <strong>text</strong></p>\n"


@pytest.mark.parametrize(
    "autolink", ["file:///etc/passwd", "javascript:alert(1)", "mailto:me@x.org"]
)
def test_an_autolink_that_is_not_a_web_link_is_its_text_alone(autolink):
    assert rendered(f"<{autolink}>") == f"<p>{autolink}</p>\n"


def test_an_autolink_to_the_web_stays_a_link():
    assert 'href="https://example.com"' in rendered("<https://example.com>")


def test_a_link_reference_is_resolved_like_a_link():
    assert rendered("[x][1]\n\n[1]: file:///a/b.py") == "<p>x</p>\n"


# the other shapes of documentation


def test_plain_text_is_escaped_in_one_preformatted_block():
    value = {"kind": "plaintext", "value": "a <b> & c\n  indented"}
    assert hover_html(value) == '<pre class="doc-plain">a &lt;b&gt; &amp; c\n  indented</pre>'


def test_a_kind_the_broker_does_not_know_is_plain_text():
    assert documentation_html({"kind": "html", "value": "<b>x</b>"}) == (
        '<pre class="doc-plain">&lt;b&gt;x&lt;/b&gt;</pre>'
    )


def test_a_marked_string_that_is_a_string_is_markdown():
    assert hover_html("**bold**") == "<p><strong>bold</strong></p>\n"


def test_documentation_that_is_a_string_is_plain_text():
    assert (
        documentation_html("**not bold** <i>")
        == '<pre class="doc-plain">**not bold** &lt;i&gt;</pre>'
    )


def test_a_marked_string_with_a_language_is_a_highlighted_code_block():
    html = hover_html({"language": "python", "value": PYTHON_CODE})
    assert html is not None
    assert (html.startswith('<pre><code class="language-python">'), HIGHLIGHTED in html) == (
        True,
        True,
    )


def test_a_marked_string_cannot_close_its_own_code_block():
    html = hover_html({"language": "no-such-language", "value": "```\n<script>x</script>\n```"})
    assert html is not None
    assert ("<script" in html, "&lt;script&gt;" in html, html.count("<pre>")) == (False, True, 1)


def test_a_list_renders_each_in_order_separated_by_a_rule():
    contents = [markdown("a"), "b", {"language": "python", "value": "x = 1"}]
    html = hover_html(contents)
    assert html is not None
    assert html.split("<hr>\n")[:2] == ["<p>a</p>\n", "<p>b</p>\n"]
    assert html.count("<hr>") == 2


def test_a_list_leaves_out_what_renders_to_nothing():
    assert hover_html([markdown(""), "b", markdown("  ")]) == "<p>b</p>\n"


@pytest.mark.parametrize(
    "nothing",
    [None, "", "  \n ", markdown(""), markdown(" \n"), [], [""], {"kind": "markdown"}, 7, True, {}],
)
def test_what_renders_to_nothing_is_none(nothing):
    assert (hover_html(nothing), documentation_html(nothing)) == (None, None)


@pytest.mark.parametrize(
    "garbage", [{"kind": "markdown", "value": 7}, {"language": "python"}, [7, None]]
)
def test_a_value_of_another_shape_is_none(garbage):
    assert hover_html(garbage) is None
