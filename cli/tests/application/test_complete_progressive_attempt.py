"""`cstudy done` on a progressive problem: a pass through level N of M is a pass
(docs/decisions/0024-level-passes.md, docs/specs/cli.md#cstudy-done)."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.environment import Environment
from coding_study.application.run_tests import RunTestsRequest, run_tests
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import Attempt, AttemptStatus, Grade, Rating, RunRecord
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.level_passes import LevelsPassed
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import LevelReview, ReviewState
from tests.application.test_progressive_practice import environment_for
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment
from tests.fakes import repository_root as copy_repository

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
SLUG = "level-store"
LEVELS = 3
CASES = 12


def started(tmp_path: Path, implemented: int, mock: bool = False) -> Environment:
    environment = environment_for(tmp_path, implemented)
    start_attempt(environment, StartRequest(SLUG, mock=mock))
    return environment


def active(environment: Environment) -> Attempt:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    return attempt


def run(environment: Environment, **fields) -> None:
    run_tests(environment, RunTestsRequest(**fields), lambda _line: None)


def runs(environment: Environment, count: int) -> None:
    for _ in range(count):
        run(environment)


def done(environment: Environment, rating: Rating | None = Rating.OK):
    return complete_attempt(environment, DoneRequest(rating=rating, gave_up=rating is None))


def through_level_2(tmp_path: Path, mock: bool = False) -> Environment:
    """Levels 1 and 2 pass and level 3 is open, with a run that fails it."""
    environment = started(tmp_path, implemented=2, mock=mock)
    runs(environment, 3)
    return environment


def test_a_pass_through_level_2_of_3_takes_a_rating_and_passes(tmp_path):
    attempt = done(through_level_2(tmp_path)).attempt
    assert (attempt.status, attempt.grade) == (AttemptStatus.PASSED, Grade.OK)


def test_the_attempt_records_the_levels_it_passed(tmp_path):
    attempt = done(through_level_2(tmp_path)).attempt
    assert (attempt.levels_passed, attempt.levels_total) == (2, LEVELS)


def test_the_levels_are_reported(tmp_path):
    levels = done(through_level_2(tmp_path)).levels
    assert levels is not None
    assert (levels.levels, levels.cap) == (LevelsPassed(2, LEVELS), None)


def test_a_pass_through_a_level_is_graded_from_the_rating_alone(tmp_path):
    assert done(through_level_2(tmp_path), Rating.EASY).attempt.grade is Grade.EASY


def test_a_pass_through_a_level_schedules_as_any_pass(tmp_path):
    assert done(through_level_2(tmp_path)).schedule.state.interval_days == 3


def test_a_pass_through_a_level_refuses_gave_up(tmp_path):
    message = "levels 1 to 2; finish with --rating easy|ok|hard"
    with pytest.raises(UsageError, match=re.escape(message)):
        done(through_level_2(tmp_path), None)


def test_a_hint_still_caps_a_pass_through_a_level(tmp_path):
    environment = through_level_2(tmp_path)
    attempt = active(environment)
    environment.progress.update_attempt(replace(attempt, hints_used=1))
    assert done(environment, Rating.EASY).attempt.grade is Grade.OK


def test_a_solution_revealed_before_every_level_passed_still_grades_again(tmp_path):
    environment = through_level_2(tmp_path)
    attempt = active(environment)
    environment.progress.update_attempt(replace(attempt, solution_revealed=True))
    attempt = done(environment, Rating.EASY).attempt
    assert (attempt.status, attempt.grade) == (AttemptStatus.PASSED, Grade.AGAIN)


def test_level_n_is_the_highest_passed_level_below_the_unlocked_one(tmp_path):
    environment = started(tmp_path, implemented=1)
    runs(environment, 2)
    attempt = done(environment).attempt
    assert (attempt.level_unlocked, attempt.levels_passed) == (2, 1)


def test_a_run_of_the_lower_levels_counts_for_them(tmp_path):
    environment = started(tmp_path, implemented=3)
    runs(environment, 2)
    run(environment, level=1)
    assert done(environment).attempt.levels_passed == 1


def test_every_level_passed_records_every_level(tmp_path):
    environment = started(tmp_path, implemented=3)
    runs(environment, 3)
    attempt = done(environment).attempt
    assert (attempt.status, attempt.levels_passed, attempt.levels_total) == (
        AttemptStatus.PASSED,
        LEVELS,
        LEVELS,
    )


def test_no_level_passed_refuses_a_rating(tmp_path):
    environment = started(tmp_path, implemented=0)
    run(environment)
    with pytest.raises(UsageError, match="did not pass level 1; run cstudy test, or finish with"):
        done(environment)


def test_no_level_passed_gives_up_with_grade_again(tmp_path):
    environment = started(tmp_path, implemented=0)
    run(environment)
    attempt = done(environment, None).attempt
    assert (attempt.status, attempt.grade, attempt.levels_passed) == (
        AttemptStatus.FAILED,
        Grade.AGAIN,
        0,
    )


def test_without_a_run_only_gave_up_finishes(tmp_path):
    environment = started(tmp_path, implemented=3)
    with pytest.raises(UsageError, match="--gave-up"):
        done(environment)


def test_a_run_recorded_before_level_passes_counts_every_level_when_it_passed_every_case(
    tmp_path,
):
    environment = started(tmp_path, implemented=3)
    attempt = active(environment)
    tally = Tally(total=CASES, passed=CASES)
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", tally, 10))
    assert done(environment).attempt.levels_passed == LEVELS


def test_a_run_recorded_before_level_passes_that_failed_a_case_passes_no_level(tmp_path):
    environment = started(tmp_path, implemented=3)
    attempt = active(environment)
    tally = Tally(total=CASES, passed=CASES - 1, failed=1)
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", tally, 10))
    with pytest.raises(UsageError, match="--gave-up"):
        done(environment)


# A mock keeps the rule of an interview: every level for a pass


def test_a_mock_through_level_2_refuses_a_rating(tmp_path):
    with pytest.raises(UsageError, match="a mock needs every level"):
        done(through_level_2(tmp_path, mock=True))


def test_a_mock_through_level_2_gives_up_and_fails(tmp_path):
    attempt = done(through_level_2(tmp_path, mock=True), None).attempt
    assert (attempt.status, attempt.grade, attempt.levels_passed) == (
        AttemptStatus.FAILED,
        Grade.AGAIN,
        2,
    )


def test_a_mock_through_every_level_passes(tmp_path):
    environment = started(tmp_path, implemented=3, mock=True)
    runs(environment, 3)
    assert done(environment).attempt.status is AttemptStatus.PASSED


def test_a_problem_without_levels_records_no_levels(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(copy_repository(tmp_path, PRACTICE), toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum"))
    attempt = done(environment, None).attempt
    assert (attempt.levels_passed, attempt.levels_total) == (None, None)


def test_done_gives_each_level_passed_after_the_first_its_own_review(tmp_path):
    environment = through_level_2(tmp_path)
    done(environment)
    entry = environment.progress.schedule_entry(SLUG)
    assert entry is not None
    assert entry.levels == (LevelReview(2, ReviewState(interval_days=3, reps=1), Grade.OK),)


def test_done_of_a_problem_without_levels_keeps_no_level_reviews(tmp_path):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(copy_repository(tmp_path, PRACTICE), toolchains=toolchains)
    start_attempt(environment, StartRequest("two-sum"))
    done(environment, None)
    entry = environment.progress.schedule_entry("two-sum")
    assert entry is not None
    assert entry.levels is None
