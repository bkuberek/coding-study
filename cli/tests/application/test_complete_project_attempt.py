"""`cstudy done` on a project attempt: graded from its counted submission
(docs/specs/cli.md#cstudy-done, progress-and-scheduling.md#project-attempts)."""

import re
from dataclasses import replace
from datetime import timedelta

import pytest

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus, Grade, Rating
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from tests.fakes import NOW
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment

PASSED_1 = LevelTally(1, 1, 1, 2, 2)
FAILED_1 = LevelTally(1, 1, 1, 2, 1)
PASSED_2 = LevelTally(2, 1, 1, 2, 2)
FAILED_2 = LevelTally(2, 1, 0, 2, 2)


@pytest.fixture
def environment(tmp_path) -> Environment:
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def submit(environment: Environment, *levels: LevelTally, every_level: bool = True) -> None:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.add_submission(
        SubmissionRecord(
            attempt_id=attempt.id,
            submitted_at=NOW,
            code_hash="abc",
            graded_up_to=len(levels),
            every_level=every_level,
            levels=levels,
            tally=Tally(total=sum(level.total for level in levels)),
            duration_ms=300,
        )
    )


def done(environment: Environment, rating: Rating | None = Rating.OK):
    return complete_attempt(environment, DoneRequest(rating=rating, gave_up=rating is None))


def test_without_a_submission_a_rating_is_refused(environment):
    with pytest.raises(UsageError, match="run cstudy submit, or finish with --gave-up"):
        done(environment)


def test_without_a_submission_giving_up_grades_again(environment):
    assert done(environment, None).attempt.grade is Grade.AGAIN


def test_a_counted_submission_that_failed_level_1_needs_gave_up(environment):
    submit(environment, FAILED_1)
    with pytest.raises(UsageError):
        done(environment)


def test_a_submission_of_lower_levels_does_not_count(environment):
    submit(environment, PASSED_1, every_level=False)
    with pytest.raises(UsageError):
        done(environment)


def test_once_level_1_passed_a_rating_is_required(environment):
    submit(environment, PASSED_1, FAILED_2)
    with pytest.raises(UsageError, match=re.escape("finish with --rating easy|ok|hard")):
        done(environment, None)


def test_every_level_finished_is_not_capped(environment):
    submit(environment, PASSED_1, PASSED_2)
    assert done(environment).attempt.grade is Grade.OK


def test_every_level_finished_passes_the_attempt(environment):
    submit(environment, PASSED_1, PASSED_2)
    assert done(environment).attempt.status is AttemptStatus.PASSED


def test_all_but_the_last_level_caps_at_hard(environment):
    submit(environment, PASSED_1, FAILED_2)
    assert done(environment, Rating.EASY).attempt.grade is Grade.HARD


def test_fewer_levels_finished_fail_the_attempt_even_with_a_rating(environment):
    submit(environment, PASSED_1, FAILED_2)
    assert done(environment).attempt.status is AttemptStatus.FAILED


def test_the_latest_counted_submission_stands(environment):
    submit(environment, PASSED_1, PASSED_2)
    submit(environment, PASSED_1, FAILED_2)
    assert done(environment).attempt.grade is Grade.HARD


def test_the_levels_finished_are_reported(environment):
    submit(environment, PASSED_1, FAILED_2)
    project = done(environment).project
    assert project is not None
    assert (project.finished, project.last, project.cap) == (1, 2, Grade.HARD)


def test_the_time_box_still_caps_the_grade(environment):
    submit(environment, PASSED_1, PASSED_2)
    attempt = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(attempt, time_limit_s=60))
    environment.clock.advance(timedelta(hours=1))
    assert done(environment, Rating.EASY).attempt.grade is Grade.HARD
