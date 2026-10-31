"""The `.venv` links of a workspace's Python project folders, and where its venv's console
scripts think the venv is
(docs/specs/installation-and-workspaces.md#cstudy-doctor-in-a-workspace)."""

from pathlib import Path

import pytest

from coding_study.adapters.workspace_setup import FsProjectLinks

LINK_TARGET = "../../python/.venv"
BANK = "projects/bank-project-python"
LOT = "projects/parking-lot-python"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "python" / ".venv" / "bin").mkdir(parents=True)
    return tmp_path


def python_folder(root: Path, folder: str) -> Path:
    (root / folder).mkdir(parents=True)
    (root / folder / "pyproject.toml").write_text("[tool.ruff]\n")
    return root / folder


def linked(root: Path, folder: str, target: str = LINK_TARGET) -> Path:
    project = python_folder(root, folder)
    (project / ".venv").symlink_to(target, target_is_directory=True)
    return project


def script(root: Path, name: str, text: str) -> None:
    (root / "python" / ".venv" / "bin" / name).write_text(text)


def test_a_linked_folder_is_not_reported(root):
    linked(root, BANK)
    assert FsProjectLinks().unlinked(root) == ()


def test_folders_without_a_link_or_with_a_dangling_one_are_reported_in_path_order(root):
    python_folder(root, LOT)
    linked(root, BANK, "../../elsewhere/.venv")
    assert FsProjectLinks().unlinked(root) == (BANK, LOT)


def test_a_typescript_folder_has_no_link_to_report(root):
    (root / "projects" / "bank-project-typescript").mkdir(parents=True)
    (root / "projects" / "bank-project-typescript" / "package.json").write_text("{}\n")
    assert FsProjectLinks().unlinked(root) == ()


def test_a_workspace_without_projects_has_nothing_to_report(root):
    assert FsProjectLinks().unlinked(root) == ()


def test_relinking_links_each_folder_to_the_workspace_venv_by_relative_path(root):
    project = python_folder(root, BANK)
    FsProjectLinks().relink(root)
    link = project / ".venv"
    assert (link.readlink(), link.resolve()) == (
        Path(LINK_TARGET),
        (root / "python/.venv").resolve(),
    )


def test_relinking_replaces_a_dangling_link(root):
    project = linked(root, BANK, "../../elsewhere/.venv")
    FsProjectLinks().relink(root)
    assert (project / ".venv").readlink() == Path(LINK_TARGET)


def test_relinking_returns_the_folders_it_relinked(root):
    linked(root, LOT)
    python_folder(root, BANK)
    assert FsProjectLinks().relink(root) == (BANK,)


def test_a_venv_whose_scripts_name_it_has_not_moved(root):
    script(root, "pytest", f"#!{root}/python/.venv/bin/python\nimport pytest\n")
    assert FsProjectLinks().moved_venv(root) is None


def test_a_venv_whose_scripts_name_another_path_has_moved(root):
    script(root, "pytest", "#!/old/ws/python/.venv/bin/python3\nimport pytest\n")
    assert FsProjectLinks().moved_venv(root) == "/old/ws/python/.venv"


def test_a_long_path_shebang_is_read_through_its_shell_trampoline(root):
    trampoline = "#!/bin/sh\n'''exec' '/old/ws/python/.venv/bin/python' \"$0\" \"$@\"\n' '''\n"
    script(root, "pytest", trampoline)
    assert FsProjectLinks().moved_venv(root) == "/old/ws/python/.venv"


def test_scripts_that_are_not_python_are_skipped(root):
    script(root, "activate", "# This file must be used with source\n")
    script(root, "a-shell-tool", "#!/bin/bash\necho\n")
    script(root, "pytest", "#!/old/ws/python/.venv/bin/python\n")
    assert FsProjectLinks().moved_venv(root) == "/old/ws/python/.venv"


def test_a_venv_reached_through_a_link_has_not_moved(tmp_path):
    shared = tmp_path / "shared" / ".venv"
    (shared / "bin").mkdir(parents=True)
    (shared / "bin" / "pytest").write_text(f"#!{shared}/bin/python\n")
    (tmp_path / "ws" / "python").mkdir(parents=True)
    (tmp_path / "ws" / "python" / ".venv").symlink_to(shared, target_is_directory=True)
    assert FsProjectLinks().moved_venv(tmp_path / "ws") is None


def test_a_venv_without_scripts_has_nothing_to_read(root):
    assert FsProjectLinks().moved_venv(root) is None


def test_a_workspace_without_a_venv_has_nothing_to_read(tmp_path):
    assert FsProjectLinks().moved_venv(tmp_path) is None
