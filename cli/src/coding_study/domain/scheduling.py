"""Spaced repetition and problem status (docs/specs/progress-and-scheduling.md).

A simplified SM-2 per problem, language-agnostic: the interval uses the old ease, which is
updated afterwards. The fixed intervals and the mastered threshold are the user's to set
(`schedule` in docs/specs/cli.md#configuration); the ease and its multipliers are not.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from coding_study.domain.attempts import FINISHED_STATUSES, AttemptStatus, Grade

INITIAL_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 3.0
EASE_STEP_AGAIN = 0.20
EASE_STEP_HARD = 0.15
EASE_STEP_EASY = 0.10
HARD_GROWTH = 1.2
EASY_BONUS = 1.3
EASE_DECIMALS = 2
MASTERED_INTERVAL_DAYS = 21


@dataclass(frozen=True, slots=True)
class ReviewIntervals:
    """The fixed intervals of the scheduling table, in days: the first review after a new start
    or a lapse, and the second, which `hard` and `again` have no row for."""

    again: int = 1
    hard_first: int = 2
    ok_first: int = 3
    ok_second: int = 7
    easy_first: int = 5
    easy_second: int = 12

    def first(self, grade: Grade) -> int:
        match grade:
            case Grade.HARD:
                return self.hard_first
            case Grade.EASY:
                return self.easy_first
            case _:
                return self.ok_first

    def second(self, grade: Grade) -> int:
        return self.easy_second if grade is Grade.EASY else self.ok_second


DEFAULT_REVIEW_INTERVALS = ReviewIntervals()


@dataclass(frozen=True, slots=True)
class ReviewState:
    ease: float = INITIAL_EASE
    interval_days: int = 0
    reps: int = 0
    lapses: int = 0


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """One row of `schedule`."""

    slug: str
    state: ReviewState
    due_on: date
    """A local calendar date."""
    last_grade: Grade
    updated_at: datetime


def next_review_state(
    state: ReviewState,
    grade: Grade,
    max_interval_days: int,
    intervals: ReviewIntervals = DEFAULT_REVIEW_INTERVALS,
) -> ReviewState:
    if grade is Grade.AGAIN:
        return ReviewState(
            ease=_ease(state.ease - EASE_STEP_AGAIN),
            interval_days=min(intervals.again, max_interval_days),
            reps=0,
            lapses=state.lapses + 1,
        )
    return ReviewState(
        ease=_ease(_next_ease(state.ease, grade)),
        interval_days=min(_next_interval(state, grade, intervals), max_interval_days),
        reps=state.reps + 1,
        lapses=state.lapses,
    )


def _next_interval(state: ReviewState, grade: Grade, intervals: ReviewIntervals) -> int:
    if state.reps == 0:
        return intervals.first(grade)
    if grade is Grade.HARD:
        return max(state.interval_days + 1, _round_half_up(state.interval_days * HARD_GROWTH))
    if state.reps == 1:
        return intervals.second(grade)
    bonus = EASY_BONUS if grade is Grade.EASY else 1
    return _round_half_up(state.interval_days * state.ease * bonus)


def _next_ease(ease: float, grade: Grade) -> float:
    match grade:
        case Grade.HARD:
            return ease - EASE_STEP_HARD
        case Grade.EASY:
            return ease + EASE_STEP_EASY
        case _:
            return ease


def _ease(ease: float) -> float:
    return round(min(MAX_EASE, max(MIN_EASE, ease)), EASE_DECIMALS)


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


class ProblemStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    ATTEMPTED = "attempted"
    PASSED = "passed"
    DUE = "due"
    MASTERED = "mastered"

    @property
    def label(self) -> str:
        """The status as people read it, `in progress`; the value is for `--json` and the API."""
        return self.value.replace("_", " ")


@dataclass(frozen=True, slots=True)
class ProblemProgress:
    """What `cstudy list` knows about one problem from progress.db."""

    attempt_statuses: frozenset[AttemptStatus] = frozenset()
    schedule: ScheduleEntry | None = None
    mastered_interval_days: int = MASTERED_INTERVAL_DAYS

    def status(self, today: date) -> ProblemStatus:
        """docs/specs/progress-and-scheduling.md#problem-status"""
        if self.in_progress:
            return ProblemStatus.IN_PROGRESS
        if self.is_due(today):
            return ProblemStatus.DUE
        if self.has_passed:
            return ProblemStatus.MASTERED if self.is_mastered else ProblemStatus.PASSED
        if AttemptStatus.FAILED in self.attempt_statuses:
            return ProblemStatus.ATTEMPTED
        return ProblemStatus.NEW

    def is_due(self, today: date) -> bool:
        return self.schedule is not None and self.schedule.due_on <= today

    @property
    def is_new(self) -> bool:
        """No finished attempt; abandoned and unfinished ones do not count."""
        return not self.attempt_statuses & FINISHED_STATUSES

    @property
    def has_passed(self) -> bool:
        return AttemptStatus.PASSED in self.attempt_statuses

    @property
    def in_progress(self) -> bool:
        return AttemptStatus.IN_PROGRESS in self.attempt_statuses

    @property
    def is_mastered(self) -> bool:
        """Mastered even while due: `due` only takes precedence when shown."""
        entry = self.schedule
        return (
            entry is not None
            and entry.state.interval_days >= self.mastered_interval_days
            and entry.last_grade >= Grade.OK
        )
