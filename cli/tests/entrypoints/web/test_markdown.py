"""An HTML comment in markdown, such as the footer of a rendered statement file, is not shown
(docs/specs/web-ui.md#documentation): raw HTML is never inserted and a comment is not text."""

import pytest

from coding_study.entrypoints.web.markdown import (
    render_doc_markdown,
    render_documentation_markdown,
    render_guide_markdown,
    render_markdown,
)

FOOTER = "<!-- Rendered by cstudy from the problem's problem.md; edits here are overwritten. -->"

RENDERERS = [
    render_markdown,
    render_documentation_markdown,
    render_guide_markdown,
    lambda text: render_doc_markdown(text, "intro"),
]


@pytest.mark.parametrize("render", RENDERERS)
def test_a_comment_paragraph_is_dropped(render):
    assert render(f"Body.\n\n{FOOTER}\n") == "<p>Body.</p>\n"


@pytest.mark.parametrize("render", RENDERERS)
def test_a_comment_over_several_lines_is_dropped(render):
    assert render("Body.\n\n<!--\nnote\n-->\n") == "<p>Body.</p>\n"


def test_a_comment_in_a_code_block_is_code():
    assert "&lt;!-- keep --&gt;" in render_markdown("```\n<!-- keep -->\n```\n")


def test_other_raw_html_is_still_text():
    assert "&lt;script&gt;" in render_markdown("<script>x</script>\n")
