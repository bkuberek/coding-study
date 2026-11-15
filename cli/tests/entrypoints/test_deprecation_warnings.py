"""A deprecated flag, config key or environment variable still works and warns once on standard
error (docs/specs/compatibility.md#deprecation); the registry of this release is empty."""

import json
import re
from pathlib import Path
from typing import Annotated

import pytest
import typer
from typer.testing import CliRunner

from coding_study.adapters import deprecation_warnings, environment_factory
from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.toml_config import TomlConfigSource
from coding_study.domain.deprecations import DEPRECATIONS, DeprecatedSurface, Deprecation
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import deprecated_flag, merged
from tests.helpers import SCHEMAS_DIRECTORY, mark_workspace

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
"""Rich styles the help, its option names included, when the environment forces a terminal."""

runner = CliRunner()

OLD_FLAG = Deprecation(DeprecatedSurface.FLAG, "cstudy show --old-name", "0.60.0", "--new-name")
KEY = Deprecation(DeprecatedSurface.CONFIG_KEY, "next.tracks", "0.61.0", "tracks")
VARIABLE = Deprecation(DeprecatedSurface.ENV_VAR, "CSTUDY_OLD", "0.62.0", "CSTUDY_NEW")
OLD_FLAG_LINE = (
    "warning: cstudy show --old-name is deprecated since cstudy 0.60.0"
    " and is removed in 2.0; use --new-name"
)
VARIABLE_LINE = (
    "warning: CSTUDY_OLD is deprecated since cstudy 0.62.0 and is removed in 2.0; use CSTUDY_NEW"
)
KEY_LINE = (
    "warning: next.tracks is deprecated since cstudy 0.61.0 and is removed in 2.0; use tracks"
)


