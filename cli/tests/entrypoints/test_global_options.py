"""The global `--workspace` and `--content` flags (docs/specs/installation-and-workspaces.md)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode, GlobalOptions
from tests.helpers import mark_workspace

runner = CliRunner()


def test_the_workspace_flag_overrides_cs_workspace():
    options = GlobalOptions(workspace=Path("/flag"))
    assert options.environ({"CSTUDY_WORKSPACE": "/variable"})["CSTUDY_WORKSPACE"] == "/flag"


def test_the_content_flag_becomes_cs_content():
    assert GlobalOptions(content=Path("/checkout")).environ({})["CSTUDY_CONTENT"] == "/checkout"


def test_without_flags_the_environment_is_unchanged():
    assert GlobalOptions().environ({"CSTUDY_WORKSPACE": "/variable"}) == {
        "CSTUDY_WORKSPACE": "/variable"
    }


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return mark_workspace(tmp_path / "ws")


def test_a_command_runs_in_the_workspace_the_flag_names(workspace, content_root, monkeypatch):
    monkeypatch.setenv("CSTUDY_CONTENT", str(content_root))
    result = runner.invoke(cli.app, ["--workspace", str(workspace), "list"])
    assert "two-sum" in result.output


def test_a_command_that_needs_a_workspace_exits_3_without_one(tmp_path, content_root, monkeypatch):
    monkeypatch.setenv("CSTUDY_CONTENT", str(content_root))
    result = runner.invoke(cli.app, ["--workspace", str(tmp_path), "next"])
    assert (result.exit_code, "run cstudy init" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_cs_list_reads_the_catalog_outside_a_workspace(tmp_path, content_root, monkeypatch):
    monkeypatch.setenv("CSTUDY_CONTENT", str(content_root))
    result = runner.invoke(cli.app, ["--workspace", str(tmp_path), "list"])
    assert "lru-cache" in result.output


def test_cs_list_outside_a_workspace_writes_nothing_there(tmp_path, content_root, monkeypatch):
    monkeypatch.setenv("CSTUDY_CONTENT", str(content_root))
    outside = tmp_path / "outside"
    outside.mkdir()
    runner.invoke(cli.app, ["--workspace", str(outside), "list"])
    assert list(outside.iterdir()) == []


def test_the_content_flag_must_name_a_content_root(tmp_path, workspace):
    result = runner.invoke(
        cli.app, ["--content", str(tmp_path), "--workspace", str(workspace), "list"]
    )
    assert (result.exit_code, "needs problems/ and schemas/" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )
