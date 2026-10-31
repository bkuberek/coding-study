"""`cstudy status` (docs/specs/cli.md#cstudy-status).

Times show in local time, and ages relative to the run of the command; a mock attempt's tallies
count hidden cases but never name one. The `files` line counts the folder's changes against the
starter; `--json` adds every file's origin and state.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.project_status import ProjectStatus, project_status
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.domain.cases import JsonValue
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.entrypoints.commands.project_documents import level_tally_value
from coding_study.entrypoints.commands.report_text import clock_text
from coding_study.entrypoints.commands.run_document import timer_value
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "status"
LABEL_WIDTH = 11
NOT_YET = "not yet"
PROJECT_KIND = "project"
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


def register(app: typer.Typer) -> None:
    add_command(app, status, NAME)


def status(
    context: typer.Context,
    slug: Annotated[str | None, typer.Argument(help=OPTIONAL_TARGET_HELP)] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the report.")
    ] = False,
) -> None:
    """Show where a project attempt stands."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    found = project_status(environment, target.slug, target.language)
    if as_json:
        typer.echo(json.dumps(status_document(found), indent=2))
        return
    output = console(context)
    output.print(Text(_header(found), style="bold"))
    for label, value in _lines(found):
        line = Text(label.ljust(LABEL_WIDTH), style="dim")
        line.append(value)
        output.print(line)


def status_document(found: ProjectStatus) -> dict[str, JsonValue]:
    attempt = found.attempt
    latest = found.latest_submission
    run = found.last_test_run
    return {
        "slug": found.meta.slug,
        "language": attempt.language.value if attempt.language else None,
        "attempt_id": attempt.id,
        "mode": attempt.mode.value,
        "statement": found.statement,
        "levels": {
            "unlocked": found.levels.unlocked,
            "last": found.levels.last,
            "titles": [level.title for level in found.opened],
            "opened_at": [_instant(level.opened_at) for level in found.opened],
        },
        "timer": timer_value(attempt, found.now),
        "last_test_run": (
            {"ran_at": run.ran_at.isoformat(), "total": run.tally.total, "passed": run.tally.passed}
            if run
            else None
        ),
        "latest_submission": (
            {
                "submitted_at": latest.submitted_at.isoformat(),
                "level_tallies": [level_tally_value(tally) for tally in latest.levels],
            }
            if latest
            else None
        ),
        "best_per_level": [
            {"level": tally.level, "passed": tally.passed, "total": tally.total}
            for tally in found.best_per_level
        ],
        "files": _files_value(found),
        "next": found.next_step,
    }


def _header(found: ProjectStatus) -> str:
    attempt = found.attempt
    parts = (
        found.meta.slug,
        attempt.language or "",
        PROJECT_KIND,
        f"attempt {attempt.id}",
        attempt.mode,
    )
    return " · ".join(parts)


def _lines(found: ProjectStatus) -> list[tuple[str, str]]:
    levels = found.levels
    current = found.opened[-1]
    level = f"{levels.unlocked} of {levels.last}: {current.title}"
    if current.opened_at is not None:
        level += f" (opened {_local_time(current.opened_at, found.now)})"
    lines = [("level", level)]
    attempt = found.attempt
    if attempt.time_limit_s is not None:
        elapsed = attempt.solve_time(found.now)
        limit = timedelta(seconds=attempt.time_limit_s)
        lines.append(("timer", f"{clock_text(elapsed)} / {clock_text(limit)}"))
    run = found.last_test_run
    tested = (
        f"{run.tally.passed}/{run.tally.total} passed, {_ago(found.now - run.ran_at)}"
        if run
        else NOT_YET
    )
    lines.append(("tested", tested))
    lines.append(("submitted", _submitted(found)))
    changes = found.starter_changes
    counts = f"{len(changes.changed)} changed, {len(changes.added)} added"
    lines.append(("files", f"{counts}, {len(changes.removed)} removed against the starter"))
    lines.append(("next", found.next_step))
    return lines


def _files_value(found: ProjectStatus) -> dict[str, JsonValue]:
    changes = found.starter_changes
    entries: list[JsonValue] = [
        {
            "path": file.path,
            "origin": file.origin.value,
            "level": file.level,
            "state": file.state.value,
        }
        for file in found.files
    ]
    return {
        "changed": list(changes.changed),
        "added": list(changes.added),
        "removed": list(changes.removed),
        "entries": entries,
    }


def _submitted(found: ProjectStatus) -> str:
    latest = found.latest_submission
    if latest is None:
        return NOT_YET
    text = f"{_tallies(latest.levels)}, {_ago(found.now - latest.submitted_at)}"
    better = _better(latest, found.best_per_level)
    return f"{text} · best {_tallies(better)}" if better else text


def _better(latest: SubmissionRecord, best: tuple[LevelTally, ...]) -> tuple[LevelTally, ...]:
    """The levels an earlier submission passed more cases of, or that the latest did not grade."""
    passed = {tally.level: tally.passed for tally in latest.levels}
    return tuple(tally for tally in best if tally.passed > passed.get(tally.level, -1))


def _tallies(tallies: tuple[LevelTally, ...]) -> str:
    return " · ".join(f"level {tally.level} {tally.passed}/{tally.total}" for tally in tallies)


def _local_time(instant: datetime, now: datetime) -> str:
    """`18:02`, with the date when it is not today's."""
    local = instant.astimezone()
    same_day = local.date() == now.astimezone().date()
    return local.strftime("%H:%M" if same_day else "%Y-%m-%d %H:%M")


def _ago(age: timedelta) -> str:
    minutes = int(age.total_seconds()) // SECONDS_PER_MINUTE
    if minutes < 1:
        return "just now"
    if minutes < MINUTES_PER_HOUR:
        return f"{minutes} min ago"
    hours = minutes // MINUTES_PER_HOUR
    if hours < HOURS_PER_DAY:
        return f"{hours} h ago"
    days = hours // HOURS_PER_DAY
    return f"{days} day ago" if days == 1 else f"{days} days ago"


def _instant(instant: datetime | None) -> str | None:
    return instant.isoformat() if instant else None
