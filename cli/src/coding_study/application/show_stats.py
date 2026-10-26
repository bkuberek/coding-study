"""`cstudy stats`: a progress summary (docs/specs/cli.md#cstudy-stats).

The rules are pure (`coding_study.domain.progress_stats`); this gathers their inputs: every
problem and item with its progress, the finished attempts and the latest bench verdicts.
"""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import practice_candidates
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.problem import Track
from coding_study.domain.progress_stats import (
    BenchGrade,
    ProgressStats,
    StatsAttempt,
    StatsGrouping,
    StatsQuery,
    progress_stats,
)


@dataclass(frozen=True, slots=True)
class StatsRequest:
    grouping: StatsGrouping = StatsGrouping.PATTERN
    since: date | None = None


@dataclass(frozen=True, slots=True)
class StatsView:
    query: StatsQuery
    stats: ProgressStats


def show_stats(environment: Environment, request: StatsRequest) -> StatsView:
    clock = environment.clock
    query = StatsQuery(clock.local_date(clock.now()), request.grouping, request.since)
    entries = practice_candidates(environment, tuple(Track))
    attempts = tuple(
        found
        for attempt in environment.progress.finished_attempts()
        if (found := _stats_attempt(environment, attempt)) is not None
    )
    bench = tuple(
        BenchGrade(latest.slug, latest.language, latest.verdict, clock.local_date(latest.ran_at))
        for latest in environment.progress.latest_bench_verdicts()
    )
    return StatsView(query, progress_stats(entries, attempts, bench, query))


def _stats_attempt(environment: Environment, attempt: Attempt) -> StatsAttempt | None:
    if attempt.grade is None or attempt.ended_at is None:
        return None
    return StatsAttempt(
        id=attempt.id,
        slug=attempt.slug,
        language=attempt.language,
        passed=attempt.status is AttemptStatus.PASSED,
        grade=attempt.grade,
        started_at=attempt.started_at,
        ended_at=attempt.ended_at,
        ended_on=environment.clock.local_date(attempt.ended_at),
    )
