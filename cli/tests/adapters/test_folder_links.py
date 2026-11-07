"""Code in a sandbox can leave a link to anything in a project folder, and it shows up on your
machine as a real link. `cstudy`'s hash, archive and file code read the link, never what it names
(docs/specs/service-projects.md#mounts)."""

import os
import threading
from pathlib import Path

import pytest

from coding_study.adapters.project_folders import (
    PLAIN_FILE_LIMIT_BYTES,
    declares_its_project,
    go_project_folders,
    tracked_files,
    write_missing_go_work_files,
)
from coding_study.adapters.workspace_fs import WorkspaceFs
from coding_study.adapters.workspace_setup import FsProjectLinks


@pytest.fixture
def secret(tmp_path: Path) -> Path:
    """A file above the project folder."""
    file = tmp_path / "secret.txt"
    file.write_text("one")
    return file


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    project = tmp_path / "workspace" / "projects" / "rooms"
    project.mkdir(parents=True)
    (project / "main.py").write_text("print('hi')\n")
    return project


@pytest.fixture
def workspace(tmp_path: Path) -> WorkspaceFs:
    return WorkspaceFs(tmp_path / "workspace")


FOLDER = "projects/rooms"


def test_the_hash_of_a_folder_does_not_read_what_a_link_names(workspace, folder, secret):
    (folder / "leak").symlink_to(secret)
    before = workspace.content_hash(FOLDER)

    secret.write_text("two")

    assert workspace.content_hash(FOLDER) == before


def test_the_hash_of_a_folder_still_sees_a_link_that_appears(workspace, folder, secret):
    before = workspace.content_hash(FOLDER)

    (folder / "leak").symlink_to(secret)

    assert workspace.content_hash(FOLDER) != before


def test_the_hash_of_a_folder_sees_where_a_link_points(workspace, folder, secret, tmp_path):
    (folder / "leak").symlink_to(secret)
    before = workspace.content_hash(FOLDER)

    (folder / "leak").unlink()
    (folder / "leak").symlink_to(tmp_path)

    assert workspace.content_hash(FOLDER) != before


def test_a_folder_without_links_keeps_the_hash_it_always_had(workspace, folder):
    import hashlib

    expected = hashlib.sha256()
    expected.update(b"main.py")
    expected.update(b"print('hi')\n")

    assert workspace.content_hash(FOLDER) == expected.hexdigest()


def test_the_hash_of_a_file_that_is_a_link_does_not_read_what_it_names(workspace, folder, secret):
    (folder / "uv.lock").symlink_to(secret)
    before = workspace.content_hash(f"{FOLDER}/uv.lock")

    secret.write_text("two")

    assert workspace.content_hash(f"{FOLDER}/uv.lock") == before


def test_a_link_is_no_tracked_file(folder, secret):
    (folder / "leak").symlink_to(secret)

    assert [path.name for path in tracked_files(folder)] == ["main.py"]


def test_an_archive_moves_a_link_as_a_link(workspace, folder, secret, tmp_path):
    (folder / "leak").symlink_to(secret)

    workspace.archive_folder(FOLDER, ".archive/rooms/1-python")

    archived = tmp_path / "workspace" / ".archive" / "rooms" / "1-python" / "leak"
    assert archived.is_symlink()
    assert secret.read_text() == "one"


