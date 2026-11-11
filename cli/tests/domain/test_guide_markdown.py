import hashlib

from coding_study.domain.guide_markdown import GuideMarkdown, mermaid_digest, text_marker

DIAGRAM = "flowchart LR\n  accTitle: Two boxes\n  accDescr: A points to B.\n  a --> b\n"
DIGEST = hashlib.sha256(DIAGRAM.encode()).hexdigest()


def guide_with_diagram(marker: str) -> str:
    return (
        "# Title\n\nBefore.\n\n```mermaid\n"
        f"{DIAGRAM}```\n\n{marker}\n```text\n[a] --> [b]\n```\n\nAfter.\n"
    )


def test_a_fence_knows_its_language_its_argument_and_its_content():
    markdown = GuideMarkdown("```python examples/one.py\nprint(1)\n```\n")
    fence = markdown.fences[0]
    assert (fence.language, fence.argument, fence.content) == (
        "python",
        "examples/one.py",
        "print(1)\n",
    )


def test_a_fence_closes_only_on_a_marker_at_least_as_long_as_the_one_that_opened_it():
    markdown = GuideMarkdown("````markdown\n```python\nx\n```\n````\nafter\n")
    assert [fence.content for fence in markdown.fences] == ["```python\nx\n```\n"]


def test_an_unclosed_fence_runs_to_the_end_and_says_so():
    fence = GuideMarkdown("```text\nleft open\n").fences[0]
    assert (fence.closed, fence.content) == (False, "left open\n")


def test_examples_and_outputs_are_the_fences_that_name_a_file_in_examples():
    markdown = GuideMarkdown(
        "```python examples/a.py\nprint(1)\n```\n\n```output examples/a.py\n1\n```\n\n"
        "```python\nillustration()\n```\n"
    )
    assert (
        [fence.argument for fence in markdown.example_fences()],
        [fence.argument for fence in markdown.output_fences()],
    ) == (["examples/a.py"], ["examples/a.py"])


def test_the_digest_is_the_sha256_of_the_mermaid_source_in_utf8():
    assert mermaid_digest(DIAGRAM) == DIGEST


def test_the_marker_names_the_digest():
    assert text_marker(DIAGRAM) == f"<!-- text-of-mermaid sha256:{DIGEST} -->"


def test_a_diagram_finds_its_text_drawing_after_the_marker():
    markdown = GuideMarkdown(guide_with_diagram(text_marker(DIAGRAM)))
    drawing = markdown.text_drawing(markdown.mermaid_fences()[0])
    assert drawing is not None
    assert (drawing.digest, drawing.fence.content) == (DIGEST, "[a] --> [b]\n")


def test_a_diagram_without_a_marker_has_no_text_drawing():
    markdown = GuideMarkdown("```mermaid\nflowchart LR\n```\n\nProse.\n")
    assert markdown.text_drawing(markdown.mermaid_fences()[0]) is None


def test_a_marker_after_prose_is_a_stray_marker():
    markdown = GuideMarkdown(f"Prose.\n\n{text_marker(DIAGRAM)}\n```text\nx\n```\n")
    assert markdown.stray_markers() == (2,)


def test_a_marker_right_after_its_diagram_is_not_stray():
    markdown = GuideMarkdown(guide_with_diagram(text_marker(DIAGRAM)))
    assert markdown.stray_markers() == ()


def test_the_terminal_text_shows_the_drawing_and_hides_the_mermaid_source_and_marker():
    text = GuideMarkdown(guide_with_diagram(text_marker(DIAGRAM))).terminal_text()
    assert text == "# Title\n\nBefore.\n\n```text\n[a] --> [b]\n```\n\nAfter.\n"


def test_the_terminal_text_keeps_a_diagram_that_has_no_drawing():
    source = "Before.\n\n```mermaid\nflowchart LR\n  a --> b\n```\n"
    assert GuideMarkdown(source).terminal_text() == source


def test_a_marker_inside_a_fence_is_text_not_a_marker():
    markdown = GuideMarkdown(f"```text\n{text_marker(DIAGRAM)}\n```\n")
    assert markdown.stray_markers() == ()
