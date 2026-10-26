"""The index cache in `.cs/index.json` (docs/architecture.md#cache-directory-cs): a listing
reads a file again only when its modification time or size changed, and a hit is the same
listing a cold read would give."""

import json
import os
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.document_index import INDEX_FILE, DocumentIndex
from coding_study.adapters.fs_item_repository import FsItemRepository
from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.errors import ContentError
from coding_study.domain.problem import ContentStatus
from tests.helpers import FIXTURE_TRACKS

TWO_SUM_META = Path("problems/0001-two-sum/meta.yaml")
URL_SHORTENER_ITEM = Path("tracks/system-design/url-shortener/item.yaml")
FUTURE_NS = 4_000_000_000_000_000_000


def problems(root: Path) -> FsProblemRepository:
    return FsProblemRepository(root, index=DocumentIndex(root / INDEX_FILE))


def items(root: Path) -> FsItemRepository:
    return FsItemRepository(root, index=DocumentIndex(root / INDEX_FILE))


def rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def keep_stamp(path: Path, edit) -> None:
    """Edit `path` without changing its size or modification time."""
    stamp = path.stat()
    size = len(path.read_bytes())
    edit()
    assert len(path.read_bytes()) == size
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))


def touch_forward(path: Path) -> None:
    os.utime(path, ns=(FUTURE_NS, FUTURE_NS))


@pytest.fixture
def root(content_root: Path) -> Path:
    shutil.copytree(FIXTURE_TRACKS, content_root / "tracks")
    return content_root


def test_a_warm_listing_equals_the_cold_one(root):
    cold = problems(root).list_summaries()
    assert problems(root).list_summaries() == cold


def test_a_warm_listing_equals_the_uncached_one(root):
    problems(root).list_summaries()
    assert problems(root).list_summaries() == FsProblemRepository(root).list_summaries()


def test_the_index_is_written_under_the_cache_directory(root):
    problems(root).list_summaries()
    assert (root / ".cs" / "index.json").is_file()


def test_an_unchanged_file_is_not_read_again(root):
    problems(root).list_summaries()
    meta = root / TWO_SUM_META
    keep_stamp(meta, lambda: rewrite(meta, "status: ready", "status: draft"))
    [two_sum, _] = problems(root).list_summaries()
    assert two_sum.meta.status is ContentStatus.READY


def test_a_changed_modification_time_is_read_again(root):
    problems(root).list_summaries()
    meta = root / TWO_SUM_META
    rewrite(meta, "status: ready", "status: draft")
    touch_forward(meta)
    [two_sum, _] = problems(root).list_summaries()
    assert two_sum.meta.status is ContentStatus.DRAFT


