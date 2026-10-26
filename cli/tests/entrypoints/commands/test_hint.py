from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import hint
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(copy_repository(tmp_path, PRACTICE), toolchains=toolchains)
    monkeypatch.setattr(hint, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["hint", *arguments])


def test_prints_the_next_hint(environment):
    assert invoke().output.splitlines() == [
        "two-sum · hint 1 of 2",
        "For each value, which partner would complete the sum?",
    ]


def test_prints_no_more_hints_once_exhausted(environment):
    invoke()
    invoke()
    assert invoke().output == "no more hints\n"


def test_exhausted_hints_still_exit_0(environment):
    invoke()
    invoke()
    assert invoke().exit_code == 0


def test_without_an_attempt_exits_3(environment):
    assert invoke("lru-cache").exit_code == ExitCode.USAGE_ERROR
