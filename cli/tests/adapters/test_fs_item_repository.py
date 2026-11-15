import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.items import EntryKind, ItemMeta, ItemReferences
from coding_study.domain.labels import Labels
from coding_study.domain.problem import ContentStatus, Difficulty, Track
from coding_study.domain.taxonomy import Scope
from tests.helpers import FIXTURE_PROBLEMS, FIXTURE_RUBRIC_PROBLEMS, SCHEMAS_DIRECTORY

URL_SHORTENER = ItemMeta(
    slug="url-shortener",
    title="URL Shortener",
    track=Track.SYSTEM_DESIGN,
    difficulty=Difficulty.MEDIUM,
    estimate_minutes=45,
    status=ContentStatus.READY,
    order=1,
    labels=Labels(domains=("backend",), job_roles=("backend", "platform"), scope=Scope.SYSTEM),
    references=ItemReferences(
        study_guides=("distributed-systems-study-guide.md#databases",),
        links=("https://en.wikipedia.org/wiki/URL_shortening",),
    ),
    related=("news-feed",),
)
META_YAML = "problems/url-shortener/meta.yaml"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    shutil.copytree(FIXTURE_PROBLEMS, tmp_path / "problems")
    shutil.copytree(FIXTURE_RUBRIC_PROBLEMS, tmp_path / "problems", dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def repository(root: Path) -> FsItemRepository:
    return FsItemRepository(root)


def rewrite(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_loads_a_rubric_problem(repository):
    assert repository.load("url-shortener") == URL_SHORTENER


def test_a_rubric_problem_has_the_kind_of_its_track(repository):
    assert repository.load("retry-wrapper").kind is EntryKind.CODE_REVIEW


def test_optional_fields_default(repository):
    assert (repository.load("news-feed").order, repository.load("news-feed").related) == (1000, ())


def test_slugs_in_name_order(repository):
    assert repository.slugs() == ("news-feed", "retry-wrapper", "url-shortener")


def test_the_autograded_problems_are_absent(repository):
    assert "two-sum" not in repository.slugs()
    assert "two-sum" not in [meta.slug for meta in repository.list_items()]


def test_directories_in_slug_order(repository):
    assert repository.directories() == (
        "problems/news-feed",
        "problems/retry-wrapper",
        "problems/url-shortener",
    )


def test_lists_every_rubric_problem(repository):
    assert [meta.slug for meta in repository.list_items()] == list(repository.slugs())


def test_item_directory(repository):
    assert repository.item_directory("url-shortener") == "problems/url-shortener"


def test_unknown_slug(repository):
    with pytest.raises(UnknownProblemError):
        repository.load("three-sum")


def test_an_autograded_problem_is_an_unknown_slug(repository):
    with pytest.raises(UnknownProblemError):
        repository.load("two-sum")


def test_reads_rubric_problem_files(repository):
    assert repository.read_text("retry-wrapper", "change.diff").startswith("--- a/payments")


def test_an_autograded_problem_has_no_files_here(repository):
    with pytest.raises(UnknownProblemError):
        repository.read_text("two-sum", "problem.md")


def test_missing_file_reads_as_none(repository):
    assert repository.read_text("url-shortener", "change.diff") is None


def test_file_names(repository):
    assert repository.file_names("retry-wrapper") == (
        "change.diff",
        "meta.yaml",
        "prompt.md",
        "reference.md",
        "rubric.md",
        "template.md",
    )


def test_file_names_of_a_missing_directory(repository):
    assert repository.file_names("retry-wrapper", "files") == ()


def test_no_problems_directory(tmp_path):
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    assert FsItemRepository(tmp_path).slugs() == ()


def test_schema_violations_are_content_errors(root, repository):
    rewrite(root, META_YAML, "difficulty: medium", "difficulty: tricky")
    with pytest.raises(ContentError, match=f"{META_YAML}: difficulty: 'tricky' is not one of"):
        repository.load("url-shortener")


def test_directory_must_be_the_slug(root, repository):
    rewrite(root, META_YAML, "slug: url-shortener", "slug: short-links")
    with pytest.raises(
        ContentError, match="slug: directory name url-shortener does not match slug short-links"
    ):
        repository.load("url-shortener")


def test_the_track_must_be_the_kind(root, repository):
    rewrite(root, META_YAML, "track: system-design", "track: code-review")
    with pytest.raises(ContentError, match=f"{META_YAML}: track: "):
        repository.load("url-shortener")


def test_a_folder_that_is_not_named_by_a_slug_is_not_a_rubric_problem(root, repository):
    shutil.copytree(root / "problems" / "url-shortener", root / "problems" / "0007-url-shortener")
    assert repository.slugs() == ("news-feed", "retry-wrapper", "url-shortener")


def test_missing_meta_yaml_is_not_a_rubric_problem(root, repository):
    (root / META_YAML).unlink()
    assert "url-shortener" not in repository.slugs()


def test_listing_reports_every_invalid_rubric_problem(root, repository):
    rewrite(root, META_YAML, "status: ready", "status: done")
    rewrite(root, "problems/news-feed/meta.yaml", "title: News Feed\n", "")
    with pytest.raises(ContentError) as raised:
        repository.list_items()
    assert len(raised.value.issues) == 2
