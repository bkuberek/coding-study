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
