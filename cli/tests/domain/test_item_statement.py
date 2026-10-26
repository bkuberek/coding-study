from coding_study.domain.item_statement import (
    STATEMENT_FOOTER,
    Change,
    ChangeFile,
    ItemStatementParts,
    notes_text,
    render_item_statement,
)
from coding_study.domain.items import GuideLink, ItemMeta, guide_path
from coding_study.domain.layout import notes_archive_directory, notes_path
from coding_study.domain.problem import ContentStatus, Difficulty, Track

META = ItemMeta(
    slug="retry-wrapper",
    title="Retry Wrapper",
    track=Track.CODE_REVIEW,
    difficulty=Difficulty.EASY,
    estimate_minutes=20,
    status=ContentStatus.READY,
)
PROMPT = "# Retry Wrapper\n\n## Context\n\nA helper.\n\n## Task\n\nReview it.\n"


def test_statement_keeps_the_prompt_and_adds_the_metadata():
    assert render_item_statement(META, ItemStatementParts(PROMPT)).splitlines() == [
        "# Retry Wrapper",
        "",
        "easy · code-review · 20 min",
        "",
        "## Context",
        "",
        "A helper.",
        "",
        "## Task",
        "",
        "Review it.",
        "",
        STATEMENT_FOOTER,
    ]


def test_statement_appends_the_diff():
    change = Change(diff="--- a/x.py\n+++ b/x.py\n")
    statement = render_item_statement(META, ItemStatementParts(PROMPT, change))
    block = ["## Change", "", "```diff", "--- a/x.py", "+++ b/x.py", "```", "", STATEMENT_FOOTER]
    assert statement.splitlines()[-len(block) :] == block


def test_statement_appends_each_file_in_a_block_named_after_its_extension():
    change = Change(files=(ChangeFile("client.py", "x = 1\n"), ChangeFile("Makefile", "all:\n")))
    block = [
        "## Files",
        "",
        "### client.py",
        "",
        "```py",
        "x = 1",
        "```",
        "",
        "### Makefile",
        "",
        "```text",
        "all:",
        "```",
    ]
    assert "\n".join(block) in render_item_statement(META, ItemStatementParts(PROMPT, change))


def test_statement_without_a_title_gets_one():
    parts = ItemStatementParts("## Context\n\nA helper.\n")
    assert render_item_statement(META, parts).splitlines()[:3] == [
        "# Retry Wrapper",
        "",
        "easy · code-review · 20 min",
    ]


GUIDE_LOCATION = "file:///home/me/study-guides/caching.md"


def test_statement_lists_the_located_study_guides_last():
    guides = (GuideLink("caching.md#eviction", GUIDE_LOCATION),)
    statement = render_item_statement(META, ItemStatementParts(PROMPT, guides=guides))
    block = [
        "## Study guides",
        "",
        f"- [caching.md#eviction]({GUIDE_LOCATION}#eviction)",
        "",
        STATEMENT_FOOTER,
    ]
    assert statement.splitlines()[-len(block) :] == block


def test_statement_without_located_guides_has_no_study_guide_section():
    assert "## Study guides" not in render_item_statement(META, ItemStatementParts(PROMPT))


def test_guide_link_target_keeps_the_section_anchor():
    assert GuideLink("caching.md#eviction", GUIDE_LOCATION).target == f"{GUIDE_LOCATION}#eviction"


def test_guide_link_target_without_an_anchor_is_the_location():
    assert GuideLink("caching.md", GUIDE_LOCATION).target == GUIDE_LOCATION


def test_guide_path_drops_the_section_anchor():
    assert guide_path("systems/caching.md#eviction") == "systems/caching.md"


def test_guide_path_without_an_anchor_is_unchanged():
    assert guide_path("caching.md") == "caching.md"


def test_notes_start_with_a_header_comment():
    assert notes_text(META, "# Retry Wrapper: Notes\n\n## Blocker\n").splitlines() == [
        "<!-- Retry Wrapper. Prompt: .statements/retry-wrapper.md. "
        "Then: cstudy solution retry-wrapper, cstudy done --rating easy|ok|hard -->",
        "",
        "# Retry Wrapper: Notes",
        "",
        "## Blocker",
    ]


def test_notes_path():
    assert notes_path(META) == "notes/code-review/retry-wrapper.md"


def test_notes_archive_directory():
    assert notes_archive_directory("retry-wrapper", 7) == ".archive/retry-wrapper/7-notes"
