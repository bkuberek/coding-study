"""`cstudy config` (docs/specs/cli.md#cstudy-config): where the file is, and opening it."""

import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.toml_config import config_from_mapping
from coding_study.domain.config import Config
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode

runner = CliRunner()
KEPT = '# mine\ndefault_lang = "go"\n'


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "somewhere" / "config.toml"


def recording_editor(tmp_path: Path) -> tuple[str, Path]:
    """A `$VISUAL` that writes the path it was given to a file."""
    record = tmp_path / "opened"
    return f"sh -c 'printf %s \"$0\" > {record}'", record


def config(arguments: list[str], environ: dict[str, str]):
    return runner.invoke(cli.app, ["config", *arguments], env=environ)


def no_editor(path: Path) -> dict[str, str]:
    return {"CSTUDY_CONFIG": str(path), "VISUAL": "", "EDITOR": ""}


def test_config_path_prints_the_path_that_cstudy_config_names(path):
    result = config(["path"], {"CSTUDY_CONFIG": str(path)})
    assert (result.exit_code, result.stdout.strip()) == (ExitCode.SUCCESS, str(path))


def test_config_path_follows_the_xdg_config_home(tmp_path):
    result = config(["path"], {"CSTUDY_CONFIG": "", "XDG_CONFIG_HOME": str(tmp_path)})
    assert result.stdout.strip() == str(tmp_path / "coding-study" / "config.toml")


def test_config_path_needs_no_workspace(tmp_path, path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert config(["path"], {"CSTUDY_CONFIG": str(path)}).exit_code == ExitCode.SUCCESS


def test_config_path_creates_nothing(path):
    config(["path"], {"CSTUDY_CONFIG": str(path)})
    assert not path.exists()


def test_config_alone_shows_its_commands():
    result = config([], {})
    assert "edit" in result.output and "path" in result.output


def test_config_edit_opens_the_file_in_the_editor(tmp_path, path):
    editor, record = recording_editor(tmp_path)
    result = config(["edit"], {"CSTUDY_CONFIG": str(path), "VISUAL": editor})
    assert (result.exit_code, record.read_text()) == (ExitCode.SUCCESS, str(path))


def test_config_edit_creates_a_missing_file_from_the_commented_template(path):
    config(["edit"], no_editor(path))
    assert config_from_mapping(tomllib.loads(path.read_text()), "test") == Config()


def test_config_edit_says_it_created_the_file(path):
    assert "created" in config(["edit"], no_editor(path)).stdout


def test_config_edit_keeps_a_file_that_is_there(path):
    path.parent.mkdir(parents=True)
    path.write_text(KEPT)
    config(["edit"], no_editor(path))
    assert path.read_text() == KEPT


def test_with_no_editor_it_prints_the_path_and_says_so(path):
    result = config(["edit"], no_editor(path))
    assert (
        result.exit_code,
        str(path) in result.stdout,
        "$VISUAL or $EDITOR" in result.stdout,
    ) == (
        ExitCode.SUCCESS,
        True,
        True,
    )


def test_an_editor_that_does_not_run_is_said(path):
    result = config(["edit"], {"CSTUDY_CONFIG": str(path), "VISUAL": "/no/such/editor"})
    assert "cannot run $VISUAL" in result.stdout
