"""The workspace template on disk (docs/specs/installation-and-workspaces.md#cstudy-init)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.workspace_marker import read_marker
from coding_study.adapters.workspace_setup import FsWorkspaceSetup
from coding_study.domain.problem import Language

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


SHIPPED_SETS = "sets:\n  backend-loop:\n    problems:\n      - two-sum  # mine\n"


@pytest.fixture
def shipped_workspace(tmp_path: Path) -> tuple[FsWorkspaceSetup, Path]:
    """The template this package ships, written with a `sets.yaml` of the user's already there."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "sets.yaml").write_text(SHIPPED_SETS)
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    setup.write_missing(workspace)
    return setup, workspace


def test_the_template_does_not_ship_sets(shipped_workspace):
    setup, workspace = shipped_workspace
    (workspace / "sets.yaml").unlink()
    assert "sets.yaml" not in setup.missing_files(workspace)


def test_writing_what_is_missing_leaves_sets_as_they_are(shipped_workspace):
    _, workspace = shipped_workspace
    assert (workspace / "sets.yaml").read_text() == SHIPPED_SETS


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_the_workspace_gitignore_keeps_sets_tracked(shipped_workspace):
    _, workspace = shipped_workspace
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    ignored = subprocess.run(["git", "check-ignore", "-q", "sets.yaml"], cwd=workspace, check=False)
    assert ignored.returncode == 1


SHARED_ROOTS = {"notes", "problems", "projects", "README.md", ".gitignore", ".cs"}
ALL_FOLDERS = {"python", "typescript", "jvm", "go", "go.work", "rust"}


def written_roots(setup: FsWorkspaceSetup, workspace: Path, *languages: Language) -> set[str]:
    return {path.split("/")[0] for path in setup.write_missing(workspace, languages).written}


def test_a_workspace_of_one_language_gets_its_folder_and_the_shared_files(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    assert written_roots(setup, tmp_path / "ws", Language.PYTHON) == SHARED_ROOTS | {"python"}


def test_go_brings_go_work(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    roots = written_roots(setup, tmp_path / "ws", Language.GO)
    assert roots == SHARED_ROOTS | {"go", "go.work"}


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_either_jvm_language_writes_the_whole_jvm_folder(tmp_path, language):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    written = setup.write_missing(tmp_path / "ws", (language,)).written
    assert {"jvm/gradlew", "jvm/java/build.gradle.kts", "jvm/kotlin/build.gradle.kts"} <= set(
        written
    )


def test_choosing_every_language_writes_what_choosing_none_writes(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    chosen = setup.write_missing(tmp_path / "chosen", tuple(Language)).written
    unchosen = setup.write_missing(tmp_path / "unchosen").written
    assert chosen == unchosen


def test_the_marker_lists_the_chosen_languages_only_when_some_were_chosen(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    setup.write_missing(tmp_path / "chosen", (Language.PYTHON, Language.GO))
    setup.write_missing(tmp_path / "unchosen")
    assert (
        read_marker(tmp_path / "chosen").languages,
        read_marker(tmp_path / "unchosen").languages,
    ) == ((Language.PYTHON, Language.GO), None)


def test_a_narrowed_workspace_lacks_nothing_of_its_languages(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace, (Language.PYTHON,))
    assert setup.missing_files(workspace, (Language.PYTHON,)) == ()


def test_a_deleted_file_of_a_chosen_language_is_missing(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace, (Language.PYTHON, Language.GO))
    (workspace / "go.work").unlink()
    assert setup.missing_files(workspace, (Language.PYTHON, Language.GO)) == ("go.work",)


def test_without_a_choice_the_folders_of_the_other_languages_are_missing(tmp_path):
    setup = FsWorkspaceSetup(tmp_path / "runners", "0.1.0")
    workspace = tmp_path / "ws"
    setup.write_missing(workspace, (Language.PYTHON,))
    missing = {path.split("/")[0] for path in setup.missing_files(workspace)}
    assert missing == ALL_FOLDERS - {"python"}
