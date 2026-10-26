from pathlib import Path

import pytest

from coding_study.domain.rubric import (
    LLD_RUBRIC_SECTIONS,
    Rubric,
    RubricArea,
    RubricSection,
    item_rubric_issues,
    parse_rubric,
    rubric_issues,
    rubric_skeleton,
)

PARKING_LOT_RUBRIC = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "phase4"
    / "problems"
    / "0002-parking-lot"
    / "rubric.md"
)
RUBRIC = PARKING_LOT_RUBRIC.read_text()


def edited(old: str, new: str) -> str:
    assert old in RUBRIC
    return RUBRIC.replace(old, new)


def issues(text: str) -> list[str]:
    return list(rubric_issues(text, LLD_RUBRIC_SECTIONS))


def test_lld_sections_are_the_design_criteria_then_the_reference_design():
    assert [section.title for section in LLD_RUBRIC_SECTIONS] == [
        "Responsibilities",
        "Extension points",
        "Patterns",
        "Testability",
        "Reference design",
    ]


def test_a_complete_rubric_has_no_issues():
    assert issues(RUBRIC) == []


def test_a_missing_section():
    assert issues(edited("## Patterns", "## Idioms")) == ['missing "## Patterns"']


def test_a_criteria_section_needs_a_checklist_item():
    text = edited(
        "- [ ] All behavior is observable through the public API: no clock, randomness or I/O.",
        "Observable through the public API.",
    )
    assert issues(text) == ['"## Testability" needs at least one "- [ ] <criterion>" item']


def test_an_empty_checklist_item_does_not_count():
    text = edited(
        "- [ ] Choosing a spot is a natural strategy seam, even while only one policy exists.",
        "- [ ]",
    )
    assert issues(text) == ['"## Patterns" needs at least one "- [ ] <criterion>" item']


def test_the_reference_design_needs_text():
    text = RUBRIC[: RUBRIC.index("## Reference design")] + "## Reference design\n"
    assert issues(text) == ['"## Reference design" is empty']


def test_sections_follow_the_rubric_order():
    start, end = RUBRIC.index("## Patterns"), RUBRIC.index("## Testability")
    later = RUBRIC.index("## Reference design")
    text = RUBRIC[:start] + RUBRIC[end:later] + RUBRIC[start:end] + RUBRIC[later:]
    assert issues(text) == ['"## Patterns" must come before "## Testability"']


def test_placeholder_text_is_rejected():
    assert issues(edited("lives in one place.", "lives in TODO.")) == [
        '"## Extension points" contains TODO'
    ]


def test_other_sections_are_allowed():
    assert issues(RUBRIC + "\n## Follow-ups\n\nAdd payments.\n") == []


@pytest.mark.parametrize("checklist", [True, False])
def test_custom_sections_for_other_rubrics(checklist):
    sections = (RubricSection("Requirements", checklist=checklist),)
    text = "# Rubric\n\n## Requirements\n\n- [ ] Read and write paths are separated.\n"
    assert rubric_issues(text, sections) == ()


def test_a_skeleton_reports_a_placeholder_in_every_section():
    skeleton = rubric_skeleton("Vending Machine", LLD_RUBRIC_SECTIONS)
    assert issues(skeleton) == [
        f'"## {section.title}" contains TODO' for section in LLD_RUBRIC_SECTIONS
    ]


def test_a_skeleton_passes_once_its_placeholders_are_replaced():
    skeleton = rubric_skeleton("Vending Machine", LLD_RUBRIC_SECTIONS)
    assert issues(skeleton.replace("TODO", "Written")) == []


def test_a_skeleton_is_titled_after_the_problem():
    skeleton = rubric_skeleton("Vending Machine", LLD_RUBRIC_SECTIONS)
    assert parse_rubric(skeleton).title == "Vending Machine: Rubric"


def test_a_checkbox_inside_a_code_fence_is_no_criterion():
    sections = (RubricSection("Requirements"),)
    text = "# Rubric\n\n## Requirements\n\n```text\n- [ ] example\n```\n"
    assert rubric_issues(text, sections) == (
        '"## Requirements" needs at least one "- [ ] <criterion>" item',
    )


ITEM_TITLE = "URL Shortener: Rubric"
ITEM_RUBRIC = """# URL Shortener: Rubric

## Design

- [ ] Picks a key scheme.
- [ ] Caches hot links.

## Operations

- [ ] Handles expiry.
"""


def test_parses_areas_and_criteria():
    assert parse_rubric(ITEM_RUBRIC) == Rubric(
        ITEM_TITLE,
        (
            RubricArea("Design", ("Picks a key scheme.", "Caches hot links.")),
            RubricArea("Operations", ("Handles expiry.",)),
        ),
    )


def test_counts_criteria():
    assert parse_rubric(ITEM_RUBRIC).criteria_count == 3


def test_plain_bullets_are_not_criteria():
    assert parse_rubric("# R\n\n## A\n\n- a note\n").areas == (RubricArea("A", ()),)


def test_checkboxes_inside_code_fences_are_not_criteria():
    text = "# R\n\n## A\n\n- [ ] real\n\n```text\n- [ ] example\n```\n"
    assert parse_rubric(text).areas == (RubricArea("A", ("real",)),)


def test_complete_item_rubric_has_no_issues():
    assert item_rubric_issues(ITEM_RUBRIC, ITEM_TITLE) == ()


def test_item_rubric_title_must_match():
    assert item_rubric_issues(ITEM_RUBRIC.replace(ITEM_TITLE, "Rubric"), ITEM_TITLE) == (
        f'title "Rubric" must be "{ITEM_TITLE}"',
    )


def test_item_rubric_needs_an_area():
    assert item_rubric_issues(f"# {ITEM_TITLE}\n\n- [ ] loose\n", ITEM_TITLE) == (
        'needs at least one "## <area>" section with "- [ ] <criterion>" lines',
    )


def test_every_item_rubric_area_needs_a_criterion():
    text = ITEM_RUBRIC + "\n## Security\n\nThink about abuse.\n"
    assert item_rubric_issues(text, ITEM_TITLE) == (
        '"## Security" has no "- [ ] <criterion>" line',
    )
