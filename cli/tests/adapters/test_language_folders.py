"""The folders of a workspace's languages on the filesystem, as `cstudy lang remove
--delete-folder` deletes them (docs/specs/cli.md#deleting-a-languages-folder)."""

import os
import stat
from pathlib import Path

import pytest

from coding_study.adapters.language_folders import FsLanguageFolders
from coding_study.domain.errors import FolderNotDeletedError


@pytest.fixture
def root(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    (workspace / "rust" / "target" / "debug").mkdir(parents=True)
    (workspace / "rust" / "target" / "debug" / "deps").write_text("built")
    (workspace / "rust" / "lib.rs").write_text("mine")
    (workspace / "go.work").write_text("go 1.26\n")
    return workspace


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("outside")
    return elsewhere


def test_a_folder_and_a_file_are_present(root):
    folders = FsLanguageFolders(root)
    assert (folders.present("rust"), folders.present("go.work"), folders.present("go")) == (
        True,
        True,
        False,
    )


def test_a_link_is_present_even_when_it_dangles(root):
    (root / "go").symlink_to(root / "missing")
    assert FsLanguageFolders(root).present("go") is True


def test_a_folder_inside_the_workspace_does_not_leave_it(root):
    assert FsLanguageFolders(root).leaves_workspace("rust") is False


def test_a_folder_that_is_a_link_leaves_the_workspace(root, outside):
    (root / "go").symlink_to(outside, target_is_directory=True)
    assert FsLanguageFolders(root).leaves_workspace("go") is True


def test_a_link_to_a_place_inside_the_workspace_is_still_a_link(root):
    (root / "go").symlink_to(root / "rust", target_is_directory=True)
    assert FsLanguageFolders(root).leaves_workspace("go") is True


def test_a_link_inside_the_folder_is_not_asked(root, outside):
    (root / "rust" / "link").symlink_to(outside, target_is_directory=True)
    assert FsLanguageFolders(root).leaves_workspace("rust") is False


def test_deleting_a_folder_removes_all_it_holds(root):
    FsLanguageFolders(root).delete("rust")
    assert not (root / "rust").exists()


def test_deleting_a_file_removes_it(root):
    FsLanguageFolders(root).delete("go.work")
    assert not (root / "go.work").exists()


def test_deleting_what_is_not_there_does_nothing(root):
    FsLanguageFolders(root).delete("go")
    assert sorted(path.name for path in root.iterdir()) == ["go.work", "rust"]


def test_deleting_a_link_inside_the_folder_never_follows_it(root, outside):
    (root / "rust" / "link").symlink_to(outside, target_is_directory=True)
    FsLanguageFolders(root).delete("rust")
    assert ((root / "rust").exists(), (outside / "keep.txt").read_text()) == (False, "outside")


def test_deleting_a_link_removes_the_link_only(root, outside):
    (root / "go").symlink_to(outside, target_is_directory=True)
    FsLanguageFolders(root).delete("go")
    assert (os.path.lexists(root / "go"), (outside / "keep.txt").read_text()) == (False, "outside")


@pytest.mark.skipif(os.geteuid() == 0, reason="root deletes through a read-only folder")
def test_a_folder_that_cannot_be_deleted_whole_names_what_stays(root):
    debug = root / "rust" / "target" / "debug"
    debug.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        with pytest.raises(FolderNotDeletedError) as caught:
            FsLanguageFolders(root).delete("rust")
        assert str(caught.value) == (
            "could not delete rust/target/debug/deps: permission denied; "
            "the rest of rust/ is deleted"
        )
        assert [(root / "rust" / "lib.rs").exists(), (debug / "deps").exists()] == [False, True]
    finally:
        debug.chmod(stat.S_IRWXU)
