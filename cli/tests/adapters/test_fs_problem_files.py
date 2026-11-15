from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.domain.errors import UnknownProblemError
from tests.helpers import numbered_directory


@pytest.fixture
def files(tmp_path: Path) -> FsProblemFiles:
    problem = tmp_path / "problems" / "two-sum"
    (problem / "solutions").mkdir(parents=True)
    (problem / "problem.md").write_text("# Two Sum\n")
    (problem / "solutions" / "hash-map.py").write_text("x = 1\n")
    (problem / "solutions" / "brute-force.py").write_text("x = 2\n")
    (problem / "solutions" / "nested").mkdir()
    (tmp_path / "problems" / "lru-cache").mkdir()
    (tmp_path / "problems" / "README.md").write_text("")
    return FsProblemFiles(tmp_path)


def test_slugs_of_problem_directories_in_name_order(files):
    assert files.slugs() == ("lru-cache", "two-sum")


def test_a_directory_that_is_not_a_slug_is_misnamed_not_a_problem(files, tmp_path):
    (tmp_path / "problems" / numbered_directory(3, "word-break")).mkdir()
    assert files.slugs() == ("lru-cache", "two-sum")
    assert [found.name for found in files.misnamed()] == [numbered_directory(3, "word-break")]


def test_a_numbered_directory_is_renamed_by_the_slug_of_its_meta(files, tmp_path):
    numbered = tmp_path / "problems" / numbered_directory(3, "word-break")
    numbered.mkdir()
    (numbered / "meta.yaml").write_text("slug: break-words\n")
    assert files.misnamed()[0].rename("problems") == (
        f"mv problems/{numbered_directory(3, 'word-break')} problems/break-words"
    )


def test_a_numbered_directory_without_a_readable_meta_is_renamed_without_its_number(
    files, tmp_path
):
    first, second = numbered_directory(3, "word-break"), numbered_directory(4, "two-pointers")
    (tmp_path / "problems" / first).mkdir()
    (tmp_path / "problems" / second).mkdir()
    (tmp_path / "problems" / second / "meta.yaml").write_text("slug: [\n")
    assert [found.rename("problems") for found in files.misnamed()] == [
        f"mv problems/{first} problems/word-break",
        f"mv problems/{second} problems/two-pointers",
    ]


def test_a_misnamed_directory_with_no_slug_to_take_has_no_rename(files, tmp_path):
    (tmp_path / "problems" / "Word Break").mkdir()
    assert [found.rename("problems") for found in files.misnamed()] == [None]


def test_no_slugs_without_a_problems_directory(tmp_path):
    assert FsProblemFiles(tmp_path).slugs() == ()


def test_problem_directory_is_repository_relative(files):
    assert files.problem_directory("two-sum") == "problems/two-sum"


def test_unknown_slug(files):
    with pytest.raises(UnknownProblemError):
        files.problem_directory("three-sum")


def test_reads_a_problem_file(files):
    assert files.read_text("two-sum", "problem.md") == "# Two Sum\n"


def test_missing_file_reads_as_none(files):
    assert files.read_text("two-sum", "generator.py") is None


def test_file_names_in_a_subdirectory_are_sorted_files_only(files):
    assert files.file_names("two-sum", "solutions") == ("brute-force.py", "hash-map.py")


def test_file_names_at_the_top(files):
    assert files.file_names("two-sum") == ("problem.md",)


def test_file_names_of_a_missing_directory(files):
    assert files.file_names("lru-cache", "solutions") == ()


def test_path_is_absolute(files, tmp_path):
    assert files.path("two-sum", "problem.md") == tmp_path / "problems/two-sum/problem.md"


def test_fingerprint_is_stable(files):
    names = ["problem.md", "solutions/hash-map.py"]
    assert files.fingerprint("two-sum", names) == files.fingerprint("two-sum", names)


def test_fingerprint_changes_with_content(files, tmp_path):
    before = files.fingerprint("two-sum", ["problem.md"])
    (tmp_path / "problems/two-sum/problem.md").write_text("# Changed\n")
    assert files.fingerprint("two-sum", ["problem.md"]) != before


def test_fingerprint_tells_a_missing_file_from_an_empty_one(files, tmp_path):
    missing = files.fingerprint("two-sum", ["generator.py"])
    (tmp_path / "problems/two-sum/generator.py").write_text("")
    assert files.fingerprint("two-sum", ["generator.py"]) != missing


def test_other_problems_directory(tmp_path):
    (tmp_path / "runners/conformance/conformance-types").mkdir(parents=True)
    assert FsProblemFiles(tmp_path, "runners/conformance").slugs() == ("conformance-types",)
