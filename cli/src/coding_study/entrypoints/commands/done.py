"""`cstudy done` (docs/specs/cli.md#cstudy-done)."""

from datetime import timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.complete_attempt import (
    DoneRequest,
    FinishedAttempt,
    complete_attempt,
)
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.domain.attempts import AttemptStatus, Rating, self_graded
from coding_study.domain.problem import ProblemKind, ProblemMeta
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "done"
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60


def register(app: typer.Typer) -> None:
    add_command(app, done, NAME)


def done(
    context: typer.Context,
    slug: Annotated[
        str | None,
        typer.Argument(help=OPTIONAL_TARGET_HELP),
    ] = None,
    rating: Annotated[
        Rating | None, typer.Option("--rating", help="How it went, after a pass.")
    ] = None,
    gave_up: Annotated[
        bool, typer.Option("--gave-up", help="Finish without a pass (grade again).")
    ] = False,
    notes: Annotated[str | None, typer.Option("--notes", help="Notes kept on the attempt.")] = None,
) -> None:
    """Finish an attempt and schedule its review."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    finished = complete_attempt(environment, DoneRequest(target.slug, rating, gave_up, notes))
    output = console(context)
    output.print(Text(_summary(finished), style="bold"))
    output.print(Text(_next_review(finished)))


def _summary(finished: FinishedAttempt) -> str:
    attempt = finished.attempt
    assert attempt.ended_at is not None
    parts = (
        attempt.slug,
        attempt.language or "",
        attempt.status,
        _levels(finished),
        solve_time_text(attempt.solve_time(attempt.ended_at)),
        _rating(finished),
        f"hints {attempt.hints_used}",
    )
    return " · ".join(part for part in parts if part)


def _levels(finished: FinishedAttempt) -> str:
    """`through level 2 of 4` for a pass below the last level; else a project's `levels 4 of 4`,
    and nothing for a progressive problem."""
    outcome = finished.levels
    if outcome is None:
        return ""
    levels = outcome.levels
    if finished.attempt.status is AttemptStatus.PASSED and levels.partial:
        return levels.text
    if isinstance(finished.meta, ProblemMeta) and finished.meta.kind is ProblemKind.PROJECT:
        return f"levels {levels.passed} of {levels.last}"
    return ""


def _rating(finished: FinishedAttempt) -> str:
    """`rating ok`; a mock project's grade its levels capped below the rating says so."""
    attempt = finished.attempt
    if attempt.rating is None:
        return "gave up"
    rating = f"rating {attempt.rating}"
    cap = finished.levels.cap if finished.levels else None
    if cap is None or attempt.grade is None or cap >= self_graded(attempt.rating):
        return rating
    return f"{rating}, capped at {attempt.grade.name.lower()}"


def _next_review(finished: FinishedAttempt) -> str:
    entry = finished.schedule
    days = (entry.due_on - finished.today).days
    when = f"in {days} day" if days == 1 else f"in {days} days"
    return f"next review  {entry.due_on.isoformat()} ({when}) · ease {entry.state.ease:.2f}"


def solve_time_text(duration: timedelta) -> str:
    """`18m 40s`, `1h 05m` or `42s`."""
    minutes, seconds = divmod(int(duration.total_seconds()), SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"
