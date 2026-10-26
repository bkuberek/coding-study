"""A small progress.db whose `cstudy stats` values are computed by hand in
tests/entrypoints/commands/test_stats.py, over the first three catalog problems and the fixture
items."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta

from coding_study.application.environment import Environment
from coding_study.domain.attempts import (
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.bench_records import BenchRunRecord
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry


def october(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class _Finished:
    slug: str
    language: Language | None
    started_at: datetime
    minutes: int
    status: AttemptStatus
    rating: Rating | None
    grade: Grade


PASSED, FAILED = AttemptStatus.PASSED, AttemptStatus.FAILED
FINISHED = (
    _Finished("two-sum", Language.PYTHON, october(20, 9), 20, PASSED, Rating.OK, Grade.OK),
    _Finished("two-sum", Language.KOTLIN, october(22, 9), 40, FAILED, None, Grade.AGAIN),
    _Finished("lru-cache", Language.PYTHON, october(23, 8), 30, PASSED, Rating.HARD, Grade.HARD),
    _Finished("url-shortener", None, october(24, 8), 45, PASSED, Rating.EASY, Grade.EASY),
)
SCHEDULE = (
    # slug, interval, last grade, due on
    ("two-sum", 21, Grade.OK, date(2026, 10, 24)),
    ("lru-cache", 2, Grade.HARD, date(2026, 10, 22)),
    ("url-shortener", 5, Grade.EASY, date(2026, 10, 29)),
)
BENCHES = (
    ("two-sum", october(20, 10), Verdict.SUBOPTIMAL),
    ("two-sum", october(21, 10), Verdict.OPTIMAL),
    ("lru-cache", october(23, 9), Verdict.NEAR_OPTIMAL),
)


def fill_progress(environment: Environment) -> None:
    """Four finished attempts, an abandoned and an unfinished one, three schedule entries, test
    runs and three bench runs."""
    progress = environment.progress
    attempt_ids: dict[str, int] = {}
    for row in FINISHED:
        started = NewAttempt(row.slug, row.language, AttemptMode.NEW, row.started_at)
        attempt = progress.add_attempt(started)
        ended_at = row.started_at + timedelta(minutes=row.minutes)
        progress.update_attempt(
            replace(
                attempt, status=row.status, ended_at=ended_at, rating=row.rating, grade=row.grade
            )
        )
        progress.add_test_run(RunRecord(attempt.id, ended_at, "hash", Tally(4, 4), 300))
        attempt_ids.setdefault(row.slug, attempt.id)
    tree = "invert-binary-tree"
    abandoned = progress.add_attempt(NewAttempt(tree, Language.JAVA, AttemptMode.NEW, october(21)))
    progress.update_attempt(replace(abandoned, status=AttemptStatus.ABANDONED))
    progress.add_attempt(NewAttempt(tree, Language.PYTHON, AttemptMode.NEW, october(24)))
    for slug, interval, grade, due_on in SCHEDULE:
        state = ReviewState(interval_days=interval, reps=2)
        progress.save_schedule_entry(ScheduleEntry(slug, state, due_on, grade, october(20)))
    for slug, ran_at, verdict in BENCHES:
        progress.add_bench_run(
            BenchRunRecord(
                attempt_ids[slug],
                slug,
                Language.PYTHON,
                ran_at,
                "hash",
                (100, 1000),
                (),
                verdict,
                Confidence.HIGH,
                environment={"cpu": "Test CPU"},
            )
        )
