"""Mock interviews (docs/specs/cli.md#cstudy-mock).

`cstudy mock` picks new medium and hard problems with the `cstudy next` rules and starts them with
one shared timer; while that timer runs and a problem is unfinished, hints and solutions stay
locked.
The session is not stored separately: it is the attempts in progress with mode `mock`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus
from coding_study.domain.next_selection import Candidate, NewPick, NextQuery, NextSource, pick_next
from coding_study.domain.problem import Difficulty
from coding_study.domain.weakness import GradedAttempt

MOCK_DIFFICULTIES = frozenset({Difficulty.MEDIUM, Difficulty.HARD})


def pick_mock(
    candidates: Sequence[Candidate],
    attempts: Sequence[GradedAttempt],
    query: NextQuery,
    count: int,
) -> tuple[NewPick, ...]:
    """Up to `count` new medium or hard problems, each from a group not picked yet when one
    still has a new problem in scope.

    The `cstudy next` rules run over the medium and hard problems only, so their difficulty gate
    opens medium at once. Picked problems and groups are held back as if in progress: they leave
    the candidates but keep counting for their group's weakness.
    """
    pool = [candidate for candidate in candidates if candidate.difficulty in MOCK_DIFFICULTIES]
    new_only = replace(query, source=NextSource.NEW_ONLY)
    picks: list[NewPick] = []
    for _ in range(count):
        slugs = {pick.candidate.slug for pick in picks}
        groups = {pick.group for pick in picks}
        in_other_groups = [
            _held(candidate) if candidate.group in groups else candidate
            for candidate in _without(pool, slugs)
        ]
        pick = pick_next(in_other_groups, attempts, new_only) or pick_next(
            _without(pool, slugs), attempts, new_only
        )
        if not isinstance(pick, NewPick):
            break
        picks.append(pick)
    return tuple(picks)


def _without(pool: Sequence[Candidate], slugs: set[str]) -> list[Candidate]:
    """The pool with these problems held back."""
    return [_held(candidate) if candidate.slug in slugs else candidate for candidate in pool]


def _held(candidate: Candidate) -> Candidate:
    progress = candidate.progress
    statuses = progress.attempt_statuses | {AttemptStatus.IN_PROGRESS}
    return replace(candidate, progress=replace(progress, attempt_statuses=statuses))


@dataclass(frozen=True, slots=True)
class RunningMock:
    slugs: tuple[str, ...]
    """The unfinished problems, sorted."""
    ends_at: datetime

    def remaining(self, now: datetime) -> timedelta:
        return self.ends_at - now


def running_mock(in_progress: Sequence[Attempt], now: datetime) -> RunningMock | None:
    """The mock interview whose timer still runs, from the attempts in progress; None when there
    is none, its timer ended, or every problem is done."""
    ends = {
        attempt.slug: end
        for attempt in in_progress
        if (end := _mock_end(attempt)) is not None and end > now
    }
    if not ends:
        return None
    return RunningMock(tuple(sorted(ends)), max(ends.values()))


def _mock_end(attempt: Attempt) -> datetime | None:
    if attempt.mode is not AttemptMode.MOCK or attempt.status is not AttemptStatus.IN_PROGRESS:
        return None
    if attempt.time_limit_s is None:
        return None
    return attempt.started_at + timedelta(seconds=attempt.time_limit_s)
