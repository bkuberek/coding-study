import os
from pathlib import Path

import pytest

from coding_study.adapters.workspace_fs import WorkspaceFs

STUB = "python/practice/two_sum.py"


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspaceFs:
    return WorkspaceFs(tmp_path)


def test_write_creates_parent_directories(workspace, tmp_path):
    workspace.write_text(STUB, "pass\n")
    assert (tmp_path / STUB).read_text() == "pass\n"


def test_exists_after_write(workspace):
    workspace.write_text(STUB, "pass\n")
    assert workspace.exists(STUB)


def test_missing_file_does_not_exist(workspace):
    assert not workspace.exists(STUB)


def test_read_text(workspace):
    workspace.write_text(STUB, "pass\n")
    assert workspace.read_text(STUB) == "pass\n"


def test_move_into_returns_the_new_path(workspace):
    workspace.write_text(STUB, "pass\n")
    assert workspace.move_into(STUB, ".archive/two-sum/1-python") == (
        ".archive/two-sum/1-python/two_sum.py"
    )


def test_move_into_removes_the_original(workspace):
    workspace.write_text(STUB, "pass\n")
    workspace.move_into(STUB, ".archive/two-sum/1-python")
    assert not workspace.exists(STUB)


def test_move_into_keeps_the_content(workspace):
    workspace.write_text(STUB, "pass\n")
    moved = workspace.move_into(STUB, ".archive/two-sum/1-python")
    assert workspace.read_text(moved) == "pass\n"


def test_content_hash_of_a_file_changes_with_its_content(workspace):
    workspace.write_text(STUB, "a\n")
    before = workspace.content_hash(STUB)
    workspace.write_text(STUB, "b\n")
    assert workspace.content_hash(STUB) != before


def test_content_hash_of_a_directory_covers_every_file(workspace):
    package = "jvm/java/src/main/java/practice/two_sum"
    workspace.write_text(f"{package}/Solution.java", "class Solution {}\n")
    before = workspace.content_hash(package)
    workspace.write_text(f"{package}/Helper.java", "class Helper {}\n")
    assert workspace.content_hash(package) != before


def test_content_hash_of_a_missing_path_is_stable(workspace):
    assert workspace.content_hash(STUB) == workspace.content_hash(STUB)


def test_absolute_path(workspace, tmp_path):
    assert workspace.absolute(STUB) == tmp_path / STUB


# project folders (docs/specs/installation-and-workspaces.md#project-folders)

PROJECT = "projects/bank-project-python"
VENV_LINK = f"{PROJECT}/.venv"
SHARED_VENV_TARGET = "../../python/.venv"
ARCHIVE = ".archive/bank-project-python/3-python"


@pytest.fixture
def shared_venv(workspace) -> Path:
    workspace.write_text("python/.venv/bin/python", "#!/bin/sh\n")
    return workspace.absolute("python/.venv")


@pytest.fixture
def project(workspace, shared_venv) -> str:
    workspace.write_text(f"{PROJECT}/bank/bank.py", "class Bank: ...\n")
    workspace.write_text(f"{PROJECT}/README.md", "# Bank\n")
    workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)
    return PROJECT


@pytest.mark.parametrize(
    "untracked",
    [
        "bank/__pycache__/bank.cpython-313.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".ruff_cache/CACHEDIR.TAG",
        "node_modules/typescript/index.js",
        "uv.lock",
    ],
)
def test_content_hash_of_a_project_folder_leaves_out_untracked_files(workspace, project, untracked):
    before = workspace.content_hash(project)
    workspace.write_text(f"{project}/{untracked}", "generated\n")
    assert workspace.content_hash(project) == before


def test_content_hash_of_a_project_folder_leaves_out_the_shared_venv(workspace, project):
    before = workspace.content_hash(project)
    workspace.write_text("python/.venv/lib/site.py", "installed\n")
    assert workspace.content_hash(project) == before


def test_content_hash_of_a_project_folder_covers_a_nested_file(workspace, project):
    before = workspace.content_hash(project)
    workspace.write_text(f"{project}/bank/ledger/entries.py", "ENTRIES = []\n")
    assert workspace.content_hash(project) != before


def test_content_hash_of_a_project_folder_covers_relative_paths(workspace, project):
    before = workspace.content_hash(project)
    workspace.move_into(f"{project}/README.md", f"{project}/docs")
    assert workspace.content_hash(project) != before


def test_content_hash_of_a_project_folder_does_not_depend_on_its_location(workspace, project):
    workspace.write_text("projects/copy/bank/bank.py", "class Bank: ...\n")
    workspace.write_text("projects/copy/README.md", "# Bank\n")
    assert workspace.content_hash("projects/copy") == workspace.content_hash(project)


def test_tracked_files_lists_a_folders_files_relative_to_it_in_path_order(workspace, project):
    workspace.write_text(f"{project}/bank/models.py", "MODELS = []\n")
    assert workspace.tracked_files(project) == ("README.md", "bank/bank.py", "bank/models.py")


