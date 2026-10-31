"""A project folder's tracked files (docs/specs/installation-and-workspaces.md#project-folders)."""

from pathlib import Path

import pytest

from coding_study.adapters.project_folders import remove_untracked, tracked_files

UNTRACKED = (
    "uv.lock",
    "__pycache__/conftest.cpython-313.pyc",
    "bank/__pycache__/bank.cpython-313.pyc",
    ".pytest_cache/v/cache/lastfailed",
    ".ruff_cache/CACHEDIR.TAG",
    "node_modules/typescript/index.js",
)


@pytest.fixture
def shared_venv(tmp_path: Path) -> Path:
    venv = tmp_path / "python" / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("#!/bin/sh\n")
    return venv


@pytest.fixture
def folder(tmp_path: Path, shared_venv: Path) -> Path:
    project = tmp_path / "projects" / "bank-project-python"
    for relative in ("README.md", "bank/bank.py", "tests/test_level_1.py", *UNTRACKED):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{relative}\n")
    (project / ".venv").symlink_to("../../python/.venv", target_is_directory=True)
    return project


def relative(folder: Path, files: list[Path]) -> list[str]:
    return [file.relative_to(folder).as_posix() for file in files]


def test_tracked_files_are_the_folder_files_in_path_order(folder):
    assert relative(folder, tracked_files(folder)) == [
        "README.md",
        "bank/bank.py",
        "tests/test_level_1.py",
    ]


def test_a_linked_directory_is_never_walked(folder, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "notes.md").write_text("outside\n")
    (folder / "linked").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    assert "linked/notes.md" not in relative(folder, tracked_files(folder))


def test_a_missing_folder_has_no_tracked_files(tmp_path):
    assert tracked_files(tmp_path / "missing") == []


@pytest.mark.parametrize("path", [".venv", *UNTRACKED])
def test_removing_untracked_entries_deletes_them(folder, path):
    remove_untracked(folder)
    assert not (folder / path).exists()


def test_removing_untracked_entries_removes_the_venv_link_itself(folder):
    remove_untracked(folder)
    assert not (folder / ".venv").is_symlink()


def test_removing_untracked_entries_never_follows_the_venv_link(folder, shared_venv):
    remove_untracked(folder)
    assert (shared_venv / "bin" / "python").is_file()


def test_removing_untracked_entries_keeps_the_tracked_files(folder):
    remove_untracked(folder)
    assert relative(folder, tracked_files(folder)) == [
        "README.md",
        "bank/bank.py",
        "tests/test_level_1.py",
    ]
