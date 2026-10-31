"""`cstudy done`: finish an attempt and schedule its review.

Specs: docs/specs/cli.md#cstudy-done and progress-and-scheduling.md. A project attempt is graded
from its counted submission instead of its latest test run (progress-and-scheduling.md#project-
attempts): a rating once level 1 passed, capped by the levels finished.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.domain.attempts import (
    SUBOPTIMAL_GRADE_CAP,
    Attempt,
    AttemptStatus,
    Grade,
    Rating,
    cap_grade,
    grade_attempt,
    self_graded,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.items import ItemMeta
from coding_study.domain.problem import Problem, ProblemKind, ProblemMeta
from coding_study.domain.scheduling import ReviewState, ScheduleEntry, next_review_state
from coding_study.domain.stress_runs import full_run_case_count
from coding_study.domain.submissions import counted_submission, level_grade_cap, levels_finished

RATINGS = "|".join(Rating)


@dataclass(frozen=True, slots=True)
class DoneRequest:
    slug: str | None = None
    rating: Rating | None = None
    gave_up: bool = False
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class LevelsFinished:
    """A project attempt's levels finished by its counted submission, and the grade cap they
    set."""

    finished: int
    last: int
    cap: Grade | None


@dataclass(frozen=True, slots=True)
class FinishedAttempt:
    meta: ProblemMeta | ItemMeta
    attempt: Attempt
    schedule: ScheduleEntry
    today: date
    project: LevelsFinished | None = None
    """Project problems only."""


def complete_attempt(environment: Environment, request: DoneRequest) -> FinishedAttempt:
    if (request.rating is None) == (not request.gave_up):
        raise UsageError(f"finish with either --rating {RATINGS} or --gave-up")
    attempt = find_attempt(environment.progress, request.slug, None)
    if attempt.language is None:
        return _finish_item(environment, attempt, request)
    problem = environment.problems.load(attempt.slug)
    if problem.meta.kind is ProblemKind.PROJECT:
        return _finish_project(environment, attempt, problem, request)
    passed = _latest_run_passed(
        environment, attempt, full_run_case_count(problem, attempt.language)
    )
    _check_rating_matches(passed, request)
    now = environment.clock.now()
    caps = _measured_caps(environment, attempt)
    grade = cap_grade(grade_attempt(attempt, request.rating, now), caps)
    finished = replace(
        attempt,
        status=AttemptStatus.PASSED if passed else AttemptStatus.FAILED,
        ended_at=now,
        rating=request.rating,
        grade=grade,
        notes=request.notes,
    )
    environment.progress.update_attempt(finished)
    schedule = _reschedule(environment, finished)
    return FinishedAttempt(problem.meta, finished, schedule, environment.clock.local_date(now))


def _finish_project(
    environment: Environment, attempt: Attempt, problem: Problem, request: DoneRequest
) -> FinishedAttempt:
    """The counted submission stands in for the latest test run: a rating once it passed level 1,
    `--gave-up` otherwise; the levels it finished cap the grade, and only all of them pass."""
    counted = counted_submission(environment.progress.submissions(attempt.id))
    levels = LevelsFinished(levels_finished(counted), len(problem.meta.levels), None)
    levels = replace(levels, cap=level_grade_cap(levels.finished, levels.last))
    if levels.finished and request.gave_up:
        raise UsageError(
            f"the latest submission of every unlocked level passed level 1; "
            f"finish with --rating {RATINGS}"
        )
    if not levels.finished and request.rating is not None:
        raise UsageError(
            "no submission of every unlocked level passed level 1 yet; run cstudy submit, or "
            "finish with --gave-up"
        )
    now = environment.clock.now()
    caps = (levels.cap,) if levels.cap is not None else ()
    finished = replace(
        attempt,
        status=AttemptStatus.PASSED if levels.cap is None else AttemptStatus.FAILED,
        ended_at=now,
        rating=request.rating,
        grade=cap_grade(grade_attempt(attempt, request.rating, now), caps),
        notes=request.notes,
    )
    environment.progress.update_attempt(finished)
    schedule = _reschedule(environment, finished)
    today = environment.clock.local_date(now)
    return FinishedAttempt(problem.meta, finished, schedule, today, levels)


def _measured_caps(environment: Environment, attempt: Attempt) -> tuple[Grade, ...]:
    """Grade caps from facts outside the attempt row (progress-and-scheduling.md#grade): with
    `schedule.penalize_suboptimal`, the attempt's latest bench verdict `suboptimal` at
    confidence `medium` or `high` caps the grade at `hard`.
    """
    if not environment.config.schedule.penalize_suboptimal:
        return ()
    outcome = environment.progress.latest_bench_outcome(attempt.id)
    if outcome is None or not outcome.is_confident_suboptimal:
        return ()
    return (SUBOPTIMAL_GRADE_CAP,)


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


def _latest_run_passed(environment: Environment, attempt: Attempt, full_run_total: int) -> bool:
    """Whether the latest `cstudy test` run passed every case of the problem."""
    latest = environment.progress.latest_test_run(attempt.id)
    return latest is not None and latest.tally.all_passed and latest.tally.total == full_run_total


def _check_rating_matches(passed: bool, request: DoneRequest) -> None:
    if passed and request.gave_up:
        raise UsageError(f"the latest test run passed every case; finish with --rating {RATINGS}")
    if not passed and request.rating is not None:
        raise UsageError(
            "the latest test run did not pass every case; run cstudy test, or finish with --gave-up"
        )


def _reschedule(environment: Environment, attempt: Attempt) -> ScheduleEntry:
    assert attempt.grade is not None
    assert attempt.ended_at is not None
    previous = environment.progress.schedule_entry(attempt.slug)
    state = next_review_state(
        previous.state if previous else ReviewState(),
        attempt.grade,
        environment.config.schedule.max_interval_days,
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
