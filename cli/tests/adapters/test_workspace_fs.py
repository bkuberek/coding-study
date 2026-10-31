import os
import shutil
import stat
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from coding_study.adapters.file_lock import exclusive_lock
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.domain.errors import LockBusyError
from tests.project_locks import lock_is_held

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


# build folders (docs/specs/runners.md#reference-materialization)

BUILD = ".cs/build/projects/bank-project-java/reference"
BANK_SOURCE = "src/main/java/bank/Bank.java"
BUILD_FILES = {"build.gradle.kts": "plugins {}\n", BANK_SOURCE: "class Bank {}\n"}
OLD_NS = 1_000_000_000


@pytest.fixture
def synced(workspace) -> str:
    workspace.sync_folder(BUILD, BUILD_FILES)
    return BUILD


@pytest.fixture
def elsewhere(workspace) -> Path:
    workspace.write_text("elsewhere/Bank.java", "kept\n")
    return workspace.absolute("elsewhere")


def test_sync_folder_writes_the_files(workspace, synced):
    assert workspace.tracked_files(synced) == ("build.gradle.kts", BANK_SOURCE)


def test_sync_folder_rewrites_a_changed_file(workspace, synced):
    workspace.sync_folder(synced, {**BUILD_FILES, BANK_SOURCE: "class Bank { int id; }\n"})
    assert workspace.read_text(f"{synced}/{BANK_SOURCE}") == "class Bank { int id; }\n"


def test_sync_folder_keeps_the_timestamp_of_an_unchanged_file(workspace, synced):
    unchanged = workspace.absolute(f"{synced}/{BANK_SOURCE}")
    os.utime(unchanged, ns=(OLD_NS, OLD_NS))
    workspace.sync_folder(synced, BUILD_FILES)
    assert unchanged.stat().st_mtime_ns == OLD_NS


def test_sync_folder_deletes_a_file_it_was_not_given(workspace, synced):
    workspace.write_text(f"{synced}/src/main/java/bank/Ledger.java", "class Ledger {}\n")
    workspace.sync_folder(synced, BUILD_FILES)
    assert workspace.tracked_files(synced) == ("build.gradle.kts", BANK_SOURCE)


def test_sync_folder_deletes_a_directory_it_leaves_empty(workspace, synced):
    workspace.write_text(f"{synced}/src/main/java/ledger/Ledger.java", "class Ledger {}\n")
    workspace.sync_folder(synced, BUILD_FILES)
    assert not os.path.lexists(workspace.absolute(f"{synced}/src/main/java/ledger"))


@pytest.mark.parametrize(
    "output",
    [
        "build/classes/java/main/bank/Bank.class",
        ".gradle/configuration-cache/entry.bin",
        ".kotlin/sessions/daemon.salive",
        "target/debug/bank",
        "src/main/java/bank/__pycache__/bank.cpython-313.pyc",
    ],
)
def test_sync_folder_keeps_what_build_tools_wrote(workspace, synced, output):
    workspace.write_text(f"{synced}/{output}", "built\n")
    workspace.sync_folder(synced, BUILD_FILES)
    assert workspace.read_text(f"{synced}/{output}") == "built\n"


def test_sync_folder_replaces_a_link_at_a_files_path(workspace, synced, elsewhere):
    source = workspace.absolute(f"{synced}/{BANK_SOURCE}")
    source.unlink()
    source.symlink_to(elsewhere / "Bank.java")
    workspace.sync_folder(synced, BUILD_FILES)
    assert (source.is_symlink(), source.read_text()) == (False, "class Bank {}\n")


def test_sync_folder_never_writes_through_a_link_at_a_files_path(workspace, synced, elsewhere):
    source = workspace.absolute(f"{synced}/{BANK_SOURCE}")
    source.unlink()
    source.symlink_to(elsewhere / "Bank.java")
    workspace.sync_folder(synced, BUILD_FILES)
    assert (elsewhere / "Bank.java").read_text() == "kept\n"


def test_sync_folder_never_writes_through_a_link_on_the_way(workspace, synced, elsewhere):
    package = workspace.absolute(f"{synced}/src/main/java/bank")
    shutil.rmtree(package)
    package.symlink_to(elsewhere, target_is_directory=True)
    workspace.sync_folder(synced, BUILD_FILES)
    assert sorted(path.name for path in elsewhere.iterdir()) == ["Bank.java"]


