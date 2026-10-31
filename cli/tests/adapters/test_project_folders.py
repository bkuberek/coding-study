"""A project folder's tracked files (docs/specs/installation-and-workspaces.md#project-folders)."""

from pathlib import Path

import pytest

from coding_study.adapters.project_folders import (
    go_project_folders,
    remove_untracked,
    tracked_files,
    write_missing_go_work_files,
)
from coding_study.domain.workspace_projects import GoProjectFolder

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


# Go folders

GO_MODULE = """module bank-project-go

go 1.24

require github.com/shopspring/decimal v1.5.0

replace github.com/shopspring/decimal => {}
""".format("../../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal")


@pytest.fixture
def go_workspace(tmp_path: Path) -> Path:
    folder = tmp_path / "projects" / "bank-project-go"
    folder.mkdir(parents=True)
    (folder / "go.mod").write_text(GO_MODULE)
    (folder / "go.work").write_text("go 1.24\n\nuse .\n")
    (tmp_path / ".cs/runtime/runners/go/third_party/github.com/shopspring/decimal").mkdir(
        parents=True
    )
    (tmp_path / "projects" / "bank-project-python").mkdir()
    return tmp_path


def test_a_go_folder_is_a_folder_with_a_go_mod(go_workspace):
    assert go_project_folders(go_workspace) == (
        GoProjectFolder("projects/bank-project-go", "bank-project-go", has_work_file=True),
    )


def test_a_go_folder_without_its_go_work_says_so(go_workspace):
    (go_workspace / "projects/bank-project-go/go.work").unlink()
    (found,) = go_project_folders(go_workspace)
    assert not found.has_work_file


def test_a_replacement_that_names_no_directory_is_unresolved(go_workspace):
    module = go_workspace / "projects/bank-project-go/go.mod"
    module.write_text(GO_MODULE.replace("../../.cs", "../../../.cs"))
    (found,) = go_project_folders(go_workspace)
    assert found.unresolved == (
        "../../../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal",
    )


def test_a_replacement_by_another_module_is_not_a_directory(go_workspace):
    module = go_workspace / "projects/bank-project-go/go.mod"
    module.write_text("module bank\n\nreplace example.com/a => example.com/b v1.0.0\n")
    (found,) = go_project_folders(go_workspace)
    assert found.unresolved == ()


def test_a_workspace_without_projects_has_no_go_folders(tmp_path):
    assert go_project_folders(tmp_path) == ()


def test_the_missing_go_work_files_are_written(go_workspace):
    (go_workspace / "projects/bank-project-go/go.work").unlink()
    written = write_missing_go_work_files(go_workspace)
    work = (go_workspace / "projects/bank-project-go/go.work").read_text()
    assert (written, work) == (("projects/bank-project-go",), "go 1.24\n\nuse .\n")


def test_a_go_work_of_yours_is_never_rewritten(go_workspace):
    (go_workspace / "projects/bank-project-go/go.work").write_text("go 1.25\n\nuse .\n")
    assert write_missing_go_work_files(go_workspace) == ()
