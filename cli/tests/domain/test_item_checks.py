from dataclasses import replace

import pytest

from coding_study.domain.item_checks import ItemContent, item_ready_problems, item_static_checks
from coding_study.domain.items import ItemMeta, ItemReferences
from coding_study.domain.problem import ContentStatus, Difficulty, Track
from tests.helpers import FIXTURE_TRACKS

SYSTEM_DESIGN = "tracks/system-design/url-shortener"
CODE_REVIEW = "tracks/code-review/retry-wrapper"
URL_SHORTENER = ItemMeta(
    slug="url-shortener",
    title="URL Shortener",
    track=Track.SYSTEM_DESIGN,
    difficulty=Difficulty.MEDIUM,
    estimate_minutes=45,
    status=ContentStatus.READY,
    references=ItemReferences(study_guides=("guide.md#databases",)),
)
RETRY_WRAPPER = ItemMeta(
    slug="retry-wrapper",
    title="Retry Wrapper",
    track=Track.CODE_REVIEW,
    difficulty=Difficulty.EASY,
    estimate_minutes=20,
    status=ContentStatus.READY,
)


def fixture_content(meta: ItemMeta) -> ItemContent:
    directory = FIXTURE_TRACKS / meta.track / meta.slug

    def text(name: str) -> str | None:
        path = directory / name
        return path.read_text() if path.is_file() else None

    return ItemContent(
        directory=f"tracks/{meta.track}/{meta.slug}",
        meta=meta,
        prompt=text("prompt.md"),
        rubric=text("rubric.md"),
        reference=text("reference.md"),
        template=text("template.md"),
        change=text("change.diff"),
    )


@pytest.fixture
def system_design() -> ItemContent:
    return fixture_content(URL_SHORTENER)


@pytest.fixture
def code_review() -> ItemContent:
    return fixture_content(RETRY_WRAPPER)


def messages(content: ItemContent) -> list[str]:
    return [str(issue) for issue in item_static_checks(content)]


def edited(content: ItemContent, field: str, old: str, new: str) -> ItemContent:
    text = getattr(content, field)
    assert old in text
    return replace(content, **{field: text.replace(old, new)})


def test_complete_system_design_item_passes(system_design):
    assert messages(system_design) == []


def test_complete_code_review_item_passes(code_review):
    assert messages(code_review) == []


@pytest.mark.parametrize("field", ["prompt", "rubric", "reference", "template"])
def test_every_markdown_file_is_required(system_design, field):
    content = replace(system_design, **{field: None})
    assert messages(content) == [f"{SYSTEM_DESIGN}/{field}.md: missing"]


def test_prompt_title_equals_the_item_title(system_design):
    content = edited(system_design, "prompt", "# URL Shortener", "# Shortener")
    assert messages(content) == [
        f'{SYSTEM_DESIGN}/prompt.md: title "Shortener" must be "URL Shortener"'
    ]


def test_system_design_prompt_needs_its_sections(system_design):
    content = edited(system_design, "prompt", "## Scale", "## Size")
    assert messages(content) == [f'{SYSTEM_DESIGN}/prompt.md: missing "## Scale"']


def test_code_review_prompt_needs_its_sections(code_review):
    content = edited(code_review, "prompt", "## Task", "## Ask")
    assert messages(content) == [f'{CODE_REVIEW}/prompt.md: missing "## Task"']


def test_required_sections_must_not_be_empty(system_design):
    content = replace(
        system_design, prompt=system_design.prompt.split("## Scale")[0] + "## Scale\n"
    )
    assert messages(content) == [f'{SYSTEM_DESIGN}/prompt.md: "## Scale" is empty']


def test_required_sections_keep_their_order(system_design):
    sections = ("Question", "Functional requirements", "Scale", "Non-functional requirements")
    prompt = "# URL Shortener\n" + "".join(f"\n## {title}\n\nText.\n" for title in sections)
    assert messages(replace(system_design, prompt=prompt)) == [
        f'{SYSTEM_DESIGN}/prompt.md: "## Non-functional requirements" must come before "## Scale"'
    ]


def test_placeholders_are_rejected(system_design):
    content = edited(system_design, "reference", "One table keyed", "TODO: one table keyed")
    assert messages(content) == [f'{SYSTEM_DESIGN}/reference.md: "## Data model" contains TODO']