def test_a_changed_size_is_read_again(root):
    problems(root).list_summaries()
    meta = root / TWO_SUM_META
    stamp = meta.stat()
    rewrite(meta, "status: ready", "status: draft\n# longer")
    os.utime(meta, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    [two_sum, _] = problems(root).list_summaries()
    assert two_sum.meta.status is ContentStatus.DRAFT


def test_an_added_problem_is_listed(root):
    problems(root).list_summaries()
    shutil.copytree(root / "problems" / "0001-two-sum", root / "problems" / "0003-three-sum")
    rewrite(root / "problems" / "0003-three-sum" / "meta.yaml", "two-sum", "three-sum")
    rewrite(root / "problems" / "0003-three-sum" / "meta.yaml", 'id: "0001"', 'id: "0003"')
    slugs = [summary.meta.slug for summary in problems(root).list_summaries()]
    assert slugs == ["two-sum", "lru-cache", "three-sum"]


def test_a_removed_problem_is_dropped(root):
    problems(root).list_summaries()
    shutil.rmtree(root / "problems" / "0002-lru-cache")
    assert [s.meta.slug for s in problems(root).list_summaries()] == ["two-sum"]


def test_a_new_reference_file_is_listed(root):
    problems(root).list_summaries()
    solutions = root / "problems" / "0001-two-sum" / "solutions"
    solutions.mkdir()
    (solutions / "hash-map.py").write_text("")
    [two_sum, _] = problems(root).list_summaries()
    assert [str(language) for language in two_sum.reference_languages] == ["python"]


def test_a_file_that_became_invalid_is_reported(root):
    problems(root).list_summaries()
    meta = root / TWO_SUM_META
    rewrite(meta, "status: ready", "status: done")
    touch_forward(meta)
    with pytest.raises(ContentError):
        problems(root).list_summaries()


def test_an_invalid_file_is_still_reported_after_the_first_listing(root):
    meta = root / TWO_SUM_META
    rewrite(meta, "status: ready", "status: done")
    for _ in range(2):
        with pytest.raises(ContentError):
            problems(root).list_summaries()


def test_a_changed_schema_revalidates_every_file(root):
    problems(root).list_summaries()
    schema = root / "schemas" / "meta.schema.json"
    rewrite(schema, '"title"', '"title_renamed"')
    touch_forward(schema)
    with pytest.raises(ContentError):
        problems(root).list_summaries()


def test_a_corrupt_index_is_rebuilt(root):
    problems(root).list_summaries()
    (root / INDEX_FILE).write_text("{not json")
    assert len(problems(root).list_summaries()) == 2
    assert json.loads((root / INDEX_FILE).read_text())["entries"]


def test_an_index_of_another_format_is_rebuilt(root):
    problems(root).list_summaries()
    (root / INDEX_FILE).write_text(json.dumps({"version": 0, "entries": {"stale": 1}}))
    assert len(problems(root).list_summaries()) == 2


def test_an_unchanged_listing_does_not_rewrite_the_index(root):
    problems(root).list_summaries()
    index = root / INDEX_FILE
    touch_forward(index)
    problems(root).list_summaries()
    assert index.stat().st_mtime_ns == FUTURE_NS


def test_a_cache_directory_that_cannot_be_written_does_not_break_listing(root):
    (root / ".cs").write_text("not a directory")
    assert len(problems(root).list_summaries()) == 2


def test_problems_and_items_share_one_index_file(root):
    problems(root).list_summaries()
    items(root).list_items()
    entries = json.loads((root / INDEX_FILE).read_text())["entries"]
    kinds = {Path(key).relative_to(root).parts[0] for key in entries}
    assert kinds == {"problems", "tracks"}


def test_a_warm_item_listing_equals_the_cold_one(root):
    cold = items(root).list_items()
    assert items(root).list_items() == cold


def test_an_unchanged_item_is_not_read_again(root):
    items(root).list_items()
    item = root / URL_SHORTENER_ITEM
    keep_stamp(item, lambda: rewrite(item, "status: ready", "status: draft"))
    assert {meta.slug: meta.status for meta in items(root).list_items()}[
        "url-shortener"
    ] is ContentStatus.READY


def test_a_changed_item_is_read_again(root):
    items(root).list_items()
    item = root / URL_SHORTENER_ITEM
    rewrite(item, "status: ready", "status: draft")
    touch_forward(item)
    statuses = {meta.slug: meta.status for meta in items(root).list_items()}
    assert statuses["url-shortener"] is ContentStatus.DRAFT


def test_a_removed_item_is_dropped(root):
    items(root).list_items()
    shutil.rmtree(root / "tracks" / "system-design" / "news-feed")
    assert "news-feed" not in [meta.slug for meta in items(root).list_items()]


def test_an_added_item_is_listed(root):
    items(root).list_items()
    shutil.copytree(
        root / "tracks" / "system-design" / "news-feed",
        root / "tracks" / "system-design" / "chat-app",
    )
    rewrite(root / "tracks" / "system-design" / "chat-app" / "item.yaml", "news-feed", "chat-app")
    assert "chat-app" in [meta.slug for meta in items(root).list_items()]
