from pathlib import Path

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.application.changed_problems import CHANGED_BASE, changed_problem_slugs
from tests.fakes import FixedChangedFiles


def slugs(content_root: Path, *paths: str) -> tuple[str, ...]:
    return changed_problem_slugs(FsProblemFiles(content_root), FixedChangedFiles(*paths))


def test_compares_with_main(content_root):
    changes = FixedChangedFiles()
    changed_problem_slugs(FsProblemFiles(content_root), changes)
    assert changes.bases == [CHANGED_BASE] == ["main"]


def test_a_changed_file_selects_its_problem(content_root):
    assert slugs(content_root, "problems/0002-lru-cache/tests.json") == ("lru-cache",)


def test_problems_come_in_directory_order_once_each(content_root):
    changed = (
        "problems/0002-lru-cache/meta.yaml",
        "problems/0001-two-sum/meta.yaml",
        "problems/0002-lru-cache/tests.json",
    )
    assert slugs(content_root, *changed) == ("two-sum", "lru-cache")


def test_files_outside_problem_directories_select_nothing(content_root):
    assert slugs(content_root, "README.md", "problems/README.md", "schemas/meta.schema.json") == ()


def test_deleted_problems_select_nothing(content_root):
    assert slugs(content_root, "problems/0009-gone/meta.yaml") == ()
