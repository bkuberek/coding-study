"""`cstudy status` (docs/specs/cli.md#cstudy-status).

Times show in local time, and ages relative to the run of the command; a mock attempt's tallies
count hidden cases but never name one. The lines a kind has no value for are left out. A
project's `files` line counts the folder's changes against the starter; `--json` adds every
file's origin and state.
"""

import json
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.attempt_status import (
    AttemptStanding,
    HintCount,
    ProjectStanding,
    attempt_status,
)
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.domain.cases import JsonValue
from coding_study.domain.items import EntryKind
from coding_study.domain.levels import LevelProgress
from coding_study.domain.service_project import MockScenarios
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
REVEALED = "revealed"
REVEALED_AND_GRADED = "revealed, graded as again"
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
    """Show where an attempt stands."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    found = attempt_status(environment, target.slug, target.language)
    if as_json:
        typer.echo(json.dumps(status_document(found), indent=2))
        return
    output = console(context)
    output.print(Text(_header(found), style="bold"))
    for label, value in _lines(found):
        line = Text(label.ljust(LABEL_WIDTH), style="dim")
        line.append(value)
        output.print(line)


def status_document(found: AttemptStanding) -> dict[str, JsonValue]:
    attempt = found.attempt
    project = found.project
    latest = project.latest_submission if project else None
    run = found.last_test_run
    return {
        "slug": attempt.slug,
        "kind": found.kind.value,
        "track": found.track.value,
        "language": attempt.language.value if attempt.language else None,
        "attempt_id": attempt.id,
        "mode": attempt.mode.value,
        "started_at": attempt.started_at.isoformat(),
        "file": found.file,
        "hints": _hints_value(found.hints),
        "solution_revealed": attempt.solution_revealed,
        "statement": found.statement,
        "levels": _levels_value(found),
        "timer": timer_value(attempt, found.now),
        "last_test_run": (
            {
                "ran_at": run.ran_at.isoformat(),
                "total": run.tally.total,
                "passed": run.tally.passed,
                "predates_level": found.test_run_predates_level,
            }
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
            for tally in (project.best_per_level if project else ())
        ],
        "files": _files_value(project) if project else None,
        "no_code_intelligence": found.no_code_intelligence,
        "service": _service_value(found.service),
        "next": found.next_step,
    }


def _service_value(mocks: tuple[MockScenarios, ...] | None) -> JsonValue:
    if mocks is None:
        return None
    return {"mocks": [{"name": mock.name, "scenarios": list(mock.scenarios)} for mock in mocks]}


def _hints_value(hints: HintCount) -> JsonValue:
    return {
        "used": hints.used,
        "total": hints.total,
        "locked_until_level": hints.locked_until_level,
    }


def _levels_value(found: AttemptStanding) -> JsonValue:
    """A progressive problem's openings are not stored, so only a project lists them."""
    levels = found.levels
    if levels is None:
        return None
    opened_at: list[JsonValue] = (
        [_instant(level.opened_at) for level in found.opened] if found.project is not None else []
    )
    titles: list[JsonValue] = [level.title for level in found.opened]
    return {
        "unlocked": levels.unlocked,
        "last": levels.last,
        "titles": titles,
        "opened_at": opened_at,
    }


def _header(found: AttemptStanding) -> str:
    """An item has no language, and its track stands for its kind."""
    attempt = found.attempt
    kind = found.track.value if found.kind is EntryKind.ITEM else found.kind.value
    parts = (attempt.slug, attempt.language, kind, f"attempt {attempt.id}", attempt.mode)
    return " · ".join(part for part in parts if part)


def _lines(found: AttemptStanding) -> Iterator[tuple[str, str]]:
    if found.file is not None:
        yield "file", found.file
    if found.levels is not None:
        yield "level", _level(found.levels, found)
    attempt = found.attempt
    if attempt.time_limit_s is not None:
        elapsed = attempt.solve_time(found.now)
        limit = timedelta(seconds=attempt.time_limit_s)
        yield "timer", f"{clock_text(elapsed)} / {clock_text(limit)}"
    if found.hints.total:
        yield "hints", _hints(found.hints)
    if attempt.solution_revealed:
        yield "solution", REVEALED if found.kind is EntryKind.ITEM else REVEALED_AND_GRADED
    if found.kind is not EntryKind.ITEM:
        yield "tested", _tested(found)
    if found.project is not None:
        yield from _project_lines(found.project, found.now)
    yield "next", found.next_step


def _level(levels: LevelProgress, found: AttemptStanding) -> str:
    """The unlocked level, of the last, with its title; when it opened, if recorded."""
    current = found.opened[-1]
    level = f"{levels.unlocked} of {levels.last}: {current.title}"
    if current.opened_at is not None:
        level += f" (opened {_local_time(current.opened_at, found.now)})"
    return level


def _hints(hints: HintCount) -> str:
    text = f"{hints.used} of {hints.total}"
    locked = hints.locked_until_level
    return text if locked is None else f"{text}, next opens with level {locked}"


def _project_lines(project: ProjectStanding, now: datetime) -> Iterator[tuple[str, str]]:
    yield "submitted", _submitted(project, now)
    changes = project.starter_changes
    counts = f"{len(changes.changed)} changed, {len(changes.added)} added"
    yield "files", f"{counts}, {len(changes.removed)} removed against the starter"


def _files_value(project: ProjectStanding) -> dict[str, JsonValue]:
    changes = project.starter_changes
    entries: list[JsonValue] = [
        {
            "path": file.path,
            "origin": file.origin.value,
            "level": file.level,
            "state": file.state.value,
        }
        for file in project.files
    ]
    return {
        "changed": list(changes.changed),
        "added": list(changes.added),
        "removed": list(changes.removed),
        "entries": entries,
    }


def _tested(found: AttemptStanding) -> str:
    run = found.last_test_run
    if run is None:
        return NOT_YET
    text = f"{run.tally.passed}/{run.tally.total} passed, {_ago(found.now - run.ran_at)}"
    level = found.test_run_predates_level
    return f"{text}, before level {level} opened" if level is not None else text


def _submitted(project: ProjectStanding, now: datetime) -> str:
    latest = project.latest_submission
    if latest is None:
        return NOT_YET
    text = f"{_tallies(latest.levels)}, {_ago(now - latest.submitted_at)}"
    better = _better(latest, project.best_per_level)
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
