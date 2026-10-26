"""`cstudy solution --broken[=ID]` (docs/specs/cli.md#cstudy-solution)."""

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import solution
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment, repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

runner = CliRunner()


@pytest.fixture(autouse=True)
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, CONCURRENCY_PROBLEMS))
    monkeypatch.setattr(solution, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["--no-color", "solution", *arguments])


def test_a_bare_broken_shows_the_first_broken_reference():
    output = invoke("bounded-blocking-queue", "--broken", "--lang", "python").output
    assert "broken reference no-lock" in output


def test_broken_with_an_id_shows_that_one():
    output = invoke("--broken=if-not-while", "bounded-blocking-queue", "--lang", "java").output
    assert "if (items.isEmpty())" in output


def test_the_broken_section_follows_the_code():
    output = invoke("bounded-blocking-queue", "--broken=if-not-while", "--lang", "python").output
    assert output.index("notify_all") < output.index("Failing interleaving")


def test_an_unknown_broken_id_exits_3():
    result = invoke("bounded-blocking-queue", "--broken=deadlock")
    assert result.exit_code == ExitCode.USAGE_ERROR
