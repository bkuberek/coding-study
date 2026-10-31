"""The state of each file of a project folder against what `cstudy` provided
(docs/specs/cli.md#cstudy-status)."""

import pytest

from coding_study.domain.file_states import (
    FileState,
    FolderFile,
    StarterChanges,
    folder_files,
    starter_changes,
)
from coding_study.domain.project_manifest import FileOrigin, ProjectManifest, ProvidedFile

README = ProvidedFile("README.md", "readme", FileOrigin.STARTER)
ENTRY = ProvidedFile("bank/bank.py", "entry", FileOrigin.STARTER)
LEVEL_1 = ProvidedFile("tests/test_level_1.py", "level-1", FileOrigin.LEVEL, 1)
MANIFEST = ProjectManifest((README, ENTRY, LEVEL_1))
AS_PROVIDED = {"README.md": "readme", "bank/bank.py": "entry", "tests/test_level_1.py": "level-1"}


def state_of(path: str, digests: dict[str, str]) -> FolderFile:
    return next(file for file in folder_files(MANIFEST, digests) if file.path == path)


@pytest.mark.parametrize(
    ("path", "digests", "expected"),
    [
        (
            "README.md",
            AS_PROVIDED,
            FolderFile("README.md", FileOrigin.STARTER, FileState.UNCHANGED),
        ),
        (
            "README.md",
            {**AS_PROVIDED, "README.md": "edited"},
            FolderFile("README.md", FileOrigin.STARTER, FileState.MODIFIED),
        ),
        (
            "bank/bank.py",
            {"README.md": "readme", "tests/test_level_1.py": "level-1"},
            FolderFile("bank/bank.py", FileOrigin.STARTER, FileState.DELETED),
        ),
        (
            "bank/ledger.py",
            {**AS_PROVIDED, "bank/ledger.py": "mine"},
            FolderFile("bank/ledger.py", FileOrigin.YOURS, FileState.ADDED),
        ),
        (
            "tests/test_level_1.py",
            AS_PROVIDED,
            FolderFile("tests/test_level_1.py", FileOrigin.LEVEL, FileState.UNCHANGED, 1),
        ),
        (
            "tests/test_level_1.py",
            {**AS_PROVIDED, "tests/test_level_1.py": "edited"},
            FolderFile("tests/test_level_1.py", FileOrigin.LEVEL, FileState.MODIFIED, 1),
        ),
        (
            "tests/test_level_1.py",
            {"README.md": "readme", "bank/bank.py": "entry"},
            FolderFile("tests/test_level_1.py", FileOrigin.LEVEL, FileState.DELETED, 1),
        ),
    ],
    ids=[
        "starter unchanged",
        "starter modified",
        "starter deleted",
        "yours added",
        "generated unchanged",
        "generated edited",
        "generated deleted",
    ],
)
def test_each_file_has_its_origin_and_state(path, digests, expected):
    assert state_of(path, digests) == expected


def test_folder_files_lists_the_folder_and_the_deleted_files_in_path_order():
    digests = {"README.md": "readme", "bank/ledger.py": "mine", "tests/test_level_1.py": "level-1"}
    assert [file.path for file in folder_files(MANIFEST, digests)] == [
        "README.md",
        "bank/bank.py",
        "bank/ledger.py",
        "tests/test_level_1.py",
    ]


def test_an_empty_folder_without_a_manifest_has_no_files():
    assert folder_files(ProjectManifest(), {}) == ()


def test_starter_changes_name_the_starters_files_changed_and_removed_and_yours_added():
    digests = {"README.md": "edited", "bank/ledger.py": "mine", "tests/test_level_1.py": "edited"}
    assert starter_changes(folder_files(MANIFEST, digests)) == StarterChanges(
        changed=("README.md",), added=("bank/ledger.py",), removed=("bank/bank.py",)
    )


def test_starter_changes_leave_the_generated_test_files_out():
    digests = {"README.md": "readme", "bank/bank.py": "entry"}
    assert starter_changes(folder_files(MANIFEST, digests)) == StarterChanges((), (), ())
