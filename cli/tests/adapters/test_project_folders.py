"""A project folder's tracked files (docs/specs/installation-and-workspaces.md#project-folders)."""

import os
import stat
from pathlib import Path

import pytest

from coding_study.adapters.project_folders import (
    clear_setuid_bits,
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


def test_the_missing_go_work_follows_the_go_line_of_the_folders_module(go_workspace):
    module = go_workspace / "projects/bank-project-go/go.mod"
    module.write_text(GO_MODULE.replace("go 1.24", "go 1.25"))
    (go_workspace / "projects/bank-project-go/go.work").unlink()
    write_missing_go_work_files(go_workspace)
    assert (go_workspace / "projects/bank-project-go/go.work").read_text() == "go 1.25\n\nuse .\n"


def test_a_go_work_of_yours_is_never_rewritten(go_workspace):
    (go_workspace / "projects/bank-project-go/go.work").write_text("go 1.25\n\nuse .\n")
    assert write_missing_go_work_files(go_workspace) == ()


SETUID_EXECUTABLE_ONLY = 0o4111
SETUID_NO_PERMISSION_AT_ALL = 0o4000
DEEPER_THAN_ANY_WALK = 400


def mode_of(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def file_with_mode(path: Path, mode: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(mode)
    return path


@pytest.fixture
def locked_folder(tmp_path: Path):
    """A folder the test locks, opened again at its end so that it can be removed."""
    folder = tmp_path / "locked"
    folder.mkdir()
    yield folder
    folder.chmod(0o755)


def test_a_setuid_bit_comes_off_a_file_with_its_other_bits_kept(tmp_path):
    file = file_with_mode(tmp_path / "tool", 0o4755)

    clear_setuid_bits(tmp_path)

    assert mode_of(file) == 0o755


def test_a_setgid_bit_comes_off_a_file(tmp_path):
    file = file_with_mode(tmp_path / "tool", 0o755)
    file.chmod(0o2755)

    clear_setuid_bits(tmp_path)

    assert mode_of(file) == 0o755


@pytest.mark.parametrize(
    "mode", [SETUID_EXECUTABLE_ONLY, SETUID_NO_PERMISSION_AT_ALL], ids=["4111", "4000"]
)
def test_a_setuid_bit_comes_off_a_file_nobody_can_read(tmp_path, mode):
    file = file_with_mode(tmp_path / "tool", mode)

    clear_setuid_bits(tmp_path)

    assert mode_of(file) == mode & ~stat.S_ISUID


def test_a_setuid_bit_in_a_nested_folder_comes_off(tmp_path):
    file = file_with_mode(tmp_path / "a" / "b" / "tool", 0o4755)

    clear_setuid_bits(tmp_path)

    assert mode_of(file) == 0o755


@pytest.mark.parametrize("mode", [0o000, 0o100, 0o400], ids=["000", "search-only", "read-only"])
def test_a_setuid_bit_in_a_folder_nobody_can_enter_comes_off(tmp_path, locked_folder, mode):
    file = file_with_mode(locked_folder / "tool", 0o4755)
    locked_folder.chmod(mode)

    clear_setuid_bits(tmp_path)

    locked_folder.chmod(0o755)
    assert mode_of(file) == 0o755


def test_a_locked_folder_inside_a_locked_folder_is_opened_too(tmp_path, locked_folder):
    inner = locked_folder / "inner"
    file = file_with_mode(inner / "tool", 0o4755)
    inner.chmod(0o000)
    locked_folder.chmod(0o000)

    clear_setuid_bits(tmp_path)

    locked_folder.chmod(0o755)
    inner.chmod(0o755)
    assert mode_of(file) == 0o755


def test_a_locked_folder_gets_its_mode_back(tmp_path, locked_folder):
    locked_folder.chmod(0o000)

    clear_setuid_bits(tmp_path)

    assert mode_of(locked_folder) == 0o000


def test_a_link_to_a_setuid_file_leaves_the_file_alone(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = file_with_mode(tmp_path / "outside", 0o4755)
    (project / "link").symlink_to(outside)

    clear_setuid_bits(project)

    assert mode_of(outside) == 0o4755


def test_a_link_to_a_folder_is_not_walked(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = file_with_mode(tmp_path / "elsewhere" / "tool", 0o4755)
    (project / "link").symlink_to(outside.parent, target_is_directory=True)

    clear_setuid_bits(project)

    assert mode_of(outside) == 0o4755


def test_a_named_pipe_is_left_alone_and_does_not_hang(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    file = file_with_mode(tmp_path / "tool", 0o4755)

    clear_setuid_bits(tmp_path)

    assert mode_of(file) == 0o755


def test_a_folder_too_deep_to_walk_ends_the_walk_only_there(tmp_path):
    """Past the limit on open files or on recursion, which sandboxed code can build."""
    deep = tmp_path / "a"
    for _ in range(DEEPER_THAN_ANY_WALK):
        deep = deep / "a"
    deep.mkdir(parents=True)
    beside = file_with_mode(tmp_path / "z" / "tool", 0o4755)

    clear_setuid_bits(tmp_path)

    assert mode_of(beside) == 0o755


def test_a_folder_that_is_not_there_is_nothing_to_clear(tmp_path):
    clear_setuid_bits(tmp_path / "absent")
