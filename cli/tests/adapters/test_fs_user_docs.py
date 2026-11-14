"""The user docs in user-docs/ (docs/specs/user-docs.md#layout): the pages, their front matter and
its schema (D1), and where they ship (docs/specs/installation-and-workspaces.md#install)."""

import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.fs_user_docs import FsUserDocs
from coding_study.adapters.locations import find_content_root
from coding_study.domain.errors import ContentError
from coding_study.domain.user_docs import DocPage
from tests.doc_builders import page_text, write_docs, write_page
from tests.helpers import REPOSITORY_ROOT

BUILD = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]


def test_a_content_root_without_user_docs_has_no_pages(content_root: Path):
    docs = FsUserDocs(content_root)
    assert (docs.slugs(), docs.entries()) == ((), ())


def test_the_pages_are_the_markdown_files_by_slug(content_root: Path):
    write_docs(content_root)
    (content_root / "user-docs" / ".hidden.md").write_text("x")
    (content_root / "user-docs" / "notes.txt").write_text("x")
    (content_root / "user-docs" / "images").mkdir()
    docs = FsUserDocs(content_root)
    assert (docs.slugs(), docs.entries()) == (
        ("doctor", "getting-started", "practice"),
        ("doctor.md", "getting-started.md", "images/", "notes.txt", "practice.md"),
    )


def test_a_page_loads_with_its_front_matter_and_where_its_body_starts(content_root: Path):
    write_page(content_root, "doctor", page_text("Check", "Words.\n", order=30))
    assert FsUserDocs(content_root).load("doctor") == DocPage(
        slug="doctor",
        title="Check",
        summary="A short summary.",
        section="Start here",
        order=30,
        markdown="\n# Check\n\nWords.\n",
        first_line=6,
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("# Check\n", "user-docs/doctor.md: starts with front matter between --- lines"),
        (
            "---\ntitle: [\n---\n# Check\n",
            "user-docs/doctor.md: line 3, column 1: did not find expected node content",
        ),
        (
            "---\ntitle: Check\nsummary: S\nsection: A\n---\n# Check\n",
            "user-docs/doctor.md: 'order' is a required property",
        ),
        (
            "---\ntitle: Check\nsummary: S\nsection: A\norder: 0\ncolour: red\n---\n# Check\n",
            "user-docs/doctor.md: Additional properties are not allowed ('colour' was unexpected)\n"
            "user-docs/doctor.md: order: 0 is less than the minimum of 1",
        ),
    ],
)
def test_d1_a_page_without_valid_front_matter_does_not_load(
    content_root: Path, text: str, message: str
):
    write_page(content_root, "doctor", text)
    with pytest.raises(ContentError) as raised:
        FsUserDocs(content_root).load("doctor")
    assert str(raised.value).startswith(message)


def test_the_sdist_and_the_wheel_include_the_user_docs():
    targets = BUILD["targets"]
    assert (
        "user-docs" in targets["sdist"]["only-include"],
        "user-docs" in targets["wheel"]["only-include"],
        targets["wheel"]["sources"]["user-docs"],
    ) == (True, True, "coding_study/content/user-docs")


def test_the_bundled_copy_holds_the_pages_cstudy_reads(content_root: Path, tmp_path: Path):
    package = tmp_path / "site-packages" / "coding_study"
    bundled = package / "content"
    bundled.mkdir(parents=True)
    write_docs(content_root)
    for name in ("problems", "schemas", "user-docs"):
        (bundled / name).symlink_to(content_root / name, target_is_directory=True)
    root = find_content_root({}, package)
    assert FsUserDocs(root.path).load("doctor").title == "Check your setup"
