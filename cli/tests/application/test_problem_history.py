"""`cstudy history`: a problem's schedule and its attempts with their runs
(docs/specs/cli.md#cstudy-history)."""

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from coding_study.application.environment import Environment
from coding_study.application.problem_history import problem_history
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt, RunRecord
from coding_study.domain.bench_records import BenchRunRecord, BenchRunSummary
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.errors import UnknownProblemError
from coding_study.domain.items import EntryKind
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemStatus, ReviewState, ScheduleEntry
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
LATER = NOW + timedelta(days=1)


@pytest.fixture
def environment(tmp_path) -> Environment:
    return make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))


def start(environment: Environment, language: Language, at=NOW) -> int:
    attempt = NewAttempt("two-sum", language, AttemptMode.NEW, at)
    return environment.progress.add_attempt(attempt).id


def test_an_unknown_slug_is_an_error(environment):
    with pytest.raises(UnknownProblemError):
        problem_history(environment, "three-sum")


def test_a_problem_names_its_kind_track_and_difficulty(environment):
    found = problem_history(environment, "two-sum")
    assert (found.kind, found.track, found.difficulty, found.patterns) == (
        EntryKind.FUNCTION,
        Track.DSA,
        Difficulty.EASY,
        ("arrays-hashing",),
    )


def test_an_item_is_of_the_item_kind_on_its_track(environment):
    found = problem_history(environment, "url-shortener")
    assert (found.kind, found.track, found.patterns) == (EntryKind.ITEM, Track.SYSTEM_DESIGN, ())


def test_an_untouched_problem_is_new_without_schedule_or_attempts(environment):
    found = problem_history(environment, "two-sum")
    assert (found.status, found.schedule, found.attempts) == (ProblemStatus.NEW, None, ())


def test_the_status_comes_from_progress(environment):
    start(environment, Language.PYTHON)
    attempt = environment.progress.active_attempt("two-sum")
    environment.progress.update_attempt(replace(attempt, status=AttemptStatus.PASSED))
    assert problem_history(environment, "two-sum").status is ProblemStatus.PASSED


def test_the_schedule_is_the_problems_review_row(environment):
    entry = ScheduleEntry(
        "two-sum", ReviewState(interval_days=7, reps=2), date(2026, 10, 31), Grade.OK, NOW
    )
    environment.progress.save_schedule_entry(entry)
    assert problem_history(environment, "two-sum").schedule == entry


def test_the_history_is_of_today(environment):
    assert problem_history(environment, "two-sum").today == NOW.date()


def test_attempts_come_in_every_language_newest_first(environment):
    python = start(environment, Language.PYTHON)
    kotlin = start(environment, Language.KOTLIN, LATER)
    found = problem_history(environment, "two-sum").attempts
    assert [past.attempt.id for past in found] == [kotlin, python]


def test_an_attempt_lists_its_test_runs_earliest_first(environment):
    attempt_id = start(environment, Language.PYTHON)
    first = RunRecord(attempt_id, NOW, "a", Tally(total=4, passed=3, failed=1), 10)
    second = RunRecord(attempt_id, LATER, "b", Tally(total=4, passed=4), 12)
    environment.progress.add_test_run(first)
    environment.progress.add_test_run(second)
    assert problem_history(environment, "two-sum").attempts[0].test_runs == (first, second)


def test_an_attempt_lists_its_bench_runs(environment):
    attempt_id = start(environment, Language.PYTHON)
    run = BenchRunRecord(
        attempt_id,
        "two-sum",
        Language.PYTHON,
        NOW,
        "a",
        (100,),
        (),
        Verdict.OPTIMAL,
        Confidence.LOW,
    )
    environment.progress.add_bench_run(run)
    assert problem_history(environment, "two-sum").attempts[0].bench_runs == (
        BenchRunSummary(NOW, Verdict.OPTIMAL, Confidence.LOW, None, None),
    )


def test_a_single_file_attempt_has_no_submissions_or_levels_finished(environment):
    start(environment, Language.PYTHON)
    past = problem_history(environment, "two-sum").attempts[0]
    assert (past.submissions, past.levels_finished) == ((), None)


# project problems


@pytest.fixture
def project(tmp_path) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def submit(environment: Environment, *levels: LevelTally) -> SubmissionRecord:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    record = SubmissionRecord(
        attempt_id=attempt.id,
        submitted_at=NOW,
        code_hash="abc",
        graded_up_to=len(levels),
        every_level=True,
        levels=levels,
        tally=Tally(total=sum(level.total for level in levels)),
        duration_ms=300,
    )
    environment.progress.add_submission(record)
    return record


def test_a_project_attempt_lists_its_submissions(project):
    record = submit(project, LevelTally(1, 1, 1, 2, 1))
    assert problem_history(project, PROJECT_SLUG).attempts[0].submissions == (record,)


def test_a_project_attempt_counts_the_levels_its_counted_submission_finished(project):
    submit(project, LevelTally(1, 1, 1, 2, 2))
    assert problem_history(project, PROJECT_SLUG).attempts[0].levels_finished == 1


def test_a_project_attempt_without_submissions_finished_no_level(project):
    assert problem_history(project, PROJECT_SLUG).attempts[0].levels_finished == 0