def test_sync_folder_removes_a_link_it_was_not_given(workspace, synced, elsewhere):
    link = workspace.absolute(f"{synced}/linked")
    link.symlink_to(elsewhere, target_is_directory=True)
    workspace.sync_folder(synced, BUILD_FILES)
    assert not os.path.lexists(link)


def test_sync_folder_never_deletes_through_a_link(workspace, synced, elsewhere):
    workspace.absolute(f"{synced}/linked").symlink_to(elsewhere, target_is_directory=True)
    workspace.sync_folder(synced, BUILD_FILES)
    assert (elsewhere / "Bank.java").read_text() == "kept\n"


def test_sync_folder_replaces_a_folder_that_is_a_link(workspace, elsewhere):
    folder = workspace.absolute(BUILD)
    folder.parent.mkdir(parents=True)
    folder.symlink_to(elsewhere, target_is_directory=True)
    workspace.sync_folder(BUILD, BUILD_FILES)
    assert (folder.is_symlink(), (elsewhere / "Bank.java").read_text()) == (False, "kept\n")


def test_sync_folder_replaces_a_directory_at_a_files_path(workspace, synced):
    script = workspace.absolute(f"{synced}/build.gradle.kts")
    script.unlink()
    workspace.write_text(f"{synced}/build.gradle.kts/build/output.txt", "built\n")
    workspace.sync_folder(synced, BUILD_FILES)
    assert script.read_text() == "plugins {}\n"


def test_sync_folder_replaces_a_file_on_the_way(workspace, synced):
    shutil.rmtree(workspace.absolute(f"{synced}/src/main/java/bank"))
    workspace.write_text(f"{synced}/src/main/java/bank", "a file\n")
    workspace.sync_folder(synced, BUILD_FILES)
    assert workspace.read_text(f"{synced}/{BANK_SOURCE}") == "class Bank {}\n"


LOCK = ".cs/projects/bank-project-python.lock"


def test_locked_holds_the_lock_for_the_with_block(workspace):
    with workspace.locked(LOCK):
        assert lock_is_held(workspace.absolute(LOCK))


def test_locked_releases_the_lock_after_the_with_block(workspace):
    with workspace.locked(LOCK):
        pass
    assert not lock_is_held(workspace.absolute(LOCK))


def test_locked_releases_the_lock_when_the_block_raises(workspace):
    with pytest.raises(RuntimeError), workspace.locked(LOCK):
        raise RuntimeError("interrupted")
    assert not lock_is_held(workspace.absolute(LOCK))


def test_write_within_writes_the_file_inside_the_folder(workspace, project):
    workspace.write_within(project, "bank/bank.py", "class Bank: pass\n")
    assert workspace.read_text(f"{project}/bank/bank.py") == "class Bank: pass\n"


def test_write_within_creates_missing_directories(workspace, project):
    workspace.write_within(project, "bank/ledger/entries.py", "ENTRIES = []\n")
    assert workspace.read_text(f"{project}/bank/ledger/entries.py") == "ENTRIES = []\n"


def test_write_within_refuses_a_file_that_is_a_link(workspace, project):
    workspace.write_text("elsewhere/hosts", "kept\n")
    workspace.absolute(f"{project}/README.md").unlink()
    workspace.absolute(f"{project}/README.md").symlink_to("../../elsewhere/hosts")
    with pytest.raises(ValueError, match=r"README\.md is a symbolic link"):
        workspace.write_within(project, "README.md", "# Bank\n")


def test_write_within_never_writes_through_a_link(workspace, project):
    workspace.write_text("elsewhere/hosts", "kept\n")
    workspace.absolute(f"{project}/README.md").unlink()
    workspace.absolute(f"{project}/README.md").symlink_to("../../elsewhere/hosts")
    with pytest.raises(ValueError, match="symbolic link"):
        workspace.write_within(project, "README.md", "# Bank\n")
    assert workspace.read_text("elsewhere/hosts") == "kept\n"


def test_write_within_refuses_a_directory_on_the_way_that_is_a_link(workspace, project):
    workspace.write_text("elsewhere/bank.py", "kept\n")
    workspace.remove_folder(f"{project}/bank")
    workspace.absolute(f"{project}/bank").symlink_to("../../elsewhere", target_is_directory=True)
    with pytest.raises(ValueError, match="bank is a symbolic link"):
        workspace.write_within(project, "bank/bank.py", "class Bank: ...\n")


