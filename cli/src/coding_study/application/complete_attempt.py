"""`cstudy done`: finish an attempt and schedule its review.

Specs: docs/specs/cli.md#cstudy-done and progress-and-scheduling.md. A problem with levels is
graded from the levels it passed (progress-and-scheduling.md#level-passes): those of its latest
test run, or of a project's counted submission instead (progress-and-scheduling.md#project-
attempts). A pass through level 1 takes a rating and passes; a mock keeps an interview's rules.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.level_passes import levels_passed
from coding_study.domain.attempts import (
    SUBOPTIMAL_GRADE_CAP,
    Attempt,
    AttemptMode,
    AttemptStatus,
    Grade,
    GradeCap,
    Rating,
    attempt_caps,
    cap_grade,
    capped_by,
    grade_attempt,
    passed_every_case,
    self_graded,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.items import ItemMeta
from coding_study.domain.level_passes import LevelOutcome, LevelsPassed, level_outcome
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.scheduling import ReviewState, ScheduleEntry, next_review_state

RATINGS = "|".join(Rating)
FINISH_WITH_A_RATING = f"finish with --rating {RATINGS}"


@dataclass(frozen=True, slots=True)
class DoneRequest:
    slug: str | None = None
    rating: Rating | None = None
    gave_up: bool = False
    notes: str | None = None
    language: Language | None = None
    """The attempt's language, when two attempts of `slug` are in progress."""


@dataclass(frozen=True, slots=True)
class FinishedAttempt:
    meta: ProblemMeta | ItemMeta
    attempt: Attempt
    schedule: ScheduleEntry
    today: date
    levels: LevelOutcome | None = None
    """Problems with levels only: the levels passed, and what they made of the attempt."""
    caps: tuple[GradeCap, ...] = ()
    """The caps that held the grade below the rating."""


@dataclass(frozen=True, slots=True)
class _Verdict:
    """How a problem's attempt closes: passed or not, the caps from facts outside its row, and
    the levels it passed."""

    meta: ProblemMeta
    passed: bool
    caps: Mapping[GradeCap, Grade]
    levels: LevelOutcome | None = None


def complete_attempt(environment: Environment, request: DoneRequest) -> FinishedAttempt:
    if (request.rating is None) == (not request.gave_up):
        raise UsageError(f"finish with either --rating {RATINGS} or --gave-up")
    attempt = find_attempt(environment.progress, request.slug, request.language)
    if attempt.language is None:
        return _finish_item(environment, attempt, request)
    problem = environment.problems.load(attempt.slug)
    measured = _measured_caps(environment, attempt)
    levels = levels_passed(environment, attempt, problem)
    if levels is not None:
        outcome = level_outcome(levels, attempt.mode, problem.meta.kind)
        _check_levels_rating(outcome, attempt.mode, problem.meta.kind, request)
        level_caps = {GradeCap.LEVELS: outcome.cap} if outcome.cap is not None else {}
        verdict = _Verdict(problem.meta, outcome.passes, {**measured, **level_caps}, outcome)
        return _close(environment, attempt, request, verdict)
    latest = environment.progress.latest_test_run(attempt.id)
    passed = passed_every_case(latest, problem, attempt.language)
    _check_rating_matches(passed, request)
    return _close(environment, attempt, request, _Verdict(problem.meta, passed, measured))


def _close(
    environment: Environment, attempt: Attempt, request: DoneRequest, verdict: _Verdict
) -> FinishedAttempt:
    now = environment.clock.now()
    levels = verdict.levels.levels if verdict.levels else None
    finished = replace(
        attempt,
        status=AttemptStatus.PASSED if verdict.passed else AttemptStatus.FAILED,
        ended_at=now,
        rating=request.rating,
        grade=cap_grade(grade_attempt(attempt, request.rating, now), verdict.caps.values()),
        notes=request.notes,
        levels_passed=levels.passed if levels else None,
        levels_total=levels.last if levels else None,
    )
    environment.progress.update_attempt(finished)
    schedule = _reschedule(environment, finished)
    caps = capped_by(request.rating, {**attempt_caps(attempt, now), **verdict.caps})
    today = environment.clock.local_date(now)
    return FinishedAttempt(verdict.meta, finished, schedule, today, verdict.levels, caps)


