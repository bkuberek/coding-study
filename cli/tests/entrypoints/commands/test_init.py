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
    assert "ide        vscode, idea" in init(str(target)).output


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


LANGUAGE_FOLDERS = ("python", "typescript", "jvm", "go", "rust")
UNKNOWN = 'unknown language "golang"; use python, typescript, java, kotlin, go or rust'


def folders(root: Path) -> list[str]:
    return [name for name in (*LANGUAGE_FOLDERS, "go.work") if (root / name).exists()]


def test_without_lang_the_marker_lists_no_languages(target):
    init(str(target))
    assert "languages" not in tomllib.loads((target / ".cs" / "workspace.toml").read_text())


def test_without_lang_every_language_folder_exists(target):
    init(str(target))
    assert folders(target) == [*LANGUAGE_FOLDERS, "go.work"]


def test_without_lang_the_output_says_all_six(target):
    assert "languages  all six" in init(str(target)).output


def test_lang_writes_that_languages_folder_and_the_shared_files_only(target):
    init(str(target), "--lang", "python")
    assert (folders(target), (target / "notes").is_dir(), (target / "README.md").is_file()) == (
        ["python"],
        True,
        True,
    )


def test_lang_records_the_languages_in_the_marker(target):
    init(str(target), "--lang", "python")
    marker = tomllib.loads((target / ".cs" / "workspace.toml").read_text())
    assert marker["languages"] == ["python"]


def test_lang_repeats_and_keeps_workspace_order_each_once(target):
    init(str(target), "--lang", "rust", "--lang", "go", "--lang", "python", "--lang", "go")
    marker = tomllib.loads((target / ".cs" / "workspace.toml").read_text())
    assert (marker["languages"], folders(target)) == (
        ["python", "go", "rust"],
        ["python", "go", "rust", "go.work"],
    )


@pytest.mark.parametrize("language", ["java", "kotlin"])
def test_either_jvm_language_writes_the_whole_jvm_folder(target, language):
    init(str(target), "--lang", language)
    assert ((target / "jvm" / "java").is_dir(), (target / "jvm" / "kotlin").is_dir()) == (
        True,
        True,
    )


def test_go_writes_go_work(target):
    init(str(target), "--lang", "go")
    assert folders(target) == ["go", "go.work"]


def test_the_output_names_the_chosen_languages(target):
    assert "languages  python, go" in init(str(target), "--lang", "go", "--lang", "python").output


def test_an_unknown_language_exits_3_with_the_spec_text(target):
    result = init(str(target), "--lang", "golang")
    assert (result.exit_code, UNKNOWN in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_an_unknown_language_writes_nothing(target):
    init(str(target), "--lang", "python", "--lang", "golang")
    assert not target.exists()


def test_a_chosen_workspace_is_a_workspace(target):
    init(str(target), "--lang", "go")
    assert runner.invoke(cli.app, ["--workspace", str(target), "stats"]).exit_code == 0


def test_the_start_line_names_lang_when_the_default_language_is_not_chosen(target):
    output = init(str(target), "--lang", "go", "--lang", "rust").output
    assert "cstudy start two-sum --lang go " in output


def test_the_start_line_keeps_the_default_language_when_it_is_chosen(target):
    output = init(str(target), "--lang", "rust", "--lang", "python").output
    assert "cstudy start two-sum     # your first problem" in output


def test_the_start_line_follows_the_configured_default_language(target, tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('default_lang = "rust"\n')
    monkeypatch.setenv("CSTUDY_CONFIG", str(config))
    output = init(str(target), "--lang", "rust", "--lang", "go").output
    assert "cstudy start two-sum     # your first problem" in output


def test_a_directory_with_files_keeps_them_when_it_chooses_languages(target):
    target.mkdir()
    (target / "README.md").write_text("my notes\n")
    init(str(target), "--lang", "python")
    assert (target / "README.md").read_text() == "my notes\n"
