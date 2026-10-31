"""What the workspace template and the checkout keep out of version control around project folders
(docs/specs/installation-and-workspaces.md#cstudy-init, #developing-coding-study)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.helpers import REPOSITORY_ROOT, WORKSPACE_TEMPLATE

FOLDER = "projects/bank-project-python"


def ignored(repository: Path, path: str) -> bool:
    """Whether git ignores `path` in `repository`, as `git check-ignore` decides."""
    completed = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", path], cwd=repository, check=False
    )
    return completed.returncode == 0


def repository_with(tmp_path: Path, gitignore: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    shutil.copy(gitignore, tmp_path / ".gitignore")
    return tmp_path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A repository with the template's `.gitignore` and a project folder linked to the venv."""
    repository = repository_with(tmp_path, WORKSPACE_TEMPLATE / ".gitignore")
    (repository / "python" / ".venv").mkdir(parents=True)
    (repository / FOLDER).mkdir(parents=True)
    (repository / FOLDER / ".venv").symlink_to("../../python/.venv", target_is_directory=True)
    return repository


def test_the_template_has_a_projects_folder():
    assert (WORKSPACE_TEMPLATE / "projects" / ".gitkeep").is_file()


@pytest.mark.parametrize("path", [f"{FOLDER}/.venv", f"{FOLDER}/uv.lock"])
def test_the_workspace_ignores_the_venv_link_and_uv_lock_of_a_project(workspace, path):
    assert ignored(workspace, path)


@pytest.mark.parametrize(
    "path", [f"{FOLDER}/bank/bank.py", f"{FOLDER}/pyproject.toml", f"{FOLDER}/tests/test_x.py"]
)
def test_the_workspace_tracks_the_files_of_a_project(workspace, path):
    assert not ignored(workspace, path)


def test_the_checkout_ignores_a_projects_folder_at_its_root(tmp_path):
    checkout = repository_with(tmp_path, REPOSITORY_ROOT / ".gitignore")
    assert ignored(checkout, f"{FOLDER}/bank/bank.py")


def test_the_checkout_tracks_a_project_starter(tmp_path):
    checkout = repository_with(tmp_path, REPOSITORY_ROOT / ".gitignore")
    assert not ignored(checkout, "problems/0249-bank-project-python/starter/bank/bank.py")
