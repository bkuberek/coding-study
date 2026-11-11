"""`cstudy history` (docs/specs/cli.md#cstudy-history).

The header, the review line, the best level of each language for a problem with levels, then every
attempt newest first. Times show in local time; a column is as wide as its widest value.
"""

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.problem_history import PastAttempt, ProblemHistory, problem_history
from coding_study.application.resolve_target import ProblemTarget, resolve_problem
from coding_study.domain.attempts import Attempt, AttemptStatus, Grade, RunRecord
from coding_study.domain.bench_records import BenchRunSummary
from coding_study.domain.cases import JsonValue
from coding_study.domain.items import EntryKind
from coding_study.domain.level_passes import LevelMastery, status_text
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ScheduleEntry
from coding_study.domain.submissions import SubmissionRecord
from coding_study.entrypoints.commands.done import solve_time_text
from coding_study.entrypoints.commands.project_documents import level_tally_value
from coding_study.entrypoints.shared import (
    PROBLEM_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "history"
LABEL_WIDTH = 11
COLUMN_GAP = 2
NO_VALUE = "-"
NO_ATTEMPTS = "no attempts yet"
NOT_SCHEDULED = "not scheduled"
SOLUTION_MARK = "solution"
LOCAL_MINUTE = "%Y-%m-%d %H:%M"
UNTIMED = frozenset({AttemptStatus.IN_PROGRESS, AttemptStatus.ABANDONED})
"""Statuses without a solve time."""
_HEADER = (
    "ATTEMPT",
    "LANG",
    "MODE",
    "STATUS",
    "STARTED",
    "TIME",
    "RATING",
    "GRADE",
    "HINTS",
    "TESTS",
    "BENCH",
)


def register(app: typer.Typer) -> None:
    add_command(app, history, NAME)


def history(
    context: typer.Context,
    slug: Annotated[str, typer.Argument(help=PROBLEM_TARGET_HELP)],
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the report.")
    ] = False,
) -> None:
    """Show a problem's attempts, runs and review schedule."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_problem(environment, ProblemTarget(slug), Path.cwd())
    found = problem_history(environment, target.slug)
    if as_json:
        typer.echo(json.dumps(history_document(found), indent=2))
        return
    output = console(context)
    output.print(Text(_header(found), style="bold"))
    review = Text("review".ljust(LABEL_WIDTH), style="dim")
    review.append(_review(found))
    output.print(review)
    best = _best(found)
    if best:
        line = Text("passed".ljust(LABEL_WIDTH), style="dim")
        line.append(best)
        output.print(line)
    output.print()
    if not found.attempts:
        output.print(NO_ATTEMPTS)
        return
    rows = _rows(found)
    output.print(Text(next(rows), style="bold"))
    for row in rows:
        output.print(Text(row))


def history_document(found: ProblemHistory) -> dict[str, JsonValue]:
    """`cstudy history --json`."""
    attempts: list[JsonValue] = [_attempt_value(past) for past in found.attempts]
    return {
        "slug": found.slug,
        "kind": found.kind.value,
        "track": found.track.value,
        "status": found.status.value,
        "schedule": _schedule_value(found.schedule),
        "levels": _levels_value(found),
        "attempts": attempts,
    }


def _levels_value(found: ProblemHistory) -> JsonValue:
    if found.levels is None:
        return None
    languages: list[JsonValue] = [
        _mastery_value(language, mastery) for language, mastery in found.masteries
    ]
    return {"last": found.levels, "mastered": found.mastered, "languages": languages}


def _mastery_value(language: Language, mastery: LevelMastery) -> JsonValue:
    return {
        "language": language.value,
        "best": mastery.best,
        "last_time": mastery.last_time,
        "try_level": mastery.try_level,
    }


def _best(found: ProblemHistory) -> str:
    """`python through level 2 of 4 · kotlin through level 4 of 4`: each language passed."""
    return " · ".join(
        f"{language} {mastery.best_text}"
        for language, mastery in found.masteries
        if mastery.best_text is not None
    )


def _header(found: ProblemHistory) -> str:
    """The primary pattern, or the track of a problem without patterns and of an item."""
    topic = found.patterns[0] if found.patterns else found.track.value
    mastered = None if found.levels is None else (found.mastered, found.levels)
    return " · ".join((found.slug, found.difficulty, topic, status_text(found.status, mastered)))


def _review(found: ProblemHistory) -> str:
    entry = found.schedule
    if entry is None:
        return NOT_SCHEDULED
    state = entry.state
    when = _how_far((entry.due_on - found.today).days)
    return (
        f"due {entry.due_on.isoformat()} ({when}) · interval {state.interval_days}d · "
        f"ease {state.ease:.2f} · reps {state.reps} · lapses {state.lapses}"
    )


def _how_far(days: int) -> str:
    if days == 0:
        return "today"
    count = f"{abs(days)} day" if abs(days) == 1 else f"{abs(days)} days"
    return f"in {count}" if days > 0 else f"{count} ago"


def _rows(found: ProblemHistory) -> Iterator[str]:
    """The column header, then one row per attempt."""
    counts_submissions = found.kind is EntryKind.PROJECT
    table = [_HEADER, *(_cells(past, counts_submissions) for past in found.attempts)]
    widths = [max(len(row[column]) for row in table) for column in range(len(_HEADER))]
    for cells in table:
        cells_and_widths = zip(cells[:-1], widths[:-1], strict=True)
        padded = (cell.ljust(width + COLUMN_GAP) for cell, width in cells_and_widths)
        yield "".join(padded) + cells[-1]


def _cells(past: PastAttempt, counts_submissions: bool) -> tuple[str, ...]:
    attempt = past.attempt
    runs = past.submissions if counts_submissions else past.test_runs
    return (
        str(attempt.id),
        attempt.language or NO_VALUE,
        attempt.mode,
        _status(past),
        _local_minute(attempt.started_at),
        _solve_time(attempt),
        attempt.rating or NO_VALUE,
        _grade(attempt),
        str(attempt.hints_used),
        str(len(runs)),
        past.bench_runs[-1].verdict if past.bench_runs else NO_VALUE,
    )


def _status(past: PastAttempt) -> str:
    """`passed through level 2 of 4` for a pass below the last level."""
    attempt = past.attempt
    levels = past.levels
    if attempt.status is AttemptStatus.PASSED and levels is not None and levels.partial:
        return f"{attempt.status} {levels.text}"
    return attempt.status


def _solve_time(attempt: Attempt) -> str:
    solved_at = _solved_at(attempt)
    return NO_VALUE if solved_at is None else solve_time_text(attempt.solve_time(solved_at))


def _grade(attempt: Attempt) -> str:
    """`again`, with `solution` after it once the attempt revealed the solution."""
    marks = [_grade_name(attempt.grade)] if attempt.grade is not None else []
    if attempt.solution_revealed:
        marks.append(SOLUTION_MARK)
    return " ".join(marks) or NO_VALUE


def _local_minute(instant: datetime) -> str:
    return instant.astimezone().strftime(LOCAL_MINUTE)


def _schedule_value(entry: ScheduleEntry | None) -> JsonValue:
    if entry is None:
        return None
    state = entry.state
    return {
        "due_on": entry.due_on.isoformat(),
        "interval_days": state.interval_days,
        "ease": state.ease,
        "reps": state.reps,
        "lapses": state.lapses,
        "last_grade": _grade_name(entry.last_grade),
    }


def _attempt_value(past: PastAttempt) -> JsonValue:
    attempt = past.attempt
    test_runs: list[JsonValue] = [_test_run_value(run) for run in past.test_runs]
    submissions: list[JsonValue] = [_submission_value(found) for found in past.submissions]
    bench_runs: list[JsonValue] = [_bench_run_value(run) for run in past.bench_runs]
    return {
        "attempt_id": attempt.id,
        "language": attempt.language.value if attempt.language else None,
        "mode": attempt.mode.value,
        "status": attempt.status.value,
        "started_at": attempt.started_at.isoformat(),
        "ended_at": attempt.ended_at.isoformat() if attempt.ended_at else None,
        "solve_s": _solve_seconds(attempt),
        "rating": attempt.rating.value if attempt.rating else None,
        "grade": _grade_name(attempt.grade) if attempt.grade is not None else None,
        "hints_used": attempt.hints_used,
        "solution_revealed": attempt.solution_revealed,
        "time_limit_s": attempt.time_limit_s,
        "level_unlocked": attempt.level_unlocked,
        "levels_finished": past.levels_finished,
        "levels_passed": past.levels.passed if past.levels else None,
        "levels_total": past.levels.last if past.levels else None,
        "test_runs": test_runs,
        "submissions": submissions,
        "bench_runs": bench_runs,
    }


def _solve_seconds(attempt: Attempt) -> int | None:
    solved_at = _solved_at(attempt)
    return None if solved_at is None else int(attempt.solve_time(solved_at).total_seconds())


def _solved_at(attempt: Attempt) -> datetime | None:
    """When the solve time ends: None while in progress and once abandoned."""
    return None if attempt.status in UNTIMED else attempt.ended_at


def _grade_name(grade: Grade) -> str:
    return grade.name.lower()


def _test_run_value(run: RunRecord) -> JsonValue:
    tally = run.tally
    return {
        "ran_at": run.ran_at.isoformat(),
        "total": tally.total,
        "passed": tally.passed,
        "failed": tally.failed,
        "errored": tally.errored,
        "timed_out": tally.timed_out,
        "tle": tally.tle,
        "time_limit": run.time_limit,
        "duration_ms": run.duration_ms,
    }


def _submission_value(submission: SubmissionRecord) -> JsonValue:
    levels: list[JsonValue] = [level_tally_value(tally) for tally in submission.levels]
    return {
        "submitted_at": submission.submitted_at.isoformat(),
        "graded_up_to": submission.graded_up_to,
        "every_level": submission.every_level,
        "levels": levels,
        "total": submission.tally.total,
        "passed": submission.tally.passed,
        "duration_ms": submission.duration_ms,
    }


def _bench_run_value(run: BenchRunSummary) -> JsonValue:
    return {
        "ran_at": run.ran_at.isoformat(),
        "verdict": run.verdict.value,
        "confidence": run.confidence.value,
        "ratio": run.ratio,
        "reference_id": run.reference_id,
    }
