"""`cstudy init` (docs/specs/installation-and-workspaces.md#cstudy-init)."""

import os
import shutil
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import REPOSITORY_ROOT, mark_workspace

runner = CliRunner()
PRACTICE_PROJECT_FILES = (
    "python/pyproject.toml",
    "python/uv.lock",
    "typescript/package.json",
    "typescript/support.ts",
    "jvm/settings.gradle.kts",
    "jvm/gradlew",
    "jvm/gradle/wrapper/gradle-wrapper.jar",
    "go/go.mod",
    "go/practice/.gitkeep",
    "go.work",
    "rust/Cargo.toml",
    "rust/.cargo/config.toml",
    "rust/lib.rs",
    "rust/practice/.gitkeep",
)
VSCODE_TASKS = ".vscode/tasks.json"
IDEA_MISC = ".idea/misc.xml"


def init(*arguments: str):
    return runner.invoke(cli.app, ["init", *arguments])


@pytest.fixture
def target(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def test_init_creates_the_directory_and_exits_0(target):
    result = init(str(target))
    assert (result.exit_code, target.is_dir()) == (0, True)


@pytest.mark.parametrize("relative", PRACTICE_PROJECT_FILES)
def test_init_writes_the_practice_projects(target, relative):
    init(str(target))
    assert (target / relative).is_file()


@pytest.mark.parametrize("relative", ["README.md", ".gitignore", "notes", "problems", "projects"])
def test_init_writes_the_workspace_files(target, relative):
    init(str(target))
    assert (target / relative).exists()


def test_init_writes_the_marker_with_the_schema(target):
    init(str(target))
    marker = tomllib.loads((target / ".cs" / "workspace.toml").read_text())
    assert marker["schema"] == 1


def test_init_makes_the_gradle_wrapper_executable(target):
    init(str(target))
    assert os.access(target / "jvm" / "gradlew", os.X_OK)


def test_init_materializes_the_runner_runtime(target):
    init(str(target))
    runner_script = target / ".cs" / "runtime" / "runners" / "typescript" / "runner.ts"
    assert runner_script.is_file()


def test_the_new_directory_is_a_workspace(target):
    init(str(target))
    result = runner.invoke(cli.app, ["--workspace", str(target), "stats"])
    assert result.exit_code == 0


def test_init_defaults_to_the_current_directory(target, monkeypatch):
    target.mkdir()
    monkeypatch.delenv("CSTUDY_WORKSPACE")
    monkeypatch.chdir(target)
    init()
    assert (target / ".cs" / "workspace.toml").is_file()


def test_init_defaults_to_the_workspace_flag(target):
    runner.invoke(cli.app, ["--workspace", str(target), "init"])
    assert (target / ".cs" / "workspace.toml").is_file()


def test_init_never_overwrites_an_existing_file(target):
    target.mkdir()
    (target / "README.md").write_text("my notes\n")
    init(str(target))
    assert (target / "README.md").read_text() == "my notes\n"


def test_init_reports_what_it_wrote_and_kept(target):
    target.mkdir()
    (target / "README.md").write_text("my notes\n")
    output = init(str(target)).output
    assert "1 kept" in output


def test_init_prints_the_next_steps(target):
    output = init(str(target)).output
    assert "cstudy doctor --fix" in output


def test_init_refuses_an_existing_workspace(target):
    mark_workspace(target)
    result = init(str(target))
    assert (result.exit_code, "already a workspace" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_init_refuses_a_directory_inside_a_workspace(target):
    mark_workspace(target)
    result = init(str(target / "python"))
    assert (result.exit_code, "inside the workspace" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_init_refuses_a_directory_inside_a_content_checkout(tmp_path):
    checkout = tmp_path / "coding-study"
    (checkout / "problems").mkdir(parents=True)
    (checkout / "schemas").mkdir()
    result = init(str(checkout / "ws"))
    assert (result.exit_code, "--force" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_init_inside_a_content_checkout_writes_nothing(tmp_path):
    checkout = tmp_path / "coding-study"
    (checkout / "problems").mkdir(parents=True)
    (checkout / "schemas").mkdir()
    init(str(checkout / "ws"))
    assert not (checkout / "ws").exists()


def test_init_refuses_this_repository(monkeypatch):
    monkeypatch.chdir(REPOSITORY_ROOT)
    assert init(str(REPOSITORY_ROOT / "ws")).exit_code == ExitCode.USAGE_ERROR


def test_force_creates_a_workspace_inside_a_content_checkout(tmp_path):
    checkout = tmp_path / "coding-study"
    (checkout / "problems").mkdir(parents=True)
    (checkout / "schemas").mkdir()
    result = init(str(checkout / "ws"), "--force")
    assert (result.exit_code, (checkout / "ws" / ".cs" / "workspace.toml").is_file()) == (0, True)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git on PATH")
def test_git_initializes_a_repository(target):
    init(str(target), "--git")
    assert (target / ".git").is_dir()


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git on PATH")
def test_git_commits_nothing(target):
    init(str(target), "--git")
    assert not (target / ".git" / "refs" / "heads" / "main").exists()


def test_without_git_there_is_no_repository(target):
    init(str(target))
    assert not (target / ".git").exists()


@pytest.mark.parametrize("relative", [VSCODE_TASKS, IDEA_MISC, ".cs/ide.json"])
def test_init_writes_the_ide_files_of_both_ides(target, relative):
    init(str(target))
    assert (target / relative).is_file()


def test_init_installs_the_intellij_launcher(target):
    init(str(target))
    assert (target / ".cs" / "runtime" / "ide" / "cstudy-launcher.jar").is_file()


def test_init_reports_the_ide_files(target):
    assert "ide      vscode, idea" in init(str(target)).output


@pytest.mark.parametrize("directory", [".vscode", ".idea"])
def test_no_ide_writes_no_ide_files(target, directory):
    init(str(target), "--no-ide")
    assert not (target / directory).exists()


def test_ide_writes_only_the_named_ides(target):
    init(str(target), "--ide", "idea")
    assert ((target / IDEA_MISC).is_file(), (target / ".vscode").exists()) == (True, False)


def test_ide_repeats(target):
    init(str(target), "--ide", "idea", "--ide", "vscode")
    assert ((target / IDEA_MISC).is_file(), (target / VSCODE_TASKS).is_file()) == (True, True)


def test_ide_and_no_ide_together_are_a_usage_error(target):
    result = init(str(target), "--ide", "idea", "--no-ide")
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_init_keeps_an_ide_file_of_your_own(target):
    (target / ".vscode").mkdir(parents=True)
    (target / ".vscode" / "settings.json").write_text("{}\n")
    init(str(target))
    assert (target / ".vscode" / "settings.json").read_text() == "{}\n"


def test_init_names_an_ide_file_it_kept(target):
    (target / ".vscode").mkdir(parents=True)
    (target / ".vscode" / "settings.json").write_text("{}\n")
    assert "kept .vscode/settings.json" in init(str(target)).output


def test_the_workspace_tracks_the_ide_manifest(target):
    init(str(target))
    assert "!/.cs/ide.json" in (target / ".gitignore").read_text().splitlines()
