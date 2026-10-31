from importlib.metadata import version

import pytest
import typer
from typer.testing import CliRunner

from coding_study.adapters.locations import ContentRootError, WorkspaceError
from coding_study.domain.errors import (
    ConfigError,
    ContentError,
    ContentIssue,
    LanguageNotSetUpError,
    RunnerProtocolError,
    RunnerStartError,
    UnknownProblemError,
    UsageError,
    VersionControlError,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor
from coding_study.entrypoints.shared import ExitCode, add_command

runner = CliRunner()
PHASE_0_COMMANDS = ("doctor", "start", "test", "list", "show", "solution", "done", "verify")
PHASE_1_COMMANDS = ("next", "hint", "new")
PHASE_2_COMMANDS = ("bench",)
PHASE_7_COMMANDS = ("stats", "export", "import", "mock")
WORKSPACE_COMMANDS = ("init", "ide")
PHASE_8_COMMANDS = ("submit", "status")


def registered_commands() -> set[str | None]:
    return {command.name for command in cli.app.registered_commands}


def test_every_command_so_far_is_registered():
    assert registered_commands() == {
        *PHASE_0_COMMANDS,
        *PHASE_1_COMMANDS,
        *PHASE_2_COMMANDS,
        *PHASE_7_COMMANDS,
        *PHASE_8_COMMANDS,
        *WORKSPACE_COMMANDS,
    }


def test_version_prints_the_installed_package_version():
    result = runner.invoke(cli.app, ["--version"])
    assert (result.exit_code, result.stdout) == (0, f"cstudy {version('coding-study')}\n")


def test_version_needs_no_command():
    assert runner.invoke(cli.app, ["--version", "list"]).exit_code == 0


@pytest.mark.parametrize(
    "arguments",
    [["list", "--no-such-flag"], ["no-such-command"], ["list", "--track", "no-such-track"]],
    ids=["unknown flag", "unknown command", "invalid value"],
)
def test_usage_errors_exit_3(arguments):
    assert runner.invoke(cli.app, arguments).exit_code == ExitCode.USAGE_ERROR


def test_usage_errors_explain_themselves_on_stderr():
    assert (
        "No such option: --no-such-flag"
        in runner.invoke(cli.app, ["list", "--no-such-flag"]).stderr
    )


def test_ctrl_c_exits_130(monkeypatch):
    def interrupted(*_arguments: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(doctor, "run_doctor", interrupted)
    assert runner.invoke(cli.app, ["doctor"]).exit_code == ExitCode.INTERRUPTED


def test_known_error_messages_are_never_read_as_markup():
    result = runner.invoke(app_raising(UsageError("bad value [red]x[/red]")), [])
    assert result.stderr == "error: bad value [red]x[/red]\n"


def app_raising(error: Exception) -> typer.Typer:
    app = typer.Typer()

    def boom() -> None:
        raise error

    add_command(app, boom, "boom")
    return app


@pytest.mark.parametrize(
    ("error", "exit_code"),
    [
        (UnknownProblemError("three-sum"), ExitCode.USAGE_ERROR),
        (ContentError([ContentIssue("problems/x/meta.yaml", "id", "bad")]), ExitCode.CONTENT_ERROR),
        (ConfigError("config.toml", ["bad key"]), ExitCode.ENVIRONMENT_ERROR),
        (LanguageNotSetUpError("kotlin", "runner"), ExitCode.ENVIRONMENT_ERROR),
        (RunnerStartError("runner did not say hello"), ExitCode.ENVIRONMENT_ERROR),
        (RunnerProtocolError("bad event"), ExitCode.INTERNAL_ERROR),
        (UsageError("no attempt in progress"), ExitCode.USAGE_ERROR),
        (WorkspaceError("no coding-study workspace at /tmp"), ExitCode.USAGE_ERROR),
        (ContentRootError("CSTUDY_CONTENT=/tmp needs problems/"), ExitCode.USAGE_ERROR),
        (VersionControlError("git not found on PATH"), ExitCode.ENVIRONMENT_ERROR),
    ],
)
def test_known_errors_map_to_spec_exit_codes(error, exit_code):
    assert runner.invoke(app_raising(error), []).exit_code == exit_code


def test_known_errors_are_printed_to_stderr():
    result = runner.invoke(app_raising(UnknownProblemError("three-sum")), [])
    assert result.stderr == 'error: unknown problem "three-sum"\n'


def test_content_errors_print_every_issue():
    issues = [ContentIssue("a.yaml", "id", "bad"), ContentIssue("b.json", "", "file not found")]
    result = runner.invoke(app_raising(ContentError(issues)), [])
    assert result.stderr == "error: a.yaml: id: bad\nb.json: file not found\n"


def test_unknown_errors_are_not_swallowed():
    result = runner.invoke(app_raising(KeyError("bug")), [])
    assert isinstance(result.exception, KeyError)
