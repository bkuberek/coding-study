import shutil
from pathlib import Path

import pytest

from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.domain.errors import ContentError, UnknownProblemError
from coding_study.domain.items import ItemMeta, ItemReferences
from coding_study.domain.problem import ContentStatus, Difficulty, Track
from tests.helpers import FIXTURE_TRACKS, SCHEMAS_DIRECTORY

URL_SHORTENER = ItemMeta(
    slug="url-shortener",
    title="URL Shortener",
    track=Track.SYSTEM_DESIGN,
    difficulty=Difficulty.MEDIUM,
    estimate_minutes=45,
    status=ContentStatus.READY,
    order=1,
    references=ItemReferences(
        study_guides=("distributed-systems-study-guide.md#databases",),
        links=("https://en.wikipedia.org/wiki/URL_shortening",),
    ),
    related=("news-feed",),
)
ITEM_YAML = "tracks/system-design/url-shortener/item.yaml"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    shutil.copytree(FIXTURE_TRACKS, tmp_path / "tracks")
    (tmp_path / "tracks" / "behavioral").mkdir()
    (tmp_path / "tracks" / "behavioral" / "README.md").write_text("# Behavioral\n")
    return tmp_path


@pytest.fixture
def repository(root: Path) -> FsItemRepository:
    return FsItemRepository(root)


def rewrite(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_loads_an_item(repository):
    assert repository.load("url-shortener") == URL_SHORTENER


def test_optional_fields_default(repository):
    assert (repository.load("news-feed").order, repository.load("news-feed").related) == (1000, ())


def test_slugs_in_directory_order(repository):
    assert repository.slugs() == ("retry-wrapper", "news-feed", "url-shortener")


def test_directories_in_slug_order(repository):
    assert repository.directories() == (
        "tracks/code-review/retry-wrapper",
        "tracks/system-design/news-feed",
        "tracks/system-design/url-shortener",
    )


def test_lists_every_item(repository):
    assert [meta.slug for meta in repository.list_items()] == list(repository.slugs())


def test_item_directory(repository):
    assert repository.item_directory("url-shortener") == "tracks/system-design/url-shortener"


def test_unknown_slug(repository):
    with pytest.raises(UnknownProblemError):
        repository.load("two-sum")


def test_reads_item_files(repository):
    assert repository.read_text("retry-wrapper", "change.diff").startswith("--- a/payments")


def test_missing_file_reads_as_none(repository):
    assert repository.read_text("url-shortener", "change.diff") is None


def test_file_names(repository):
    assert repository.file_names("retry-wrapper") == (
        "change.diff",
        "item.yaml",
        "prompt.md",
        "reference.md",
        "rubric.md",
        "template.md",
    )


def test_file_names_of_a_missing_directory(repository):
    assert repository.file_names("retry-wrapper", "files") == ()


def test_no_tracks_directory(tmp_path):
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    assert FsItemRepository(tmp_path).slugs() == ()


def test_schema_violations_are_content_errors(root, repository):
    rewrite(root, ITEM_YAML, "difficulty: medium", "difficulty: tricky")
    with pytest.raises(ContentError, match=f"{ITEM_YAML}: difficulty: 'tricky' is not one of"):
        repository.load("url-shortener")


def test_directory_must_be_the_slug(root, repository):
    rewrite(root, ITEM_YAML, "slug: url-shortener", "slug: short-links")
    with pytest.raises(
        ContentError, match="slug: directory url-shortener does not match slug short-links"
    ):
        repository.load("url-shortener")


def test_parent_directory_must_be_the_track(root, repository):
    rewrite(root, ITEM_YAML, "track: system-design", "track: code-review")
    with pytest.raises(
        ContentError, match="track: item is in tracks/system-design but its track is code-review"
    ):
        repository.load("url-shortener")


def test_missing_item_yaml(root, repository):
    (root / ITEM_YAML).unlink()
    with pytest.raises(ContentError, match=f"{ITEM_YAML}: file not found"):
        repository.load("url-shortener")


def test_listing_reports_every_invalid_item(root, repository):
    rewrite(root, ITEM_YAML, "status: ready", "status: done")
    rewrite(root, "tracks/system-design/news-feed/item.yaml", "title: News Feed\n", "")
    with pytest.raises(ContentError) as raised:
        repository.list_items()
    assert len(raised.value.issues) == 2