def test_write_within_refuses_a_dangling_link(workspace, project):
    workspace.absolute(f"{project}/README.md").unlink()
    workspace.absolute(f"{project}/README.md").symlink_to("../../nowhere/README.md")
    with pytest.raises(ValueError, match=r"README\.md is a symbolic link"):
        workspace.write_within(project, "README.md", "# Bank\n")


def test_write_within_refuses_a_directory_at_the_files_path(workspace, project):
    workspace.write_text(f"{project}/notes/today.md", "# Today\n")
    with pytest.raises(ValueError, match="notes is a directory"):
        workspace.write_within(project, "notes", "# Notes\n")


def test_write_within_refuses_a_file_on_the_way(workspace, project):
    with pytest.raises(ValueError, match=r"README\.md is not a directory"):
        workspace.write_within(project, "README.md/notes.md", "# Notes\n")


def test_write_within_follows_a_folder_that_is_itself_a_link(workspace, project):
    workspace.absolute("projects/alias").symlink_to("bank-project-python", target_is_directory=True)
    workspace.write_within("projects/alias", "README.md", "# Alias\n")
    assert workspace.read_text(f"{project}/README.md") == "# Alias\n"


def test_read_within_reads_the_bytes_of_a_file_inside_the_folder(workspace, project):
    assert workspace.read_within(project, "bank/bank.py") == b"class Bank: ...\n"


def test_read_within_refuses_a_file_that_is_a_link(workspace, project):
    workspace.write_text("elsewhere/hosts", "secret\n")
    workspace.absolute(f"{project}/README.md").unlink()
    workspace.absolute(f"{project}/README.md").symlink_to("../../elsewhere/hosts")
    with pytest.raises(ValueError, match=r"README\.md is a symbolic link"):
        workspace.read_within(project, "README.md")


def test_read_within_refuses_a_directory_on_the_way_that_is_a_link(workspace, project):
    workspace.write_text("elsewhere/bank.py", "secret\n")
    workspace.remove_folder(f"{project}/bank")
    workspace.absolute(f"{project}/bank").symlink_to("../../elsewhere", target_is_directory=True)
    with pytest.raises(ValueError, match="bank is a symbolic link"):
        workspace.read_within(project, "bank/bank.py")


def test_read_within_refuses_a_directory_at_the_files_path(workspace, project):
    with pytest.raises(ValueError, match="bank is a directory"):
        workspace.read_within(project, "bank")


def test_read_within_refuses_a_file_on_the_way(workspace, project):
    with pytest.raises(ValueError, match=r"README\.md is not a directory"):
        workspace.read_within(project, "README.md/notes.md")


def test_read_within_refuses_a_named_pipe_without_waiting_for_a_writer(workspace, project):
    os.mkfifo(workspace.absolute(f"{project}/bank/pipe"))
    with pytest.raises(ValueError, match="bank/pipe is not a regular file"):
        workspace.read_within(project, "bank/pipe")


def test_read_within_raises_file_not_found_for_a_missing_file(workspace, project):
    with pytest.raises(FileNotFoundError):
        workspace.read_within(project, "bank/ledger.py")


def test_read_within_raises_file_not_found_under_a_missing_directory(workspace, project):
    with pytest.raises(FileNotFoundError):
        workspace.read_within(project, "ledger/entries.py")


def test_read_within_follows_a_folder_that_is_itself_a_link(workspace, project):
    workspace.absolute("projects/alias").symlink_to("bank-project-python", target_is_directory=True)
    assert workspace.read_within("projects/alias", "README.md") == b"# Bank\n"


def file_mode(workspace: WorkspaceFs, path: str) -> int:
    return stat.S_IMODE(workspace.absolute(path).stat().st_mode)