@pytest.fixture(autouse=True)
def fresh_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test is a process that has warned about nothing."""
    monkeypatch.setattr(deprecation_warnings, "_warned", set())


def _app() -> typer.Typer:
    app = typer.Typer()

    @app.command()
    def show(
        new_name: Annotated[str | None, typer.Option("--new-name")] = None,
        old_name: Annotated[str | None, deprecated_flag(OLD_FLAG)] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
        events: Annotated[bool, typer.Option("--events")] = False,
    ) -> None:
        name = merged(new_name, old_name)
        if as_json:
            typer.echo(json.dumps({"name": name}))
        elif events:
            for kind in ("run_start", "run_end"):
                typer.echo(json.dumps({"type": kind, "version": 1, "name": name}))
        else:
            typer.echo(f"name {name}")

    @app.command()
    def other() -> None:
        typer.echo("other")

    return app


def test_a_deprecated_flag_still_works_and_warns() -> None:
    result = runner.invoke(_app(), ["show", "--old-name", "ada"])

    assert (result.exit_code, result.stdout, result.stderr) == (
        0,
        "name ada\n",
        OLD_FLAG_LINE + "\n",
    )


def test_the_deprecated_value_merges_into_the_replacement() -> None:
    only_old = runner.invoke(_app(), ["show", "--old-name", "old"])
    both = runner.invoke(_app(), ["show", "--old-name", "old", "--new-name", "new"])

    assert (only_old.stdout, both.stdout) == ("name old\n", "name new\n")


def test_it_warns_once_per_process() -> None:
    first = runner.invoke(_app(), ["show", "--old-name", "a"])
    second = runner.invoke(_app(), ["show", "--old-name", "b"])

    assert (first.stderr.count("deprecated"), second.stderr, second.stdout) == (1, "", "name b\n")


def test_without_the_flag_nothing_warns() -> None:
    result = runner.invoke(_app(), ["show", "--new-name", "ada"])

    assert (result.stdout, result.stderr) == ("name ada\n", "")


def test_the_deprecated_flag_is_hidden_from_help() -> None:
    result = runner.invoke(_app(), ["show", "--help"])
    shown = ANSI_ESCAPE.sub("", result.stdout)

    assert ("--new-name" in shown, "--old-name" in shown) == (True, False)


def test_json_output_is_unchanged_and_the_warning_is_on_stderr() -> None:
    plain = runner.invoke(_app(), ["show", "--json", "--new-name", "ada"])
    deprecated = runner.invoke(_app(), ["show", "--json", "--old-name", "ada"])

    assert json.loads(deprecated.stdout) == json.loads(plain.stdout) == {"name": "ada"}
    assert deprecated.stdout == plain.stdout
    assert (plain.stderr, deprecated.stderr) == ("", OLD_FLAG_LINE + "\n")


def test_event_output_is_unchanged_and_the_warning_is_on_stderr() -> None:
    plain = runner.invoke(_app(), ["show", "--events", "--new-name", "ada"])
    deprecated = runner.invoke(_app(), ["show", "--events", "--old-name", "ada"])

    assert [json.loads(line)["type"] for line in deprecated.stdout.splitlines()] == [
        "run_start",
        "run_end",
    ]
    assert deprecated.stdout == plain.stdout
    assert (plain.stderr, deprecated.stderr) == ("", OLD_FLAG_LINE + "\n")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return mark_workspace(tmp_path / "workspace")


@pytest.fixture
def content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    (content / "problems").mkdir(parents=True)
    (content / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    return content


@pytest.fixture
def environ(content: Path, workspace: Path, tmp_path: Path) -> dict[str, str]:
    config = tmp_path / "config.toml"
    config.write_text("")
    return {
        "CSTUDY_CONTENT": str(content),
        "CSTUDY_WORKSPACE": str(workspace),
        "CSTUDY_CONFIG": str(config),
    }


def _load(environ: dict[str, str], tmp_path: Path) -> None:
    load_environment(tmp_path, environ, tmp_path)


def test_a_deprecated_environment_variable_warns(
    environ: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(environment_factory, "DEPRECATIONS", (VARIABLE,))

    _load({**environ, "CSTUDY_OLD": "1"}, tmp_path)
    _load({**environ, "CSTUDY_OLD": "1"}, tmp_path)

    assert capsys.readouterr().err == VARIABLE_LINE + "\n"


def test_an_unset_deprecated_variable_does_not_warn(
    environ: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(environment_factory, "DEPRECATIONS", (VARIABLE,))

    _load(environ, tmp_path)

    assert capsys.readouterr().err == ""


def test_a_deprecated_config_key_warns(
    environ: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    Path(environ["CSTUDY_CONFIG"]).write_text('[next]\ntracks = ["system-design"]\n')
    monkeypatch.setattr(environment_factory, "DEPRECATIONS", (KEY,))

    _load(environ, tmp_path)

    assert capsys.readouterr().err == KEY_LINE + "\n"


def test_a_deprecated_config_key_the_file_does_not_set_does_not_warn(
    environ: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    Path(environ["CSTUDY_CONFIG"]).write_text('default_lang = "go"\n')
    monkeypatch.setattr(environment_factory, "DEPRECATIONS", (KEY,))

    _load(environ, tmp_path)

    assert capsys.readouterr().err == ""


def test_the_config_source_reports_the_deprecated_keys_present(tmp_path: Path) -> None:
    top = Deprecation(DeprecatedSurface.CONFIG_KEY, "default_lang", "0.60.0")
    path = tmp_path / "config.toml"
    path.write_text('default_lang = "go"\n[next]\ntracks = []\n')

    source = TomlConfigSource(path)

    assert source.deprecated_keys((top, KEY, VARIABLE)) == (top, KEY)
    assert TomlConfigSource(tmp_path / "missing.toml").deprecated_keys((top,)) == ()
    path.write_text("not toml =")
    assert source.deprecated_keys((top,)) == ()


def test_the_registry_of_this_release_is_empty() -> None:
    assert DEPRECATIONS == ()


def test_the_empty_registry_prints_nothing(
    environ: dict[str, str], tmp_path: Path, content_root: Path, workspace: Path, capsys
) -> None:
    _load({**environ, "CSTUDY_OLD": "1"}, tmp_path)
    result = runner.invoke(
        cli.app,
        ["--workspace", str(workspace), "--content", str(content_root), "list", "--json"],
    )

    assert (result.exit_code, result.stderr, capsys.readouterr().err) == (0, "", "")
