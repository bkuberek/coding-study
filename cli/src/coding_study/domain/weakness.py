"""Weakness per group (docs/specs/progress-and-scheduling.md#weakness-score).

Scores are exact fractions, so groups that are equally weak tie exactly and fall through to
the taxonomy and track order.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction

from coding_study.domain.attempts import Grade
from coding_study.domain.problem import Track
from coding_study.domain.taxonomy import PATTERNS, pattern_rank

RECENT_ATTEMPTS = 10
FAILING_GRADE = Grade.HARD
"""Grades at or below this count as failures."""
FAIL_RATE_WITHOUT_ATTEMPTS = Fraction(1, 2)
STALE_AFTER_DAYS = 30
FAIL_RATE_WEIGHT = Fraction(1, 2)
MASTERY_WEIGHT = Fraction(3, 10)
STALENESS_WEIGHT = Fraction(1, 5)
_TRACK_ORDER = tuple(Track)


@dataclass(frozen=True, slots=True)
class Group:
    """The primary pattern of a `dsa` problem, or the track of anything else."""

    track: Track
    pattern: str | None = None

    @property
    def name(self) -> str:
        return self.pattern or self.track.value

    def tie_break_key(self) -> tuple[int, int, str]:
        """Taxonomy order, then track order; track groups come after every pattern."""
        rank = pattern_rank(self.pattern) if self.pattern else len(PATTERNS)
        return rank, _TRACK_ORDER.index(self.track), self.name


def group_of(track: Track, patterns: Sequence[str]) -> Group:
    if track is Track.DSA and patterns:
        return Group(track, patterns[0])
    return Group(track)


@dataclass(frozen=True, slots=True)
class GradedAttempt:
    """A finished (`passed` or `failed`) attempt."""

    id: int
    slug: str
    grade: Grade
    ended_at: datetime
    ended_on: date
    """The local calendar date of `ended_at`."""


@dataclass(frozen=True, slots=True)
class GroupHistory:
    """What the score of one group needs, over the problems in the current scope."""

    problems: int
    mastered: int
    attempts: Sequence[GradedAttempt]
    """Finished attempts on the group's problems, in any order."""

    def weakness(self, today: date) -> Fraction:
        """`0.5 * fail_rate + 0.3 * (1 - mastery) + 0.2 * staleness`, in [0, 1]."""
        return (
            FAIL_RATE_WEIGHT * self._fail_rate()
            + MASTERY_WEIGHT * (1 - self._mastery())
            + STALENESS_WEIGHT * self._staleness(today)
        )

    def _latest_first(self) -> list[GradedAttempt]:
        def recency(attempt: GradedAttempt) -> tuple[datetime, int]:
            return attempt.ended_at, attempt.id

        return sorted(self.attempts, key=recency, reverse=True)

    def _fail_rate(self) -> Fraction:
        recent = self._latest_first()[:RECENT_ATTEMPTS]
        if not recent:
            return FAIL_RATE_WITHOUT_ATTEMPTS
        failures = sum(1 for attempt in recent if attempt.grade <= FAILING_GRADE)
        return Fraction(failures, len(recent))

    def _mastery(self) -> Fraction:
        return Fraction(self.mastered, self.problems) if self.problems else Fraction(0)

    def _staleness(self, today: date) -> Fraction:
        if not self.attempts:
            return Fraction(1)
        days = (today - max(attempt.ended_on for attempt in self.attempts)).days
        return min(Fraction(1), Fraction(max(days, 0), STALE_AFTER_DAYS))
