"""`cstudy abort` (docs/specs/cli.md#cstudy-abort): ends an attempt as abandoned, keeps the user's
files, and leaves progress and the review schedule as they are."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.abort_attempt import abort_attempt
from coding_study.application.ports import RunActivity
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus, Grade
from coding_study.domain.errors import WorkspaceBusyError
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from tests.fakes import NOW, FakeClock, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
STUB = "python/practice/two_sum.py"
MINE = "def two_sum(): ...\n"


class Idle:
    def active_run(self) -> str | None:
        return None


class Running:
    def active_run(self) -> str | None:
        return "a run or a job is in progress (process 4242)"


@pytest.fixture
def environment(tmp_path: Path):
    root = copy_repository(tmp_path, PRACTICE)
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    return make_environment(root, toolchains=toolchains, clock=FakeClock())


def start(environment, **fields) -> Attempt:
    return start_attempt(environment, StartRequest(**{"slug": "two-sum", **fields})).attempt


def abort(environment, attempt: Attempt, activity: RunActivity | None = None) -> Attempt:
    return abort_attempt(environment, attempt, activity or Idle())


def schedule(environment) -> ScheduleEntry:
    entry = ScheduleEntry(
        "two-sum", ReviewState(interval_days=3), date(2026, 10, 27), Grade.OK, NOW
    )
    environment.progress.save_schedule_entry(entry)
    return entry


def test_the_attempt_ends_as_abandoned(environment):
    ended = abort(environment, start(environment))
    assert environment.progress.attempt(ended.id).status is AttemptStatus.ABANDONED


def test_the_timer_stops_at_the_moment_of_the_abort(environment):
    attempt = start(environment)
    environment.clock.advance(timedelta(minutes=12))
    assert abort(environment, attempt).ended_at == NOW + timedelta(minutes=12)


def test_no_attempt_is_left_in_progress(environment):
    abort(environment, start(environment))
    assert environment.progress.attempts_in_progress() == ()


def test_the_practice_file_stays_as_the_user_left_it(environment):
    attempt = start(environment)
    environment.workspace.write_text(STUB, MINE)
    abort(environment, attempt)
    assert environment.workspace.read_text(STUB) == MINE


def test_the_review_schedule_is_left_untouched(environment):
    entry = schedule(environment)
    abort(environment, start(environment))
    assert environment.progress.schedule_entry("two-sum") == entry


def test_the_attempt_gets_no_grade_and_no_rating(environment):
    ended = abort(environment, start(environment))
    assert (ended.grade, ended.rating) == (None, None)


def test_the_abandoned_attempt_does_not_make_the_problem_attempted(environment):
    abort(environment, start(environment))
    statuses = environment.progress.problem_progress()["two-sum"].attempt_statuses
    assert statuses == {AttemptStatus.ABANDONED}


def test_a_run_in_progress_refuses_and_changes_nothing(environment):
    attempt = start(environment)
    with pytest.raises(WorkspaceBusyError, match="process 4242"):
        abort(environment, attempt, Running())
    assert environment.progress.attempt(attempt.id).status is AttemptStatus.IN_PROGRESS


def test_the_refusal_names_the_command(environment):
    with pytest.raises(WorkspaceBusyError, match="cstudy abort waits until it ends"):
        abort(environment, start(environment), Running())


def test_a_start_afterwards_begins_a_fresh_attempt(environment):
    aborted = abort(environment, start(environment))
    started = start_attempt(environment, StartRequest("two-sum"))
    assert (started.resumed, started.attempt.id != aborted.id) == (False, True)


def test_a_start_afterwards_goes_on_in_the_file_that_stayed(environment):
    attempt = start(environment)
    environment.workspace.write_text(STUB, MINE)
    abort(environment, attempt)
    started = start_attempt(environment, StartRequest("two-sum"))
    assert (environment.workspace.read_text(STUB), started.created_stub) == (MINE, False)


def test_a_start_afterwards_of_a_problem_with_a_review_archives_the_file_and_deletes_nothing(
    environment,
):
    schedule(environment)
    attempt = start(environment)
    environment.workspace.write_text(STUB, MINE)
    abort(environment, attempt)
    started = start_attempt(environment, StartRequest("two-sum"))
    archived = f".archive/two-sum/{attempt.id}-python/two_sum.py"
    assert (started.archived_to, environment.workspace.read_text(archived)) == (archived, MINE)


def test_a_start_with_fresh_afterwards_archives_the_file_and_deletes_nothing(environment):
    attempt = start(environment)
    environment.workspace.write_text(STUB, MINE)
    abort(environment, attempt)
    started = start_attempt(environment, StartRequest("two-sum", fresh=True))
    archived = f".archive/two-sum/{attempt.id}-python/two_sum.py"
    assert (started.archived_to, environment.workspace.read_text(archived)) == (archived, MINE)


def test_an_abandoned_attempt_keeps_its_mode(environment):
    assert abort(environment, start(environment)).mode is AttemptMode.NEW
