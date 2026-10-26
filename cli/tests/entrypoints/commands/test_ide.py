"""`cstudy ide` (docs/specs/cli.md#cstudy-ide)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode

runner = CliRunner()
TASKS = ".vscode/tasks.json"
MISC = ".idea/misc.xml"
LAUNCHER = ".cs/runtime/ide/cstudy-launcher.jar"
MANIFEST = ".cs/ide.json"


def ide(workspace: Path, *arguments: str):
    return runner.invoke(cli.app, ["--workspace", str(workspace), "ide", *arguments])


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
