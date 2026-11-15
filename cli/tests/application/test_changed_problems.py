import shutil
from pathlib import Path

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.application.changed_problems import CHANGED_BASE, changed_problems
from tests.fakes import FixedChangedFiles
from tests.helpers import FIXTURE_RUBRIC_PROBLEMS


def slugs(content_root: Path, *paths: str) -> tuple[str, ...]:
    return changed_problems(FsProblemFiles(content_root), FixedChangedFiles(*paths)).slugs


def misnamed(content_root: Path, *paths: str) -> tuple[str, ...]:
    return changed_problems(FsProblemFiles(content_root), FixedChangedFiles(*paths)).misnamed


def test_compares_with_main(content_root):
    changes = FixedChangedFiles()
    changed_problems(FsProblemFiles(content_root), changes)
    assert changes.bases == [CHANGED_BASE] == ["main"]


def test_a_changed_file_selects_its_problem(content_root):
    assert slugs(content_root, "problems/lru-cache/tests.json") == ("lru-cache",)


def test_problems_come_in_name_order_once_each(content_root):
    changed = (
        "problems/lru-cache/meta.yaml",
        "problems/two-sum/meta.yaml",
        "problems/lru-cache/tests.json",
    )
    assert slugs(content_root, *changed) == ("lru-cache", "two-sum")


def test_files_outside_problem_directories_select_nothing(content_root):
    assert slugs(content_root, "README.md", "problems/README.md", "schemas/meta.schema.json") == ()


def test_deleted_problems_select_nothing(content_root):
    assert slugs(content_root, "problems/gone/meta.yaml") == ()


def test_a_changed_misnamed_directory_is_reported_not_selected(content_root):
    (content_root / "problems" / "0099-foo").mkdir()
    changes = changed_problems(
        FsProblemFiles(content_root), FixedChangedFiles("problems/0099-foo/meta.yaml")
    )
    assert (changes.slugs, changes.misnamed, bool(changes)) == ((), ("0099-foo",), True)


def test_an_unchanged_misnamed_directory_is_left_out(content_root):
    (content_root / "problems" / "0099-foo").mkdir()
    assert misnamed(content_root, "problems/lru-cache/tests.json") == ()


def test_nothing_changed_is_falsy(content_root):
    assert not changed_problems(FsProblemFiles(content_root), FixedChangedFiles("README.md"))


def test_a_changed_rubric_problem_is_selected(content_root):
    shutil.copytree(FIXTURE_RUBRIC_PROBLEMS, content_root / "problems", dirs_exist_ok=True)
    assert slugs(content_root, "problems/url-shortener/prompt.md") == ("url-shortener",)