def _measured_caps(environment: Environment, attempt: Attempt) -> dict[GradeCap, Grade]:
    """Grade caps from facts outside the attempt row (progress-and-scheduling.md#grade): with
    `schedule.penalize_suboptimal`, the attempt's latest bench verdict `suboptimal` at
    confidence `medium` or `high` caps the grade at `hard`.
    """
    if not environment.config.schedule.penalize_suboptimal:
        return {}
    outcome = environment.progress.latest_bench_outcome(attempt.id)
    if outcome is None or not outcome.is_confident_suboptimal:
        return {}
    return {GradeCap.SUBOPTIMAL: SUBOPTIMAL_GRADE_CAP}


def _finish_item(
    environment: Environment, attempt: Attempt, request: DoneRequest
) -> FinishedAttempt:
    """Non-autograded items take a rating only and are graded by it alone."""
    meta = environment.items.load(attempt.slug)
    if request.rating is None:
        raise UsageError(f"{attempt.slug} is self-graded; finish with --rating {RATINGS}")
    now = environment.clock.now()
    finished = replace(
        attempt,
        status=AttemptStatus.PASSED,
        ended_at=now,
        rating=request.rating,
        grade=self_graded(request.rating),
        notes=request.notes,
    )
    environment.progress.update_attempt(finished)
    schedule = _reschedule(environment, finished)
    return FinishedAttempt(meta, finished, schedule, environment.clock.local_date(now))


def _check_rating_matches(passed: bool, request: DoneRequest) -> None:
    if passed and request.gave_up:
        raise UsageError(f"the latest test run passed every case; {FINISH_WITH_A_RATING}")
    if not passed and request.rating is not None:
        raise UsageError(
            "the latest test run did not pass every case; run cstudy test, or finish with --gave-up"
        )


def _check_levels_rating(
    outcome: LevelOutcome, mode: AttemptMode, kind: ProblemKind, request: DoneRequest
) -> None:
    """A rating once the levels passed take one, `--gave-up` otherwise, each refusal naming the
    run or submission it read."""
    if outcome.rating_needed and request.gave_up:
        raise UsageError(f"{_levels_read(outcome.levels, kind)}; {FINISH_WITH_A_RATING}")
    if outcome.rating_needed or request.rating is None:
        return
    if kind is ProblemKind.PROJECT:
        raise UsageError(
            "no submission of every unlocked level passed level 1 yet; run cstudy submit, or "
            "finish with --gave-up"
        )
    if mode is AttemptMode.MOCK and outcome.levels.passed >= FIRST_LEVEL:
        raise UsageError(
            f"a mock needs every level, and the latest test run passed {outcome.levels.text}; "
            "run cstudy test, or finish with --gave-up"
        )
    raise UsageError(
        "the latest test run did not pass level 1; run cstudy test, or finish with --gave-up"
    )


def _levels_read(levels: LevelsPassed, kind: ProblemKind) -> str:
    """What passed: `the latest test run passed every case of levels 1 to 2`."""
    if kind is ProblemKind.PROJECT:
        return "the latest submission of every unlocked level passed level 1"
    if levels.every_level:
        return "the latest test run passed every case"
    if levels.passed == FIRST_LEVEL:
        return "the latest test run passed every case of level 1"
    return f"the latest test run passed every case of levels 1 to {levels.passed}"


def _reschedule(environment: Environment, attempt: Attempt) -> ScheduleEntry:
    assert attempt.grade is not None
    assert attempt.ended_at is not None
    previous = environment.progress.schedule_entry(attempt.slug)
    schedule = environment.config.schedule
    state = next_review_state(
        previous.state if previous else ReviewState(),
        attempt.grade,
        schedule.max_interval_days,
        schedule.intervals,
    )
    ended_on = environment.clock.local_date(attempt.ended_at)
    entry = ScheduleEntry(
        slug=attempt.slug,
        state=state,
        due_on=ended_on + timedelta(days=state.interval_days),
        last_grade=attempt.grade,
        updated_at=attempt.ended_at,
    )
    environment.progress.save_schedule_entry(entry)
    return entry