@pytest.mark.parametrize(
    "untracked",
    [
        "bank/__pycache__/bank.cpython-313.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".ruff_cache/CACHEDIR.TAG",
        "node_modules/typescript/index.js",
        "uv.lock",
    ],
)
def test_tracked_files_leaves_out_untracked_files(workspace, project, untracked):
    workspace.write_text(f"{project}/{untracked}", "generated\n")
    assert untracked not in workspace.tracked_files(project)


def test_tracked_files_leaves_out_the_shared_venv(workspace, project):
    assert workspace.tracked_files(project) == ("README.md", "bank/bank.py")


def test_tracked_files_never_follows_a_link_to_a_directory(workspace, project):
    workspace.write_text("elsewhere/notes.md", "# Notes\n")
    workspace.absolute(f"{project}/linked").symlink_to("../../elsewhere", target_is_directory=True)
    assert "linked/notes.md" not in workspace.tracked_files(project)


def test_tracked_files_of_a_missing_folder_is_empty(workspace):
    assert workspace.tracked_files(PROJECT) == ()


def test_ensure_link_creates_a_relative_link(workspace, shared_venv):
    workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)
    assert workspace.absolute(VENV_LINK).readlink() == Path(SHARED_VENV_TARGET)


def test_the_link_reaches_the_shared_venv(workspace, shared_venv):
    workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)
    assert workspace.absolute(VENV_LINK).resolve() == shared_venv.resolve()


def test_ensure_link_reports_a_new_link(workspace, shared_venv):
    assert workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)


def test_ensure_link_leaves_a_working_link_alone(workspace, project):
    assert not workspace.ensure_link(VENV_LINK, "../../elsewhere/.venv")


def test_ensure_link_keeps_the_target_of_a_working_link(workspace, project):
    workspace.ensure_link(VENV_LINK, "../../elsewhere/.venv")
    assert workspace.absolute(VENV_LINK).readlink() == Path(SHARED_VENV_TARGET)


def test_ensure_link_recreates_a_dangling_link(workspace, shared_venv):
    workspace.absolute(PROJECT).mkdir(parents=True)
    workspace.absolute(VENV_LINK).symlink_to("/nowhere/.venv")
    workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)
    assert workspace.absolute(VENV_LINK).readlink() == Path(SHARED_VENV_TARGET)


def test_ensure_link_leaves_a_directory_alone(workspace, shared_venv):
    workspace.write_text(f"{VENV_LINK}/pyvenv.cfg", "home = /usr\n")
    assert not workspace.ensure_link(VENV_LINK, SHARED_VENV_TARGET)


def test_archive_folder_moves_the_tracked_files(workspace, project):
    workspace.archive_folder(project, ARCHIVE)
    assert workspace.read_text(f"{ARCHIVE}/bank/bank.py") == "class Bank: ...\n"


def test_archive_folder_removes_the_folder(workspace, project):
    workspace.archive_folder(project, ARCHIVE)
    assert not workspace.exists(project)


@pytest.mark.parametrize("untracked", [".venv", "bank/__pycache__", "uv.lock"])
def test_archive_folder_leaves_untracked_entries_out(workspace, project, untracked):
    workspace.write_text(f"{project}/bank/__pycache__/bank.cpython-313.pyc", "bytecode\n")
    workspace.write_text(f"{project}/uv.lock", "version = 1\n")
    workspace.archive_folder(project, ARCHIVE)
    assert not os.path.lexists(workspace.absolute(f"{ARCHIVE}/{untracked}"))


def test_archive_folder_never_deletes_through_the_venv_link(workspace, project, shared_venv):
    workspace.archive_folder(project, ARCHIVE)
    assert (shared_venv / "bin" / "python").is_file()


def test_archive_folder_refuses_an_existing_destination(workspace, project):
    workspace.write_text(f"{ARCHIVE}/notes.md", "an earlier attempt\n")
    with pytest.raises(FileExistsError):
        workspace.archive_folder(project, ARCHIVE)


def test_remove_folder_deletes_the_folder(workspace, project):
    workspace.remove_folder(project)
    assert not os.path.lexists(workspace.absolute(project))


def test_remove_folder_never_deletes_through_the_venv_link(workspace, project, shared_venv):
    workspace.remove_folder(project)
    assert (shared_venv / "bin" / "python").is_file()


def test_remove_folder_unlinks_a_link_to_a_folder(workspace, shared_venv):
    workspace.absolute(PROJECT).parent.mkdir(parents=True)
    workspace.absolute(PROJECT).symlink_to(shared_venv)
    workspace.remove_folder(PROJECT)
    assert (os.path.lexists(workspace.absolute(PROJECT)), (shared_venv / "bin").is_dir()) == (
        False,
        True,
    )


def test_remove_folder_leaves_its_siblings_alone(workspace, project):
    workspace.write_text("projects/other/README.md", "# Other\n")
    workspace.remove_folder(project)
    assert workspace.exists("projects/other/README.md")


def test_remove_folder_of_a_missing_path_does_nothing(workspace):
    workspace.remove_folder(PROJECT)
    assert not workspace.exists(PROJECT)
