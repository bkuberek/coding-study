"""`cstudy abort` from the terminal (docs/specs/cli.md#cstudy-abort): the question, what it prints,
and its refusals, against a scratch workspace with an attempt in progress."""

from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import abort
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeClock, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUB = "python/practice/two_sum.py"
MINE = "def two_sum(): ...\n"


class Busy:
    def active_run(self) -> str | None:
        return "a run or a job is in progress (process 4242)"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    clock = FakeClock()
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        copy_repository(tmp_path, PRACTICE), toolchains=toolchains, clock=clock
    )
    monkeypatch.setattr(abort, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    environment.workspace.write_text(STUB, MINE)
    clock.advance(timedelta(minutes=18, seconds=40))
    return environment


def invoke(*arguments: str, typed: str | None = None):
    return runner.invoke(cli.app, ["abort", *arguments], input=typed)


def status_of_the_attempt(environment) -> AttemptStatus:
    attempt = environment.progress.latest_attempt("two-sum", Language.PYTHON)
    assert attempt is not None
    return attempt.status


def test_it_reports_the_attempt_the_files_that_stay_and_the_way_back(environment):
    assert invoke("--yes").output.splitlines() == [
        "two-sum · python · abandoned · 18m 40s",
        "kept    python/practice/two_sum.py",
        "next    cstudy start two-sum",
    ]


def test_yes_ends_the_attempt_without_asking(environment):
    result = invoke("two-sum", "--yes")
    assert (result.exit_code, status_of_the_attempt(environment)) == (
        ExitCode.SUCCESS,
        AttemptStatus.ABANDONED,
    )


def test_it_keeps_the_practice_file(environment):
    invoke("--yes")
    assert environment.workspace.read_text(STUB) == MINE


def test_without_a_slug_it_works_on_the_active_attempt(environment):
    invoke("--yes")
    assert environment.progress.active_attempt() is None


def test_a_solution_file_names_its_problem(environment):
    invoke(str(environment.root / STUB), "--yes")
    assert environment.progress.active_attempt() is None


def test_it_asks_first_and_a_yes_ends_the_attempt(environment):
    result = invoke(typed="y\n")
    assert ("Abort two-sum in python?" in result.output, status_of_the_attempt(environment)) == (
        True,
        AttemptStatus.ABANDONED,
    )


def test_the_question_says_what_stays(environment):
    question = invoke(typed="n\n").output
    assert "Your files stay; progress and the review schedule do not change." in question


def test_a_no_leaves_the_attempt_in_progress_and_says_so(environment):
    result = invoke(typed="n\n")
    assert (
        result.exit_code,
        "not aborted" in result.output,
        status_of_the_attempt(environment),
    ) == (
        ExitCode.SUCCESS,
        True,
        AttemptStatus.IN_PROGRESS,
    )


def test_an_empty_answer_is_a_no(environment):
    invoke(typed="\n")
    assert status_of_the_attempt(environment) is AttemptStatus.IN_PROGRESS


def test_no_attempt_in_progress_is_a_usage_error(environment):
    invoke("--yes")
    result = invoke("--yes")
    assert (result.exit_code, "no attempt in progress" in result.stderr) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_a_run_in_progress_refuses_and_says_so(environment, monkeypatch):
    monkeypatch.setattr(abort, "ProcessRunActivity", lambda root: Busy())
    result = invoke("--yes")
    assert (result.exit_code, "process 4242" in result.stderr) == (ExitCode.USAGE_ERROR, True)


def test_a_refused_abort_leaves_the_attempt_in_progress(environment, monkeypatch):
    monkeypatch.setattr(abort, "ProcessRunActivity", lambda root: Busy())
    invoke("--yes")
    assert status_of_the_attempt(environment) is AttemptStatus.IN_PROGRESS
