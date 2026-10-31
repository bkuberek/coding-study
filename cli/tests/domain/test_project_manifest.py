"""What `cstudy` provided in a project folder
(docs/specs/installation-and-workspaces.md#project-folders)."""

import hashlib

import pytest

from coding_study.domain.project import ProjectFile, ProjectTree
from coding_study.domain.project_manifest import (
    FileOrigin,
    ProjectManifest,
    ProvidedFile,
    content_digest,
    folder_path,
    level_file,
    manifest_path,
    project_lock,
    starter_manifest,
)

README = ProvidedFile("README.md", "aaa", FileOrigin.STARTER)
ENTRY = ProvidedFile("bank/bank.py", "bbb", FileOrigin.STARTER)
LEVEL_1 = ProvidedFile("tests/test_level_1.py", "ccc", FileOrigin.LEVEL, 1)


def test_content_digest_is_the_sha256_of_the_utf8_text():
    assert content_digest("café\n") == hashlib.sha256("café\n".encode()).hexdigest()


def test_with_file_keeps_the_files_in_path_order():
    manifest = ProjectManifest((README,)).with_file(LEVEL_1).with_file(ENTRY)
    assert [file.path for file in manifest.files] == [
        "README.md",
        "bank/bank.py",
        "tests/test_level_1.py",
    ]


def test_with_file_replaces_the_file_of_its_path():
    changed = ProvidedFile("README.md", "ddd", FileOrigin.STARTER)
    assert ProjectManifest((README, ENTRY)).with_file(changed).files == (changed, ENTRY)


def test_file_finds_a_recorded_path():
    assert ProjectManifest((README, ENTRY)).file("bank/bank.py") == ENTRY


def test_file_of_an_unrecorded_path_is_none():
    assert ProjectManifest((README,)).file("bank/bank.py") is None


def test_starter_manifest_records_each_starter_file_with_its_digest():
    tree = ProjectTree(
        (ProjectFile("README.md", 7, "# Bank\n"), ProjectFile("bank/bank.py", 0, ""))
    )
    assert starter_manifest(tree).files == (
        ProvidedFile("README.md", content_digest("# Bank\n"), FileOrigin.STARTER),
        ProvidedFile("bank/bank.py", content_digest(""), FileOrigin.STARTER),
    )


def test_starter_manifest_leaves_out_a_file_that_is_not_text():
    tree = ProjectTree((ProjectFile("logo.png", 3, None),))
    assert starter_manifest(tree).files == ()


def test_level_file_records_the_generated_text_and_its_level():
    assert level_file("tests/test_level_2.py", "def test_ex3(): ...\n", 2) == ProvidedFile(
        "tests/test_level_2.py", content_digest("def test_ex3(): ...\n"), FileOrigin.LEVEL, 2
    )


def test_the_manifest_lives_outside_the_project_folder():
    assert manifest_path("bank-project-python") == ".cs/projects/bank-project-python.json"


def test_the_projects_lock_lives_next_to_its_manifest():
    assert project_lock("bank-project-python") == ".cs/projects/bank-project-python.lock"


@pytest.mark.parametrize(
    ("given", "path"),
    [
        ("bank/bank.py", "bank/bank.py"),
        ("./bank/bank.py", "bank/bank.py"),
        ("bank//bank.py", "bank/bank.py"),
        ("bank/../bank/bank.py", "bank/bank.py"),
        ("tests/./test_level_1.py", "tests/test_level_1.py"),
    ],
)
def test_folder_path_normalizes_a_path_inside_the_folder(given, path):
    assert folder_path(given) == path


@pytest.mark.parametrize(
    ("given", "reason"),
    [
        ("../other/bank.py", "leaves the folder"),
        ("bank/../../bank.py", "leaves the folder"),
        ("..", "leaves the folder"),
        ("/etc/hosts", "is absolute"),
        ("bank\\bank.py", "uses \\"),
        ("", "names no file"),
        ("bank/..", "names no file"),
        (".", "names no file"),
    ],
)
def test_folder_path_refuses_a_path_that_names_no_file_inside_the_folder(given, reason):
    with pytest.raises(ValueError, match=reason.replace("\\", "\\\\")):
        folder_path(given)
