"""The workspace template on disk (docs/specs/installation-and-workspaces.md#cstudy-init)."""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.workspace_setup import FsWorkspaceSetup

TEMPLATE_FILES = {
    "python/pyproject.toml": "[project]\n",
    "python/.ruff_cache/CACHEDIR.TAG": "cache\n",
    "typescript/node_modules/typescript/index.js": "",
    "jvm/gradlew": "#!/bin/sh\n",
    "jvm/.gradle/state": "",
    ".DS_Store": "",
}


@pytest.fixture
def template(tmp_path: Path) -> Path:
    for relative, text in TEMPLATE_FILES.items():
        path = tmp_path / "template" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path / "template"


@pytest.fixture
def setup(template: Path, tmp_path: Path) -> FsWorkspaceSetup:
    return FsWorkspaceSetup(tmp_path / "runners", "0.1.0", template)


def test_only_template_sources_are_written(setup, tmp_path):
    written = setup.write_missing(tmp_path / "ws").written
    assert written == ("jvm/gradlew", "python/pyproject.toml", ".cs/workspace.toml")


def test_caches_in_the_template_are_not_missing_files(setup, tmp_path):
    workspace = tmp_path / "ws"
    setup.write_missing(workspace)
    assert setup.missing_files(workspace) == ()


def test_a_deleted_template_file_is_missing(setup, tmp_path):
    workspace = tmp_path / "ws"
    setup.write_missing(workspace)
    (workspace / "jvm" / "gradlew").unlink()
    assert setup.missing_files(workspace) == ("jvm/gradlew",)


def test_a_workspace_from_before_go_and_rust_is_missing_only_their_files(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace)
    (workspace / "go.work").unlink()
    shutil.rmtree(workspace / "go")
    shutil.rmtree(workspace / "rust")
    missing = setup.missing_files(workspace)
    assert {path.split("/")[0] for path in missing} == {"go.work", "go", "rust"}


def test_a_workspace_from_before_project_problems_is_missing_only_the_projects_folder(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace)
    shutil.rmtree(workspace / "projects")
    assert setup.missing_files(workspace) == ("projects/.gitkeep",)


def test_writing_the_missing_files_restores_go_and_rust(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace)
    shutil.rmtree(workspace / "go")
    shutil.rmtree(workspace / "rust")
    setup.write_missing(workspace)
    assert setup.missing_files(workspace) == ()
    assert (workspace / "rust" / "Cargo.toml").is_file()
