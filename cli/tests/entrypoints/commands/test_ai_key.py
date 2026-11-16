"""`cstudy ai key` (docs/specs/cli.md#cstudy-ai-key): a key from standard input, into
`credentials.toml`, never in any output."""

import os
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import mark_workspace

runner = CliRunner()
SECRET = "sk-sentinel-0123456789"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "home"
    (directory / "work").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(directory))
    monkeypatch.chdir(directory / "work")
    return directory


@pytest.fixture
def config(home: Path) -> Path:
    return home / ".config" / "coding-study" / "credentials.toml"


def ai_key(arguments: list[str], key: str | None = None, **environ: str):
    return runner.invoke(
        cli.app,
        ["ai", "key", *arguments],
        input=key,
        env={"CSTUDY_CONFIG": "", "XDG_CONFIG_HOME": "", "CSTUDY_WORKSPACE": "", **environ},
    )


def shown(result) -> str:
    return result.stdout + result.stderr


def test_ai_alone_shows_its_commands():
    result = runner.invoke(cli.app, ["ai"])
    assert "key" in result.output


def test_a_key_from_standard_input_is_saved_beside_the_config(config):
    result = ai_key(["anthropic"], f"{SECRET}\n")
    assert (result.exit_code, result.stdout) == (
        ExitCode.SUCCESS,
        "anthropic key saved in ~/.config/coding-study/credentials.toml\n",
    )
    assert f'api_key = "{SECRET}"' in config.read_text(encoding="utf-8")


def test_the_file_is_private(config):
    ai_key(["openai"], f"{SECRET}\n")
    assert (stat.S_IMODE(config.stat().st_mode), stat.S_IMODE(config.parent.stat().st_mode)) == (
        0o600,
        0o700,
    )


def test_the_key_is_in_no_output(config):
    result = ai_key(["anthropic"], f"{SECRET}\n")
    assert SECRET not in shown(result)


def test_a_key_without_a_line_ending_is_read(config):
    assert ai_key(["google"], SECRET).exit_code == ExitCode.SUCCESS


def test_the_file_is_where_cstudy_config_says(tmp_path):
    target = tmp_path / "settings" / "config.toml"
    result = ai_key(["openrouter"], f"{SECRET}\n", CSTUDY_CONFIG=str(target))
    assert (result.exit_code, (target.parent / "credentials.toml").is_file()) == (0, True)


def test_a_key_is_set_without_a_workspace_and_with_ai_off(config):
    assert ai_key(["anthropic"], f"{SECRET}\n").exit_code == ExitCode.SUCCESS


@pytest.mark.parametrize(
    "key", ["", "\n", "two words\n", "tab\there\n"], ids=["none", "empty line", "space", "tab"]
)
def test_an_empty_key_or_one_with_spaces_exits_3_and_writes_nothing(config, key):
    result = ai_key(["anthropic"], key)
    assert (result.exit_code, config.exists()) == (ExitCode.USAGE_ERROR, False)
    assert "a key is one line of text with no spaces" in result.stderr


def test_a_refused_key_is_not_quoted(config):
    result = ai_key(["anthropic"], f"{SECRET} extra\n")
    assert SECRET not in shown(result)


def test_an_unknown_provider_exits_3_before_asking_for_a_key(config):
    result = ai_key(["antropic"], f"{SECRET}\n")
    assert (result.exit_code, config.exists()) == (ExitCode.USAGE_ERROR, False)
    assert result.stderr == (
        "error: unknown provider; use one of anthropic, google, openai, openrouter\n"
    )


def test_a_key_given_in_place_of_the_provider_is_not_echoed(config):
    result = ai_key([SECRET])
    assert (result.exit_code, config.exists()) == (ExitCode.USAGE_ERROR, False)
    assert SECRET not in shown(result)


def test_a_key_is_never_taken_as_an_argument(config):
    result = ai_key(["anthropic", SECRET])
    assert (result.exit_code, config.exists()) == (ExitCode.USAGE_ERROR, False)
    assert SECRET not in shown(result)
    assert "takes the provider only" in shown(result)


def test_remove_deletes_the_provider_key_and_keeps_the_others(config):
    ai_key(["anthropic"], f"{SECRET}\n")
    ai_key(["openai"], "other-key\n")
    result = ai_key(["anthropic", "--remove"])
    assert (result.exit_code, result.stdout) == (ExitCode.SUCCESS, "anthropic key removed\n")
    assert "[openai]" in config.read_text(encoding="utf-8")
    assert "[anthropic]" not in config.read_text(encoding="utf-8")


def test_the_file_goes_with_its_last_key(config):
    ai_key(["anthropic"], f"{SECRET}\n")
    ai_key(["anthropic", "--remove"])
    assert config.exists() is False


def test_removing_a_key_that_is_not_there_says_so(config):
    result = ai_key(["google", "--remove"])
    assert (result.exit_code, result.stdout) == (ExitCode.SUCCESS, "google has no key\n")


def test_a_file_that_does_not_load_exits_4_and_stays_as_it_was(config):
    config.parent.mkdir(parents=True)
    broken = f'[antropic]\napi_key = "{SECRET}"\n'
    config.write_text(broken, encoding="utf-8")
    result = ai_key(["anthropic"], f"{SECRET}\n")
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert result.stderr == f'error: {config}: unknown provider "antropic"\n'
    assert config.read_text(encoding="utf-8") == broken


def test_remove_exits_4_for_a_file_that_does_not_load(config):
    config.parent.mkdir(parents=True)
    config.write_text("[anthropic\n", encoding="utf-8")
    assert ai_key(["anthropic", "--remove"]).exit_code == ExitCode.ENVIRONMENT_ERROR


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes anywhere")
def test_a_file_that_cannot_be_written_exits_4(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)
    result = ai_key(["anthropic"], f"{SECRET}\n", CSTUDY_CONFIG=str(locked / "sub" / "config.toml"))
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR
    assert SECRET not in shown(result)


def test_a_file_that_would_be_inside_the_workspace_exits_3_and_writes_nothing(tmp_path, home):
    workspace = mark_workspace(tmp_path / "workspace")
    inside = workspace / "config.toml"
    result = ai_key(
        ["anthropic"], f"{SECRET}\n", CSTUDY_CONFIG=str(inside), CSTUDY_WORKSPACE=str(workspace)
    )
    assert (result.exit_code, (workspace / "credentials.toml").exists()) == (
        ExitCode.USAGE_ERROR,
        False,
    )
    assert "would be inside this workspace" in result.stderr
    assert SECRET not in shown(result)


def test_remove_refuses_a_file_inside_the_workspace_too(tmp_path, home):
    workspace = mark_workspace(tmp_path / "workspace")
    result = ai_key(
        ["anthropic", "--remove"],
        CSTUDY_CONFIG=str(workspace / "config.toml"),
        CSTUDY_WORKSPACE=str(workspace),
    )
    assert result.exit_code == ExitCode.USAGE_ERROR
