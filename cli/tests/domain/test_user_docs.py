"""The user docs' pages (docs/specs/user-docs.md): front matter, heading ids, passages, sections
and the message for an unknown topic."""

import pytest

from coding_study.domain.user_docs import (
    DocHeading,
    DocPage,
    DocPassage,
    heading_id,
    heading_ids,
    in_sections,
    split_front_matter,
    unknown_topic_message,
)


def page(slug: str, section: str, order: int, markdown: str = "# T\n") -> DocPage:
    return DocPage(slug, slug.title(), "A summary.", section, order, markdown)


def test_the_front_matter_is_split_from_the_body():
    assert split_front_matter("---\ntitle: T\n---\n\n# T\n") == ("title: T\n", "\n# T\n", 3)


@pytest.mark.parametrize(
    "text", ["# T\n", "---\ntitle: T\n", "\n---\ntitle: T\n---\n# T\n", "--- \ntitle: T\n---\n"]
)
def test_a_page_without_closed_front_matter_at_its_top_has_none(text: str):
    assert split_front_matter(text) is None


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Python and uv", "python-and-uv"),
        ("Node.js and pnpm", "nodejs-and-pnpm"),
        ("JDK", "jdk"),
        ("`cstudy doctor`", "cstudy-doctor"),
        ("Hints, solutions, Done and Abort", "hints-solutions-done-and-abort"),
        ("Change `progress_db`", "change-progress_db"),
        ("Security, in plain words", "security-in-plain-words"),
        ("[Links](https://example.org) and **bold**", "links-and-bold"),
        ("Café: qué", "café-qué"),
    ],
)
def test_a_heading_id_is_githubs(title: str, expected: str):
    assert heading_id(title) == expected


def test_repeated_headings_get_a_number_and_headings_in_code_do_not_count():
    markdown = (
        "# Title\n\n## Fix\n\n```bash\n## not a heading\n```\n\n## Fix\n\n### Fix\n\n#### Deep\n"
    )
    assert heading_ids(markdown) == (
        DocHeading("title", "Title", 1),
        DocHeading("fix", "Fix", 2),
        DocHeading("fix-1", "Fix", 2),
        DocHeading("fix-2", "Fix", 3),
        DocHeading("deep", "Deep", 4),
    )


def test_a_pages_headings_are_its_second_and_third_levels_with_their_marks_left_out():
    markdown = "# T\n\nIntro.\n\n## `cstudy doctor`\n\nRows.\n\n### --fix\n\nSets up.\n\n#### No\n"
    assert page("doctor", "Start", 1, markdown).headings == (
        DocHeading("cstudy-doctor", "cstudy doctor", 2),
        DocHeading("--fix", "--fix", 3),
    )


def test_the_passages_are_the_opening_then_each_section_as_plain_text():
    markdown = (
        "# Doctor\n\nRun `cstudy doctor` [now](https://example.org).\n\n"
        "## The rows\n\n| Row | Means |\n|-----|-------|\n| **ok** | fine |\n\n"
        "### Fix\n\n```bash\ncstudy doctor --fix\n```\n"
    )
    assert page("doctor", "Start", 1, markdown).passages == (
        DocPassage("", "Doctor", "A summary. Run cstudy doctor now."),
        DocPassage("the-rows", "The rows", "Row Means ok fine"),
        DocPassage("fix", "Fix", "cstudy doctor --fix"),
    )


def test_sections_come_in_the_order_of_their_first_page():
    pages = (page("c", "B", 30), page("a", "A", 10), page("b", "A", 20))
    assert [(name, [doc.slug for doc in docs]) for name, docs in in_sections(pages)] == [
        ("A", ["a", "b"]),
        ("B", ["c"]),
    ]


def test_an_unknown_topic_suggests_the_nearest_or_the_list():
    assert (
        unknown_topic_message("doctr", ("doctor", "levels")),
        unknown_topic_message("zzz", ("doctor",)),
    ) == (
        'unknown topic "doctr"; did you mean doctor?',
        'unknown topic "zzz"; cstudy docs lists the topics',
    )
