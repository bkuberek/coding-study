"""`cstudy done` output for a project attempt (docs/specs/cli.md#cstudy-done)."""

from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.judging import Tally
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import done as done_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, FakeClock
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

runner = CliRunner()
PASSED_1 = LevelTally(1, 1, 1, 2, 2)
PASSED_2 = LevelTally(2, 1, 1, 2, 2)
FAILED_2 = LevelTally(2, 1, 0, 2, 2)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    clock = FakeClock()
    environment = project_environment(tmp_path, ScriptedProjectProcess(), clock=clock)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(done_command, "load_environment", lambda *_: environment)
    clock.advance(timedelta(minutes=84, seconds=10))
    return environment


def submit(environment, *levels: LevelTally) -> None:
    environment.progress.add_submission(
        SubmissionRecord(
            attempt_id=environment.progress.active_attempt().id,
            submitted_at=NOW,
            code_hash="abc",
            graded_up_to=len(levels),
            every_level=True,
            levels=levels,
            tally=Tally(total=sum(level.total for level in levels)),
            duration_ms=300,
        )
    )


def cs_done(*arguments: str):
    return runner.invoke(cli.app, ["done", *arguments])


def test_a_capped_grade_says_so(environment):
    submit(environment, PASSED_1, FAILED_2)
    assert cs_done("--rating", "ok").output.splitlines()[0] == (
        f"{PROJECT_SLUG} · python · failed · levels 1 of 2 · 1h 24m · "
        "rating ok, capped at hard · hints 0"
    )


def test_every_level_finished_is_not_capped(environment):
    submit(environment, PASSED_1, PASSED_2)
    assert cs_done("--rating", "ok").output.splitlines()[0] == (
        f"{PROJECT_SLUG} · python · passed · levels 2 of 2 · 1h 24m · rating ok · hints 0"
    )


def test_giving_up_without_a_submission_names_no_cap(environment):
    assert cs_done("--gave-up").output.splitlines()[0] == (
        f"{PROJECT_SLUG} · python · failed · levels 0 of 2 · 1h 24m · gave up · hints 0"
    )


def test_a_rating_before_level_1_passes_exits_3(environment):
    result = cs_done("--rating", "ok")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: no submission of every unlocked level passed level 1 yet; run cstudy submit, "
        "or finish with --gave-up\n",
    )