def test_rubric_issues_are_reported(system_design):
    content = edited(system_design, "rubric", "- [ ] Handles expiry", "- Handles expiry")
    assert messages(content) == [
        f'{SYSTEM_DESIGN}/rubric.md: "## Operations" has no "- [ ] <criterion>" line'
    ]


def test_system_design_reference_needs_its_sections(system_design):
    content = edited(system_design, "reference", "## Deep dives", "## Details")
    assert messages(content) == [f'{SYSTEM_DESIGN}/reference.md: missing "## Deep dives"']


def test_reference_title(system_design):
    content = edited(system_design, "reference", "# URL Shortener: Reference", "# Answer")
    assert messages(content) == [
        f'{SYSTEM_DESIGN}/reference.md: title "Answer" must be "URL Shortener: Reference"'
    ]


def test_code_review_reference_sections_are_severities(code_review):
    content = edited(code_review, "reference", "## Nit", "## Style")
    assert messages(content) == [
        f'{CODE_REVIEW}/reference.md: "## Style" is not a severity: Blocker, Major, Minor, Nit'
    ]


def test_code_review_severities_keep_their_order(code_review):
    blocker, rest = code_review.reference.split("## Major")
    title, blocker_body = blocker.split("## Blocker")
    reordered = f"{title}## Major{rest}\n## Blocker{blocker_body}"
    assert messages(replace(code_review, reference=reordered)) == [
        f'{CODE_REVIEW}/reference.md: "## Blocker" must come before "## Major"'
    ]


def test_code_review_severity_lists_issues(code_review):
    content = edited(code_review, "reference", "- A fixed one-second sleep", "A fixed sleep")
    assert messages(content) == [f'{CODE_REVIEW}/reference.md: "## Nit" lists no "- " issue']


def test_code_review_reference_needs_an_issue(code_review):
    content = replace(code_review, reference="# Retry Wrapper: Reference\n")
    severities = "Blocker, Major, Minor, Nit"
    assert messages(content) == [
        f"{CODE_REVIEW}/reference.md: needs at least one severity section: {severities}"
    ]


def test_template_needs_a_section(system_design):
    content = replace(system_design, template="# URL Shortener: Notes\n")
    assert messages(content) == [f'{SYSTEM_DESIGN}/template.md: needs at least one "## " section']


def test_template_title(system_design):
    content = edited(system_design, "template", "# URL Shortener: Notes", "# Notes")
    assert messages(content) == [
        f'{SYSTEM_DESIGN}/template.md: title "Notes" must be "URL Shortener: Notes"'
    ]


def test_code_review_needs_the_change(code_review):
    content = replace(code_review, change=None)
    assert messages(content) == [f"{CODE_REVIEW}: needs change.diff or files/ (exactly one)"]


def test_code_review_accepts_files_instead_of_a_diff(code_review):
    content = replace(code_review, change=None, change_files=("client.py",))
    assert messages(content) == []


def test_code_review_rejects_both_forms(code_review):
    assert messages(replace(code_review, change_files=("client.py",))) == [
        f"{CODE_REVIEW}: needs change.diff or files/ (exactly one)"
    ]


def test_empty_diff_is_rejected(code_review):
    assert messages(replace(code_review, change="\n")) == [f"{CODE_REVIEW}/change.diff: is empty"]


def test_system_design_has_no_change(system_design):
    assert messages(replace(system_design, change="--- a\n")) == [
        f"{SYSTEM_DESIGN}/change.diff: only code-review items have a change under review"
    ]


def test_ready_item_has_no_ready_problems(system_design):
    assert item_ready_problems(system_design) == ()


def test_draft_is_not_ready(system_design):
    content = replace(system_design, meta=replace(URL_SHORTENER, status=ContentStatus.DRAFT))
    assert item_ready_problems(content) == ("status is draft, not ready",)


def test_ready_system_design_needs_a_reference(system_design):
    content = replace(system_design, meta=replace(URL_SHORTENER, references=ItemReferences()))
    assert item_ready_problems(content) == (
        "system-design items need at least one reference (links or study_guides)",
    )


def test_ready_system_design_may_reference_links_only(system_design):
    references = ItemReferences(links=("https://example.com/caching",))
    content = replace(system_design, meta=replace(URL_SHORTENER, references=references))
    assert item_ready_problems(content) == ()


def test_code_review_needs_no_study_guide(code_review):
    assert item_ready_problems(code_review) == ()
