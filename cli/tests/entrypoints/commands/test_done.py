from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import RunRecord
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import done
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, FakeClock, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    clock = FakeClock()
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        copy_repository(tmp_path, PRACTICE), toolchains=toolchains, clock=clock
    )
    monkeypatch.setattr(done, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    clock.advance(timedelta(minutes=18, seconds=40))
    return environment


def passed_every_case(environment) -> None:
    attempt = environment.progress.active_attempt()
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", Tally(4, 4), 10))
    environment.progress.update_attempt(replace(attempt, first_pass_at=NOW))


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["done", *arguments])


def test_rating_a_passed_attempt(environment):
    passed_every_case(environment)
    assert invoke("--rating", "ok").output.splitlines() == [
        "two-sum · python · passed · 18m 40s · rating ok · hints 0",
        "next review  2026-10-27 (in 3 days) · ease 2.50",
    ]


def test_giving_up(environment):
    assert invoke("--gave-up").output.splitlines() == [
        "two-sum · python · failed · 18m 40s · gave up · hints 0",
        "next review  2026-10-25 (in 1 day) · ease 2.30",
    ]


def test_notes_are_stored(environment):
    passed_every_case(environment)
    invoke("--rating", "easy", "--notes", "one pass")
    attempt = environment.progress.latest_attempt("two-sum", Language.PYTHON)
    assert attempt is not None
    assert attempt.notes == "one pass"


def test_rating_without_a_full_pass_is_a_usage_error(environment):
    result = invoke("--rating", "ok")
    assert (result.exit_code, "--gave-up" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_neither_rating_nor_gave_up_is_a_usage_error(environment):
    assert invoke().exit_code == ExitCode.USAGE_ERROR


def test_explicit_slug(environment):
    assert invoke("two-sum", "--gave-up").exit_code == 0


def test_a_solution_file_path_selects_its_problem(environment):
    path = environment.root / "python/practice/lru_cache.py"
    result = invoke(str(path), "--gave-up")
    assert (result.exit_code, "no attempt in progress for lru-cache" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )
