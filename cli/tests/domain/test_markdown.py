from coding_study.domain.markdown import MarkdownDocument, MarkdownSection

TEXT = """\
# Two Sum

Intro.

## Statement

Find two positions.

## Examples

### Example 1

<!-- case: ex1 -->

```python
# not a heading
```

### Example 2

Text.

## Hints

### Hint 1

Think.
"""
DOCUMENT = MarkdownDocument(TEXT)


def section(title: str, parent: MarkdownSection | None = None) -> MarkdownSection:
    found = DOCUMENT.section(title, parent)
    assert found is not None
    return found


def test_title_is_the_first_level_one_heading():
    assert DOCUMENT.title == "Two Sum"


def test_no_title_without_a_level_one_heading():
    assert MarkdownDocument("## Only\n").title is None


def test_sections_at_a_level_in_order():
    assert [section.title for section in DOCUMENT.sections(2)] == [
        "Statement",
        "Examples",
        "Hints",
    ]


def test_headings_inside_code_fences_are_ignored():
    examples = DOCUMENT.section("Examples")
    assert [section.title for section in DOCUMENT.sections(3, examples)] == [
        "Example 1",
        "Example 2",
    ]


def test_section_by_title():
    assert section("Statement").text == "Find two positions."


def test_missing_section_is_none():
    assert DOCUMENT.section("Constraints") is None


def test_section_text_includes_subsections():
    assert "Think." in section("Hints").text


def test_section_intro_stops_at_the_first_subsection():
    assert section("Hints").intro == ""


def test_section_lines_cover_heading_to_next_sibling():
    statement = section("Statement")
    assert DOCUMENT.lines[statement.start : statement.end] == (
        "## Statement",
        "",
        "Find two positions.",
        "",
    )


def test_last_section_runs_to_the_end():
    assert section("Hints").end == len(DOCUMENT.lines)


def test_subsection_within_a_parent():
    hint = section("Hint 1", section("Hints"))
    assert hint.text == "Think."


def test_heading_needs_a_space_after_the_hashes():
    assert MarkdownDocument("##Statement\n").sections(2) == ()


def test_heading_titles_drop_trailing_hashes_and_spaces():
    assert MarkdownDocument("## Statement ##  \n").sections(2)[0].title == "Statement"
