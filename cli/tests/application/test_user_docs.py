"""The user docs' use cases (docs/specs/user-docs.md): the listing in order, one page, and the
static checks of `cstudy verify` (D1 to D6)."""

from pathlib import Path

import pytest

from coding_study.application.user_docs import doc_page, docs_listing, verify_user_docs
from coding_study.application.verify_content import VerifyRequest, verify_content
from coding_study.domain.errors import UnknownTopicError
from tests.doc_builders import ROOT_COMMANDS, page_text, write_docs, write_page
from tests.fakes import make_environment


def test_the_listing_is_every_page_by_order(content_root: Path):
    write_docs(content_root)
    write_page(content_root, "first", page_text("First", order=1))
    pages = docs_listing(make_environment(content_root))
    assert [page.slug for page in pages] == ["first", "getting-started", "doctor", "practice"]


def test_a_content_root_without_user_docs_lists_nothing(content_root: Path):
    assert docs_listing(make_environment(content_root)) == ()


def test_a_page_is_found_by_its_slug(content_root: Path):
    write_docs(content_root)
    assert doc_page(make_environment(content_root), "doctor").title == "Check your setup"


def test_an_unknown_topic_names_the_nearest(content_root: Path):
    write_docs(content_root)
    with pytest.raises(UnknownTopicError) as raised:
        doc_page(make_environment(content_root), "doctr")
    assert str(raised.value) == 'unknown topic "doctr"; did you mean doctor?'


def test_every_page_of_sound_docs_passes(content_root: Path):
    write_docs(content_root)
    results = verify_user_docs(make_environment(content_root), ROOT_COMMANDS)
    assert [(result.file, result.static_errors) for result in results] == [
        ("user-docs/doctor.md", ()),
        ("user-docs/getting-started.md", ()),
        ("user-docs/practice.md", ()),
    ]


def test_each_page_reports_its_own_problems(content_root: Path):
    write_docs(content_root)
    write_page(content_root, "broken", "# No front matter\n")
    write_page(
        content_root,
        "flags",
        page_text("Flags", "Run `cstudy doctor --fixx` and see [x](nowhere.md).\n", order=25),
    )
    (content_root / "user-docs" / "notes.txt").write_text("x")
    results = verify_user_docs(make_environment(content_root), ROOT_COMMANDS)
    assert {result.file: result.static_errors for result in results if result.static_errors} == {
        "user-docs/broken.md": ("user-docs/broken.md: starts with front matter between --- lines",),
        "user-docs/flags.md": (
            'user-docs/flags.md: line 10: links to nowhere.md: there is no page "nowhere"',
            "user-docs/flags.md: line 10: cstudy doctor has no flag --fixx",
        ),
        "user-docs/notes.txt": ("user-docs/notes.txt: not a page: a file named <slug>.md",),
    }


def test_without_a_command_line_the_commands_are_not_checked(content_root: Path):
    write_page(content_root, "flags", page_text("Flags", "Run `cstudy doctor --fixx`.\n"))
    results = verify_user_docs(make_environment(content_root), None)
    assert [result.static_errors for result in results] == [()]


def test_verify_lists_the_pages_after_the_guides_and_fails_on_a_broken_one(content_root: Path):
    write_docs(content_root)
    write_page(content_root, "flags", page_text("Flags", "Run `cstudy doctor --fixx`.\n", order=5))
    request = VerifyRequest(static_only=True, commands=ROOT_COMMANDS)
    report = verify_content(make_environment(content_root), request, print)
    rows = [row for row in report.problems if row.directory.startswith("user-docs/")]
    assert (
        [row.directory for row in rows],
        [row.directory for row in rows if not row.passed],
        [row.static_errors for row in rows if not row.passed],
    ) == (
        [
            "user-docs/doctor.md",
            "user-docs/flags.md",
            "user-docs/getting-started.md",
            "user-docs/practice.md",
        ],
        ["user-docs/flags.md"],
        [("user-docs/flags.md: line 10: cstudy doctor has no flag --fixx",)],
    )


def test_verify_of_chosen_problems_leaves_the_pages_out(content_root: Path):
    write_docs(content_root)
    request = VerifyRequest(slugs=("two-sum",), static_only=True, commands=ROOT_COMMANDS)
    report = verify_content(make_environment(content_root), request, print)
    assert [row.directory for row in report.problems if "user-docs" in row.directory] == []