def entries(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def linked_readme(workspace: WorkspaceFs, project: str) -> None:
    """README.md becomes a link to a file outside the folder."""
    workspace.write_text("elsewhere/hosts", "kept\n")
    workspace.absolute(f"{project}/README.md").unlink()
    workspace.absolute(f"{project}/README.md").symlink_to("../../elsewhere/hosts")


def linked_bank(workspace: WorkspaceFs, project: str) -> None:
    """bank/ becomes a link to a directory outside the folder."""
    workspace.write_text("elsewhere/bank.py", "kept\n")
    workspace.remove_folder(f"{project}/bank")
    workspace.absolute(f"{project}/bank").symlink_to("../../elsewhere", target_is_directory=True)


@pytest.fixture
def private_umask() -> Iterator[None]:
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


# writing atomically (docs/specs/web-ui.md#file-api-rules)


def test_write_within_replaces_the_file_instead_of_writing_into_it(workspace, project):
    """A second name for the old file keeps the old bytes: the write renamed a new file over it,
    so no reader ever sees half of the new content."""
    os.link(workspace.absolute(f"{project}/README.md"), workspace.absolute("README.before"))
    workspace.write_within(project, "README.md", "# Bank, saved\n")
    assert workspace.read_text("README.before") == "# Bank\n"


def test_write_within_keeps_the_files_mode(workspace, project):
    workspace.absolute(f"{project}/README.md").chmod(0o600)
    workspace.write_within(project, "README.md", "# Bank, saved\n")
    assert file_mode(workspace, f"{project}/README.md") == 0o600


def test_write_within_gives_a_new_file_mode_0644_whatever_the_umask(
    workspace, project, private_umask
):
    workspace.write_within(project, "bank/ledger.py", "LEDGER = []\n")
    assert file_mode(workspace, f"{project}/bank/ledger.py") == 0o644


def test_write_within_leaves_no_temporary_file_behind(workspace, project):
    workspace.write_within(project, "bank/bank.py", "class Bank: pass\n")
    assert entries(workspace.absolute(f"{project}/bank")) == ["bank.py"]


def test_write_within_refuses_a_named_pipe_without_waiting_for_a_reader(workspace, project):
    os.mkfifo(workspace.absolute(f"{project}/bank/pipe"))
    with pytest.raises(ValueError, match="bank/pipe is not a regular file"):
        workspace.write_within(project, "bank/pipe", "data\n")


def test_write_within_refuses_a_path_that_leaves_the_folder(workspace, project):
    with pytest.raises(ValueError, match=r"\.\./escaped\.py leaves its folder"):
        workspace.write_within(project, "../escaped.py", "escaped\n")


def test_write_within_refuses_an_absolute_path(workspace, project):
    absolute = str(workspace.absolute("escaped.py"))
    with pytest.raises(ValueError, match="is absolute"):
        workspace.write_within(project, absolute, "escaped\n")


# deleting


def test_delete_within_deletes_the_file(workspace, project):
    workspace.delete_within(project, "bank/bank.py")
    assert not workspace.exists(f"{project}/bank/bank.py")


def test_delete_within_refuses_a_file_that_is_a_link(workspace, project):
    linked_readme(workspace, project)
    with pytest.raises(ValueError, match=r"README\.md is a symbolic link"):
        workspace.delete_within(project, "README.md")


def test_delete_within_never_deletes_through_a_directory_that_is_a_link(workspace, project):
    linked_bank(workspace, project)
    with pytest.raises(ValueError, match="bank is a symbolic link"):
        workspace.delete_within(project, "bank/bank.py")
    assert workspace.read_text("elsewhere/bank.py") == "kept\n"


def test_delete_within_refuses_a_directory(workspace, project):
    with pytest.raises(ValueError, match="bank is a directory"):
        workspace.delete_within(project, "bank")


def test_delete_within_refuses_a_named_pipe(workspace, project):
    os.mkfifo(workspace.absolute(f"{project}/bank/pipe"))
    with pytest.raises(ValueError, match="bank/pipe is not a regular file"):
        workspace.delete_within(project, "bank/pipe")


def test_delete_within_raises_file_not_found_for_a_missing_file(workspace, project):
    with pytest.raises(FileNotFoundError):
        workspace.delete_within(project, "bank/ledger.py")


def test_delete_within_refuses_a_path_that_leaves_the_folder(workspace, project):
    workspace.write_text("projects/kept.py", "kept\n")
    with pytest.raises(ValueError, match="leaves its folder"):
        workspace.delete_within(project, "../kept.py")


# moving


def test_move_within_moves_the_files_content(workspace, project):
    workspace.move_within(project, "bank/bank.py", "bank/core.py")
    assert workspace.read_text(f"{project}/bank/core.py") == "class Bank: ...\n"


def test_move_within_removes_the_file_from_its_old_path(workspace, project):
    workspace.move_within(project, "bank/bank.py", "bank/core.py")
    assert not workspace.exists(f"{project}/bank/bank.py")


def test_move_within_creates_missing_directories(workspace, project):
    workspace.move_within(project, "README.md", "docs/guide/README.md")
    assert workspace.read_text(f"{project}/docs/guide/README.md") == "# Bank\n"


def test_move_within_refuses_an_existing_target(workspace, project):
    with pytest.raises(FileExistsError):
        workspace.move_within(project, "README.md", "bank/bank.py")


def test_move_within_keeps_an_existing_target(workspace, project):
    with pytest.raises(FileExistsError):
        workspace.move_within(project, "README.md", "bank/bank.py")
    assert workspace.read_text(f"{project}/bank/bank.py") == "class Bank: ...\n"


def test_move_within_refuses_a_file_that_is_a_link(workspace, project):
    linked_readme(workspace, project)
    with pytest.raises(ValueError, match=r"README\.md is a symbolic link"):
        workspace.move_within(project, "README.md", "NOTES.md")


def test_move_within_never_moves_into_a_directory_that_is_a_link(workspace, project):
    workspace.write_text("elsewhere/kept.py", "kept\n")
    workspace.absolute(f"{project}/out").symlink_to("../../elsewhere", target_is_directory=True)
    with pytest.raises(ValueError, match="out is a symbolic link"):
        workspace.move_within(project, "README.md", "out/README.md")
    assert entries(workspace.absolute("elsewhere")) == ["kept.py"]


def test_move_within_raises_file_not_found_for_a_missing_file(workspace, project):
    with pytest.raises(FileNotFoundError):
        workspace.move_within(project, "bank/ledger.py", "bank/entries.py")


def test_move_within_refuses_a_target_that_leaves_the_folder(workspace, project):
    with pytest.raises(ValueError, match="leaves its folder"):
        workspace.move_within(project, "README.md", "../README.md")


def tells_case_apart(directory: Path) -> bool:
    probe = directory / "Probe"
    probe.write_text("")
    try:
        return not (directory / "probe").exists()
    finally:
        probe.unlink()


def test_move_within_renames_a_file_to_another_case_of_its_name(workspace, project, tmp_path):
    if tells_case_apart(tmp_path):
        pytest.skip("only a file system that ignores case finds the new name taken")
    workspace.move_within(project, "README.md", "Readme.md")
    assert entries(workspace.absolute(project)) == [".venv", "Readme.md", "bank"]


# a lock with a deadline (docs/specs/web-ui.md#file-api-rules)

SHORT_DEADLINE_S = 0.05
LONG_DEADLINE_S = 5.0


@pytest.fixture
def held_lock(workspace) -> Iterator[None]:
    """Another holder of the project's lock, as another `cstudy` would be."""
    with exclusive_lock(workspace.absolute(LOCK)):
        yield


def test_locked_with_deadline_holds_the_lock_for_the_with_block(workspace):
    with workspace.locked_with_deadline(LOCK, LONG_DEADLINE_S):
        assert lock_is_held(workspace.absolute(LOCK))


def test_locked_with_deadline_releases_the_lock_after_the_with_block(workspace):
    with workspace.locked_with_deadline(LOCK, LONG_DEADLINE_S):
        pass
    assert not lock_is_held(workspace.absolute(LOCK))


def test_locked_with_deadline_gives_up_once_the_deadline_passes(workspace, held_lock):
    with (
        pytest.raises(LockBusyError, match=f"another cstudy command held {LOCK}"),
        workspace.locked_with_deadline(LOCK, SHORT_DEADLINE_S),
    ):
        pass


def test_locked_with_deadline_waits_for_a_holder_that_lets_go_in_time(workspace):
    holding = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with exclusive_lock(workspace.absolute(LOCK)):
            holding.set()
            release.wait()

    holder = threading.Thread(target=hold)
    holder.start()
    holding.wait()
    threading.Timer(SHORT_DEADLINE_S, release.set).start()
    with workspace.locked_with_deadline(LOCK, LONG_DEADLINE_S):
        entered = True
    holder.join()
    assert entered
