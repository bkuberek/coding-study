"""`cstudy history`: one problem's or item's past in this workspace, its review schedule and
every attempt with the runs it recorded (docs/specs/cli.md#cstudy-history).

It reads progress.db, and the content only for the header and the problem's levels. The local web
UI's problem view shows the same history.
"""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import is_item
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.bench_records import BenchRunSummary
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.level_passes import LevelMastery, LevelsPassed, masteries, recorded_levels
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.scheduling import ProblemProgress, ProblemStatus, ScheduleEntry
from coding_study.domain.submissions import SubmissionRecord, counted_submission, levels_finished


@dataclass(frozen=True, slots=True)
class PastAttempt:
    attempt: Attempt
    test_runs: tuple[RunRecord, ...]
    """Earliest first, as are the other runs."""
    submissions: tuple[SubmissionRecord, ...]
    """Empty but for a project attempt."""
    bench_runs: tuple[BenchRunSummary, ...]
    levels_finished: int | None
    """The levels a project attempt's counted submission finished; None for another kind."""
    levels: LevelsPassed | None = None
    """The levels a finished attempt passed (progress-and-scheduling.md#level-passes); None
    without levels, while in progress, and for an attempt failed before attempts recorded
    them."""


@dataclass(frozen=True, slots=True)
class ProblemHistory:
    slug: str
    kind: EntryKind
    track: Track
    difficulty: Difficulty
    patterns: tuple[str, ...]
    """Empty for an item."""
    status: ProblemStatus
    schedule: ScheduleEntry | None
    today: date
    """The local date `status` is of."""
    attempts: tuple[PastAttempt, ...]
    """Every attempt in every language, latest start first."""
    levels: int | None = None
    """The problem's levels now; None without levels."""
    masteries: tuple[tuple[Language, LevelMastery], ...] = ()
    """Each language's best and next goal, in `Language` order; empty without levels."""


@dataclass(frozen=True, slots=True)
class _Header:
    kind: EntryKind
    track: Track
    difficulty: Difficulty
    patterns: tuple[str, ...] = ()
    levels: int | None = None


def problem_history(environment: Environment, slug: str) -> ProblemHistory:
    """Raises UnknownProblemError for a slug that names no problem or item."""
    header = _header(environment, slug)
    progress = environment.progress
    today = environment.clock.local_date(environment.clock.now())
    problem_progress = progress.problem_progress().get(slug, ProblemProgress())
    attempts = progress.attempts(slug)
    return ProblemHistory(
        slug=slug,
        kind=header.kind,
        track=header.track,
        difficulty=header.difficulty,
        patterns=header.patterns,
        status=problem_progress.status(today),
        schedule=problem_progress.schedule,
        today=today,
        attempts=tuple(_past_attempt(environment, attempt, header) for attempt in attempts),
        levels=header.levels,
        masteries=masteries(attempts, header.levels) if header.levels is not None else (),
    )


def _header(environment: Environment, slug: str) -> _Header:
    if is_item(environment, slug):
        item = environment.items.load(slug)
        return _Header(EntryKind.ITEM, item.track, item.difficulty)
    meta = environment.problems.load(slug).meta
    levels = len(meta.levels) if level_progress(meta, None) is not None else None
    return _Header(entry_kind(meta.kind), meta.track, meta.difficulty, meta.patterns, levels)


def _past_attempt(environment: Environment, attempt: Attempt, header: _Header) -> PastAttempt:
    progress = environment.progress
    is_project = header.kind is EntryKind.PROJECT
    submissions = progress.submissions(attempt.id) if is_project else ()
    return PastAttempt(
        attempt=attempt,
        test_runs=progress.test_runs(attempt.id),
        submissions=submissions,
        bench_runs=progress.bench_runs(attempt.id),
        levels_finished=levels_finished(counted_submission(submissions)) if is_project else None,
        levels=recorded_levels(attempt, header.levels) if header.levels is not None else None,
    )
