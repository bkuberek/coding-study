import shlex
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_files import FsProblemFiles
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.problem_files import WORKSPACE_ROOT
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
    return FsProblemFiles(tmp_path, root_name=WORKSPACE_ROOT)


def test_slugs_of_problem_directories_in_name_order(files):
    assert files.slugs() == ("lru-cache", "two-sum")


def test_a_directory_that_is_not_a_slug_is_misnamed_not_a_problem(files, tmp_path):
    (tmp_path / "problems" / numbered_directory(3, "word-break")).mkdir()
    assert files.slugs() == ("lru-cache", "two-sum")
    assert [found.name for found in files.misnamed()] == [numbered_directory(3, "word-break")]


def make_directory(tmp_path: Path, name: str, meta: str | None = None) -> None:
    directory = tmp_path / "problems" / name
    directory.mkdir()
    if meta is not None:
        (directory / "meta.yaml").write_text(meta)


def fixes(files: FsProblemFiles) -> list[str]:
    return [found.fix("problems") for found in files.misnamed()]


def test_a_numbered_directory_is_renamed_by_the_slug_of_its_meta(files, tmp_path):
    name = numbered_directory(3, "word-break")
    make_directory(tmp_path, name, "slug: break-words\n")
    assert fixes(files) == [
        f"from the workspace root run `mv problems/{name} problems/break-words`"
    ]


def test_a_numbered_directory_without_a_readable_meta_is_renamed_without_its_number(
    files, tmp_path
):
    first, second = numbered_directory(3, "word-break"), numbered_directory(4, "two-pointers")
    make_directory(tmp_path, first)
    make_directory(tmp_path, second, "slug: [\n")
    assert fixes(files) == [
        f"from the workspace root run `mv problems/{first} problems/word-break`",
        f"from the workspace root run `mv problems/{second} problems/two-pointers`",
    ]


def test_a_numbered_directory_with_an_id_is_renamed_and_loses_the_id_line(files, tmp_path):
    name = numbered_directory(5001, "max-gap")
    make_directory(tmp_path, name, "id: '5001'\nslug: max-gap\n")
    assert fixes(files) == [
        f"from the workspace root run `mv problems/{name} problems/max-gap`, "
        "then delete the `id:` line of `problems/max-gap/meta.yaml`"
    ]


def test_a_directory_named_by_a_slug_with_an_id_loses_the_id_line(files, tmp_path):
    make_directory(tmp_path, "max-gap", "id: '5001'\nslug: max-gap\n")
    found = files.misnamed()
    assert [item.name for item in found] == ["max-gap"]
    assert files.slugs() == ("lru-cache", "max-gap", "two-sum")
    assert fixes(files) == [
        "delete the `id:` line of `problems/max-gap/meta.yaml` in the workspace root"
    ]


def test_a_misnamed_directory_with_no_slug_to_take_asks_for_one(files, tmp_path):
    make_directory(tmp_path, "Word Break")
    assert fixes(files) == ["give `problems/Word Break` a slug"]


def test_a_misnamed_directory_with_no_slug_and_an_id_also_loses_the_id_line(files, tmp_path):
    make_directory(tmp_path, "Word Break", "id: '5001'\n")
    assert fixes(files) == [
        "give `problems/Word Break` a slug, then delete the `id:` line of its meta.yaml"
    ]


def test_a_name_with_a_space_gives_a_command_that_survives_pasting(files, tmp_path):
    make_directory(tmp_path, "my problem", "slug: my-problem\n")
    assert fixes(files) == [
        "from the workspace root run `mv 'problems/my problem' problems/my-problem`"
    ]


def test_a_name_with_a_semicolon_is_quoted_so_nothing_else_runs(files, tmp_path):
    make_directory(tmp_path, "x;echo hi", "slug: x\n")
    (command,) = fixes(files)
    assert shlex.split(command.split("`")[1]) == ["mv", "problems/x;echo hi", "problems/x"]


def test_a_slug_already_taken_gives_no_command(files, tmp_path):
    make_directory(tmp_path, numbered_directory(3, "two-sum"))
    assert fixes(files) == [
        "`problems/two-sum` is taken: give `problems/0003-two-sum` a free slug in the "
        "workspace root"
    ]


def test_a_taken_slug_with_an_id_still_loses_the_id_line(files, tmp_path):
    make_directory(tmp_path, numbered_directory(3, "two-sum"), "id: '3'\n")
    assert fixes(files)[0].endswith(
        "a free slug in the workspace root, then delete the `id:` line of its meta.yaml"
    )


def test_two_directories_for_one_slug_give_no_command(files, tmp_path):
    first, second = numbered_directory(3, "word-break"), numbered_directory(4, "word-break")
    make_directory(tmp_path, first)
    make_directory(tmp_path, second)
    assert [found.taken for found in files.misnamed()] == [True, True]
    assert all("is taken" in fix and "mv" not in fix for fix in fixes(files))


def test_hidden_directories_and_pycache_are_no_problems(files, tmp_path):
    for name in (".cs", ".git", "__pycache__"):
        make_directory(tmp_path, name)
    assert files.misnamed() == ()


def test_the_root_is_the_one_the_directory_sits_under(tmp_path):
    make_directory_in = tmp_path / "problems" / numbered_directory(3, "word-break")
    make_directory_in.mkdir(parents=True)
    found = FsProblemFiles(tmp_path, root_name=WORKSPACE_ROOT).misnamed()
    assert [item.fix("problems").split(" run")[0] for item in found] == ["from the workspace root"]
    assert (
        FsProblemFiles(tmp_path).misnamed()[0].fix("problems").startswith("from the content root")
    )


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
