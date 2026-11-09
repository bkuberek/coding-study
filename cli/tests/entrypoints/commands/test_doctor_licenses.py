"""`cstudy doctor --fix` and the license of a server (docs/specs/cli.md#cstudy-doctor, ADR 0018,
Kotlin revisited): it never accepts one for you. `--accept-license <key>` accepts it; otherwise,
at a terminal, `--fix` shows the license's name and link and asks, and elsewhere, as in the Health
view's Fix, it declines."""

import re
from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from coding_study.application.doctor import DoctorReport
from coding_study.application.ports import ScaffoldOutcome
from coding_study.domain.code_intelligence import (
    KOTLIN_LSP,
    KOTLIN_LSP_LICENSE,
    LanguageServer,
    License,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import doctor
from coding_study.entrypoints.shared import ExitCode
from tests.helpers import mark_workspace

runner = CliRunner()
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
"""Rich styles the help, its option names included, when the environment forces a terminal."""
LICENSE = "JetBrains Free Plugin License Agreement 1.0"
LICENSE_URL = "https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt"


class Answers:
    """What the consent `--fix` was given said for the Kotlin LSP."""

    def __init__(self) -> None:
        self.answers: list[bool] = []


@pytest.fixture
def answers(monkeypatch, tmp_path) -> Answers:
    """A workspace whose fix asks the consent it was given about the Kotlin LSP."""
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(mark_workspace(tmp_path)))
    found = Answers()

    def fix(
        _workspace, _content, _jdk, _notify, consent: Callable[[LanguageServer, License], bool]
    ):
        found.answers.append(consent(KOTLIN_LSP, KOTLIN_LSP_LICENSE))
        return ()

    monkeypatch.setattr(doctor, "fix_workspace", fix)
    monkeypatch.setattr(doctor, "repair_workspace", lambda *_: ScaffoldOutcome((), ()))
    monkeypatch.setattr(doctor, "run_doctor", lambda _environment, _notify: DoctorReport(()))
    return found


def at_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_is_interactive", lambda: True)


def test_the_flag_accepts_the_license_without_asking(answers):
    result = runner.invoke(cli.app, ["doctor", "--fix", "--accept-license", "kotlin-lsp"])
    assert (answers.answers, "Accept" in result.output) == ([True], False)


def test_without_the_flag_and_without_a_terminal_it_declines(answers):
    runner.invoke(cli.app, ["doctor", "--fix"], input="y\n")
    assert answers.answers == [False]


def test_at_a_terminal_it_asks_and_accepts_what_you_accept(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    runner.invoke(cli.app, ["doctor", "--fix"], input="y\n")
    assert answers.answers == [True]


def test_at_a_terminal_it_declines_what_you_decline(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    runner.invoke(cli.app, ["doctor", "--fix"], input="n\n")
    assert answers.answers == [False]


def test_at_a_terminal_it_declines_unless_you_say_yes(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    runner.invoke(cli.app, ["doctor", "--fix"], input="\n")
    assert answers.answers == [False]


def test_at_a_terminal_the_end_of_input_declines_and_the_fix_goes_on(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    result = runner.invoke(cli.app, ["doctor", "--fix"], input="")
    assert (answers.answers, result.exit_code) == ([False], 0)


def test_the_question_names_the_server_the_license_and_its_link(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    output = runner.invoke(cli.app, ["doctor", "--fix"], input="n\n").output
    assert all(part in output for part in ("kotlin-lsp", LICENSE, LICENSE_URL))


def test_the_question_says_the_server_is_partly_closed_source(answers, monkeypatch):
    at_a_terminal(monkeypatch)
    output = runner.invoke(cli.app, ["doctor", "--fix"], input="n\n").output
    assert "partly closed source" in output


def test_an_unknown_license_is_a_usage_error_naming_the_known_ones(answers):
    result = runner.invoke(cli.app, ["doctor", "--fix", "--accept-license", "jdtls"])
    assert (result.exit_code, "kotlin-lsp" in result.output) == (ExitCode.USAGE_ERROR, True)


def test_accepting_a_license_without_fix_is_a_usage_error(answers):
    result = runner.invoke(cli.app, ["doctor", "--accept-license", "kotlin-lsp"])
    assert (result.exit_code, answers.answers) == (ExitCode.USAGE_ERROR, [])


def test_the_help_names_the_option():
    output = runner.invoke(cli.app, ["doctor", "--help"]).output
    assert "--accept-license" in ANSI_ESCAPE.sub("", output)
