"""A project's reference as `cstudy solution` shows it (docs/specs/cli.md#cstudy-solution)."""

from coding_study.domain.project import ProjectFile, ProjectTree
from coding_study.domain.project_reference import ReferenceFile, reference_files


def tree(**files: str) -> ProjectTree:
    return ProjectTree(
        tuple(
            ProjectFile(path.replace("__", "/"), len(text), text)
            for path, text in sorted(files.items())
        )
    )


STARTER = tree(bank__bank_py="class Bank:\n    pass\n", README_md="# Bank\n")


def test_an_added_file_shows_in_full():
    overlay = tree(bank__ledger_py="LEDGER = []\n")
    assert reference_files(STARTER, overlay) == (
        ReferenceFile("bank/ledger_py", True, "LEDGER = []\n"),
    )


def test_a_changed_file_shows_as_a_diff_against_the_starter():
    overlay = tree(bank__bank_py="class Bank:\n    accounts = {}\n")
    (changed,) = reference_files(STARTER, overlay)
    assert changed.text.splitlines() == [
        "--- starter/bank/bank_py",
        "+++ reference/bank/bank_py",
        "@@ -1,2 +1,2 @@",
        " class Bank:",
        "-    pass",
        "+    accounts = {}",
    ]


def test_a_changed_file_is_not_added():
    overlay = tree(bank__bank_py="class Bank:\n    accounts = {}\n")
    assert not reference_files(STARTER, overlay)[0].added


def test_an_unchanged_file_shows_nothing():
    assert reference_files(STARTER, tree(README_md="# Bank\n")) == ()


def test_files_come_in_path_order():
    overlay = tree(z_py="z\n", a_py="a\n")
    assert [file.path for file in reference_files(STARTER, overlay)] == ["a_py", "z_py"]
