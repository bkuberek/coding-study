"""Code in a sandbox can leave a link to anything in a project folder, and it shows up on your
machine as a real link. `cstudy`'s hash, archive and file code read the link, never what it names
(docs/specs/service-projects.md#mounts)."""

from pathlib import Path

import pytest

from coding_study.adapters.project_folders import tracked_files
from coding_study.adapters.workspace_fs import WorkspaceFs


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
