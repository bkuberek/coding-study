"""`cstudy ide` (docs/specs/cli.md#cstudy-ide)."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import selecting_jdk

runner = CliRunner()
TASKS = ".vscode/tasks.json"
MISC = ".idea/misc.xml"
LAUNCHER = ".cs/runtime/ide/cstudy-launcher.jar"
MANIFEST = ".cs/ide.json"


def ide(workspace: Path, *arguments: str, env: dict[str, str] | None = None):
    return runner.invoke(cli.app, ["--workspace", str(workspace), "ide", *arguments], env=env)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    target = tmp_path / "ws"
    result = runner.invoke(cli.app, ["init", str(target), "--no-ide"])
    assert result.exit_code == 0
    return target


def test_ide_exits_0(workspace):
    assert ide(workspace).exit_code == 0


@pytest.mark.parametrize("relative", [TASKS, MISC, MANIFEST])
def test_ide_writes_the_files_of_both_ides_and_the_manifest(workspace, relative):
    ide(workspace)
    assert (workspace / relative).is_file()


def test_ide_reports_what_it_wrote(workspace):
    assert "created" in ide(workspace).output


def test_a_second_run_reports_no_changes(workspace):
    ide(workspace)
    assert "no changes" in ide(workspace).output


def test_a_second_run_rewrites_nothing(workspace):
    ide(workspace)
    before = {path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    ide(workspace)
    after = {path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    assert after == before


def test_only_the_named_ide_is_generated(workspace):
    ide(workspace, "vscode")
    assert ((workspace / TASKS).is_file(), (workspace / ".idea").exists()) == (True, False)


def test_an_edited_file_is_kept(workspace):
    ide(workspace)
    (workspace / TASKS).write_text("{}\n")
    ide(workspace)
    assert (workspace / TASKS).read_text() == "{}\n"


def test_a_kept_file_is_named_with_the_way_to_overwrite_it(workspace):
    ide(workspace)
    (workspace / TASKS).write_text("{}\n")
    assert f"kept {TASKS}: edited, or not written by cstudy (cstudy ide --force" in (
        ide(workspace).output
    )


def test_force_overwrites_an_edited_file(workspace):
    ide(workspace)
    (workspace / TASKS).write_text("{}\n")
    ide(workspace, "--force")
    assert (workspace / TASKS).read_text() != "{}\n"


def test_a_run_configuration_of_your_own_is_never_touched(workspace):
    own = workspace / ".idea" / "runConfigurations" / "Mine.xml"
    own.parent.mkdir(parents=True)
    own.write_text("<component />\n")
    ide(workspace, "--force")
    assert own.read_text() == "<component />\n"


def test_ide_restores_the_launcher(workspace):
    (workspace / LAUNCHER).unlink()
    ide(workspace)
    assert (workspace / LAUNCHER).is_file()


def test_outside_a_workspace_it_exits_3(tmp_path):
    assert ide(tmp_path).exit_code == ExitCode.USAGE_ERROR


def test_an_unknown_ide_is_a_usage_error(workspace):
    assert ide(workspace, "emacs").exit_code == ExitCode.USAGE_ERROR


# the project JDK follows the JDK the shell selects

NO_JAVA = {"JAVA_HOME": "/nonexistent/jdk", "PATH": "/nonexistent/bin"}


def project_jdk(workspace: Path) -> tuple[str | None, str | None]:
    """The name and the language level `.idea/misc.xml` gives the project."""
    text = (workspace / MISC).read_text()
    name = re.search(r'project-jdk-name="([^"]*)"', text)
    level = re.search(r'languageLevel="([^"]*)"', text)
    return (name and name.group(1), level and level.group(1))


def test_the_project_jdk_is_named_after_the_selected_jdk(workspace, tmp_path):
    ide(workspace, "idea", env=selecting_jdk(tmp_path, 24))
    assert project_jdk(workspace) == ("24", "JDK_24")


def test_a_jdk_above_the_range_keeps_the_language_level_at_the_top_of_it(workspace, tmp_path):
    ide(workspace, "idea", env=selecting_jdk(tmp_path, 27))
    assert project_jdk(workspace) == ("27", "JDK_26")


def test_without_a_jdk_the_project_jdk_is_the_recommended_one(workspace):
    ide(workspace, "idea", env=NO_JAVA)
    assert project_jdk(workspace) == ("25", "JDK_25")


def test_a_switch_of_jdk_updates_the_file_while_it_is_as_cstudy_wrote_it(workspace, tmp_path):
    ide(workspace, "idea", env=selecting_jdk(tmp_path / "a", 24))
    result = ide(workspace, "idea", env=selecting_jdk(tmp_path / "b", 26))
    assert (project_jdk(workspace), "1 updated" in result.output) == (("26", "JDK_26"), True)


def test_a_switch_of_jdk_keeps_the_file_once_it_was_edited(workspace, tmp_path):
    ide(workspace, "idea", env=selecting_jdk(tmp_path / "a", 24))
    edited = (
        (workspace / MISC).read_text().replace('project-jdk-name="24"', 'project-jdk-name="mine"')
    )
    (workspace / MISC).write_text(edited)
    result = ide(workspace, "idea", env=selecting_jdk(tmp_path / "b", 26))
    assert ((workspace / MISC).read_text() == edited, f"kept {MISC}" in result.output) == (
        True,
        True,
    )
