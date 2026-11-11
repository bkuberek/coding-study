from datetime import UTC, datetime

import pytest

from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus
from coding_study.domain.concept_guides import (
    PathStep,
    ProblemFacts,
    StepKind,
    guide_step_progress,
    highest_level_passed,
    problem_step_progress,
    unknown_slug_message,
)
from coding_study.domain.scheduling import ProblemStatus

STARTED = datetime(2026, 11, 11, 9, tzinfo=UTC)


def attempt(
    status: AttemptStatus, level_unlocked: int | None = None, levels_passed: int | None = None
) -> Attempt:
    return Attempt(
        id=1,
        slug="ledger",
        language=None,
        mode=AttemptMode.NEW,
        status=status,
        started_at=STARTED,
        level_unlocked=level_unlocked,
        levels_passed=levels_passed,
        levels_total=None if levels_passed is None else 4,
    )


def facts(
    status: ProblemStatus = ProblemStatus.NEW, passed: bool = False, level: int | None = None
) -> ProblemFacts:
    return ProblemFacts(title="Ledger", status=status, passed=passed, level_passed=level)


def test_a_step_is_a_guide_or_a_problem():
    assert (PathStep.guide("a").kind, PathStep.problem("b", 2)) == (
        StepKind.GUIDE,
        PathStep(StepKind.PROBLEM, "b", 2),
    )


def test_a_read_guide_is_done():
    progress = guide_step_progress(PathStep.guide("hash-maps"), "Hash maps", read=True)
    assert (progress.done, progress.status) == (True, "read")


def test_an_unread_guide_is_not_done():
    progress = guide_step_progress(PathStep.guide("hash-maps"), "Hash maps", read=False)
    assert (progress.done, progress.status) == (False, "not read")


def test_a_problem_is_done_once_passed():
    progress = problem_step_progress(PathStep.problem("ledger"), facts(ProblemStatus.DUE, True))
    assert (progress.done, progress.status) == (True, "passed")


def test_a_problem_not_passed_shows_its_status_in_words():
    progress = problem_step_progress(PathStep.problem("ledger"), facts(ProblemStatus.IN_PROGRESS))
    assert (progress.done, progress.status) == (False, "in progress")


def test_a_level_target_is_done_once_that_level_passed():
    progress = problem_step_progress(PathStep.problem("ledger", 2), facts(level=3))
    assert (progress.done, progress.status, progress.level_passed) == (True, "level 3 passed", 3)


def test_a_level_target_not_reached_shows_the_levels_passed():
    progress = problem_step_progress(PathStep.problem("ledger", 3), facts(level=1))
    assert (progress.done, progress.status) == (False, "level 1 passed")


def test_a_level_target_with_no_level_passed_shows_the_status():
    progress = problem_step_progress(PathStep.problem("ledger", 2), facts(level=0))
    assert (progress.done, progress.status) == (False, "new")


def test_a_passed_problem_meets_any_level_target():
    progress = problem_step_progress(PathStep.problem("ledger", 4), facts(passed=True, level=4))
    assert (progress.done, progress.status) == (True, "passed")


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [
        ((), 0),
        ((attempt(AttemptStatus.IN_PROGRESS, 1),), 0),
        ((attempt(AttemptStatus.IN_PROGRESS, 3),), 2),
        ((attempt(AttemptStatus.ABANDONED, 4), attempt(AttemptStatus.FAILED, 2)), 3),
        ((attempt(AttemptStatus.PASSED, 4),), 4),
        ((attempt(AttemptStatus.PASSED, 1, levels_passed=2),), 2),
        ((attempt(AttemptStatus.PASSED, 3, levels_passed=1),), 2),
        ((attempt(AttemptStatus.PASSED, 4, levels_passed=4),), 4),
    ],
)
def test_the_highest_level_passed_reads_the_unlocked_levels(
    attempts: tuple[Attempt, ...], expected: int
):
    assert highest_level_passed(attempts, levels=4) == expected


def test_a_problem_without_levels_has_no_level_passed():
    assert highest_level_passed((attempt(AttemptStatus.PASSED),), levels=0) is None


def test_an_unknown_slug_suggests_the_nearest():
    assert unknown_slug_message("guide", "hash-fn", ["hash-functions", "prefix-sums"]) == (
        'unknown guide "hash-fn"; did you mean hash-functions?'
    )


def test_an_unknown_slug_with_nothing_near_says_where_to_look():
    assert unknown_slug_message("path", "zzz", ["hashing"]) == (
        'unknown path "zzz"; cstudy learn lists the paths'
    )
