"""Attempts and their grades (docs/specs/progress-and-scheduling.md#attempt-lifecycle)."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum

from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language, Problem
from coding_study.domain.stress_runs import full_run_case_count

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
_TIMER_PATTERN = re.compile(r"(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?")


class AttemptMode(StrEnum):
    NEW = "new"
    REVIEW = "review"
    MOCK = "mock"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    ABANDONED = "abandoned"


FINISHED_STATUSES = frozenset({AttemptStatus.PASSED, AttemptStatus.FAILED})


class Rating(StrEnum):
    EASY = "easy"
    OK = "ok"
    HARD = "hard"


class Grade(IntEnum):
    AGAIN = 0
    HARD = 1
    OK = 2
    EASY = 3


class GradeCap(StrEnum):
    """What can hold a grade below its rating (docs/specs/progress-and-scheduling.md#grade), in
    the order the page's done document names them (docs/specs/web-ui.md#attempts)."""

    HINT = "hint"
    TIME_BOX = "time_box"
    SUBOPTIMAL = "suboptimal"
    LEVELS = "levels"
    SOLUTION = "solution"


type Caps = Mapping[GradeCap, Grade]
"""Each cap that holds for an attempt, with the grade it caps at."""

_RATING_GRADES = {Rating.EASY: Grade.EASY, Rating.OK: Grade.OK, Rating.HARD: Grade.HARD}
HINT_GRADE_CAP = Grade.OK
OVER_TIME_GRADE_CAP = Grade.HARD
SUBOPTIMAL_GRADE_CAP = Grade.HARD


@dataclass(frozen=True, slots=True)
class NewAttempt:
    slug: str
    language: Language | None
    """None for items that are not autograded."""
    mode: AttemptMode
    started_at: datetime
    time_limit_s: int | None = None
    stub_path: str | None = None


@dataclass(frozen=True, slots=True)
class Attempt:
    """One row of `attempts`; timestamps are timezone-aware UTC."""

    id: int
    slug: str
    language: Language | None
    mode: AttemptMode
    status: AttemptStatus
    started_at: datetime
    ended_at: datetime | None = None
    first_pass_at: datetime | None = None
    time_limit_s: int | None = None
    """The `--timer` time box."""
    rating: Rating | None = None
    grade: Grade | None = None
    hints_used: int = 0
    solution_revealed: bool = False
    level_unlocked: int | None = None
    stub_path: str | None = None
    archive_path: str | None = None
    notes: str | None = None

    def solve_time(self, ended_at: datetime) -> timedelta:
        """Wall clock since the start; there is no pause."""
        return ended_at - self.started_at

    def abandoned(self, ended_at: datetime) -> "Attempt":
        """The attempt over as `abandoned`: only its status and end change, so it has no grade
        and no rating, and it counts toward no schedule."""
        return replace(self, status=AttemptStatus.ABANDONED, ended_at=ended_at)

    def is_over_time(self, ended_at: datetime) -> bool:
        if self.time_limit_s is None:
            return False
        return self.solve_time(ended_at) > timedelta(seconds=self.time_limit_s)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """One `cstudy test` run (a row of `test_runs`)."""

    attempt_id: int
    ran_at: datetime
    code_hash: str
    """sha256 of the user file(s)."""
    tally: Tally
    duration_ms: int
    time_limit: str | None = None
    """"5x", "1500ms", or None when time limits were off."""


def passed_every_case(run: RunRecord | None, problem: Problem, language: Language) -> bool:
    """Whether a `cstudy test` run passed every case of the problem, as `cstudy done` needs for
    a rating: a run of fewer cases (`--case`, an earlier level) never counts."""
    if run is None:
        return False
    return run.tally.all_passed and run.tally.total == full_run_case_count(problem, language)


def grade_attempt(attempt: Attempt, rating: Rating | None, ended_at: datetime) -> Grade:
    """docs/specs/progress-and-scheduling.md#grade; `rating` None means the user gave up.

    Applies the caps the attempt row knows about; callers apply caps from other facts (such as
    bench verdicts) with `cap_grade`.
    """
    if rating is None:
        return Grade.AGAIN
    return cap_grade(_RATING_GRADES[rating], attempt_caps(attempt, ended_at).values())


def attempt_caps(attempt: Attempt, ended_at: datetime) -> dict[GradeCap, Grade]:
    """The caps the attempt row knows about: a solution revealed before a full pass grades
    `again`, a hint caps at `ok`, finishing past the time box at `hard`."""
    caps: dict[GradeCap, Grade] = {}
    if attempt.solution_revealed and attempt.first_pass_at is None:
        caps[GradeCap.SOLUTION] = Grade.AGAIN
    if attempt.hints_used > 0:
        caps[GradeCap.HINT] = HINT_GRADE_CAP
    if attempt.is_over_time(ended_at):
        caps[GradeCap.TIME_BOX] = OVER_TIME_GRADE_CAP
    return caps


def capped_by(rating: Rating | None, caps: Caps) -> tuple[GradeCap, ...]:
    """The caps below the rating's grade, which therefore lowered it, in `GradeCap` order; none
    without a rating, since giving up grades `again` whatever holds."""
    if rating is None:
        return ()
    rated = _RATING_GRADES[rating]
    return tuple(cap for cap in GradeCap if cap in caps and caps[cap] < rated)


def cap_grade(grade: Grade, caps: Iterable[Grade]) -> Grade:
    """Step 3 of the grade: the minimum wins."""
    return min((grade, *caps))


def self_graded(rating: Rating) -> Grade:
    """Non-autograded items: the rating alone, with no caps (progress-and-scheduling.md#grade)."""
    return _RATING_GRADES[rating]


def parse_timer(text: str) -> int:
    """`--timer` in seconds: `25m`, `1h`, `90s`, `1h30m`, or bare minutes such as `45`."""
    if text.isdigit():
        seconds = int(text) * SECONDS_PER_MINUTE
    else:
        parsed = _TIMER_PATTERN.fullmatch(text)
        seconds = _timer_seconds(parsed) if parsed else 0
    if seconds <= 0:
        raise ValueError(f'invalid timer "{text}": use a duration such as 25m, 1h or 1h30m')
    return seconds


def _timer_seconds(parsed: re.Match[str]) -> int:
    hours, minutes, seconds = (int(parsed[unit] or 0) for unit in ("hours", "minutes", "seconds"))
    return hours * SECONDS_PER_HOUR + minutes * SECONDS_PER_MINUTE + seconds