def test_a_folder_link_left_behind_is_never_descended_into(workspace, folder, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.txt").write_text("x")
    (folder / "away").symlink_to(outside, target_is_directory=True)

    assert workspace.tracked_files(FOLDER) == ("main.py",)


def test_a_service_projects_lock_is_a_tracked_file(folder):
    (folder / "pyproject.toml").write_text('[project]\nname = "rooms"\n')
    (folder / "uv.lock").write_text("version = 1\n")

    assert "uv.lock" in [path.name for path in tracked_files(folder)]


def test_any_other_projects_uv_lock_is_tool_output(folder):
    (folder / "pyproject.toml").write_text("[tool.ruff]\n")
    (folder / "uv.lock").write_text("version = 1\n")

    assert "uv.lock" not in [path.name for path in tracked_files(folder)]


def test_an_archive_of_a_service_project_keeps_its_lock(workspace, folder, tmp_path):
    (folder / "pyproject.toml").write_text('[project]\nname = "rooms"\n')
    (folder / "uv.lock").write_text("version = 1\n")

    workspace.archive_folder(FOLDER, ".archive/rooms/1-python")

    assert (tmp_path / "workspace" / ".archive" / "rooms" / "1-python" / "uv.lock").exists()


def test_a_service_projects_venv_is_never_linked(tmp_path):
    root = tmp_path
    folder = root / "projects" / "rooms"
    folder.mkdir(parents=True)
    (folder / "pyproject.toml").write_text('[project]\nname = "rooms"\n')

    assert FsProjectLinks().unlinked(root) == ()
    assert FsProjectLinks().relink(root) == ()
    assert not (folder / ".venv").exists()


PROJECT_TABLE = "[project]\nname = 'rooms'\n"
ANSWER_WAIT_S = 30.0
"""A read of a pipe with nobody writing never returns at all: this only bounds the test's wait."""


def answered_in_time(folder: Path) -> bool | None:
    """`declares_its_project`, on a thread: a read that hangs must fail the test, not hang it."""
    answers: list[bool] = []
    thread = threading.Thread(
        target=lambda: answers.append(declares_its_project(folder)), daemon=True
    )
    thread.start()
    thread.join(ANSWER_WAIT_S)
    return answers[0] if answers else None


def test_a_project_file_that_declares_its_project_is_read(folder):
    (folder / "pyproject.toml").write_text(PROJECT_TABLE)

    assert declares_its_project(folder)


def test_a_project_file_that_is_a_link_is_not_read(folder, secret):
    secret.write_text(PROJECT_TABLE)
    (folder / "pyproject.toml").symlink_to(secret)

    assert not declares_its_project(folder)


def test_a_project_file_that_is_a_named_pipe_does_not_hang(folder):
    os.mkfifo(folder / "pyproject.toml")

    assert answered_in_time(folder) is False


def test_a_project_file_that_links_to_an_endless_device_is_not_read(folder):
    (folder / "pyproject.toml").symlink_to("/dev/zero")

    assert answered_in_time(folder) is False


def test_a_project_file_that_is_a_directory_declares_nothing(folder):
    (folder / "pyproject.toml").mkdir()

    assert not declares_its_project(folder)


def test_a_project_file_past_the_limit_is_read_no_further(folder):
    filler = "#" * PLAIN_FILE_LIMIT_BYTES + "\n"
    (folder / "pyproject.toml").write_text(filler + PROJECT_TABLE)

    assert not declares_its_project(folder)


def test_a_uv_lock_stays_untracked_behind_a_project_file_that_is_a_link(folder, secret):
    secret.write_text(PROJECT_TABLE)
    (folder / "pyproject.toml").symlink_to(secret)
    (folder / "uv.lock").write_text("locked\n")

    assert "uv.lock" not in [path.name for path in tracked_files(folder)]


GO_MODULE = "module rooms\n\ngo 1.24\n"


def test_a_go_module_file_that_is_a_link_is_not_read(tmp_path, folder, secret):
    secret.write_text(GO_MODULE)
    (folder / "go.mod").symlink_to(secret)

    assert go_project_folders(tmp_path / "workspace") == ()


def test_a_go_module_file_that_is_a_named_pipe_is_no_go_folder(tmp_path, folder):
    os.mkfifo(folder / "go.mod")

    assert go_project_folders(tmp_path / "workspace") == ()


def test_a_go_work_that_is_a_dangling_link_is_not_written_through(tmp_path, folder):
    (folder / "go.mod").write_text(GO_MODULE)
    target = tmp_path / "written-through-the-link"
    (folder / "go.work").symlink_to(target)

    assert write_missing_go_work_files(tmp_path / "workspace") == ()
    assert not target.exists()
