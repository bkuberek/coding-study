"""`cstudy stats` (docs/specs/cli.md#cstudy-stats)."""

import json
import math
from collections.abc import Iterator
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.show_stats import StatsRequest, StatsView, show_stats
from coding_study.domain.bench_verdict import Verdict
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.progress_stats import GroupStats, ProgressStats, StatsGrouping
from coding_study.entrypoints.commands.done import solve_time_text
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "stats"
COLUMN_GAP = "  "
LABEL_WIDTH = 10
NO_VALUE = "-"
JSON_DECIMALS = 4
PERCENT = 100
_COLUMNS = ("PROBLEMS", "ATTEMPTED", "PASSED", "MASTERED", "PASS RATE", "SOLVE TIME", "WEAKNESS")
_GROUP_HEADER = "GROUP"


def register(app: typer.Typer) -> None:
    add_command(app, stats, NAME)


def stats(
    context: typer.Context,
    by: Annotated[
        StatsGrouping,
        typer.Option(
            "--by", help="Group by pattern (as cstudy next does), track, lang or difficulty."
        ),
    ] = StatsGrouping.PATTERN,
    since: Annotated[
        str | None,
        typer.Option("--since", metavar="DATE", help="Only attempts since DATE (YYYY-MM-DD)."),
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output.")] = False,
) -> None:
    """Progress summary."""
    request = StatsRequest(by, _since(since))
    view = show_stats(load_environment(Path.cwd(), command_environ(context), Path.home()), request)
    if as_json:
        typer.echo(json.dumps(_document(view), indent=2))
        return
    output = console(context)
    for line in _lines(view):
        output.print(line)


def _since(text: str | None) -> date | None:
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise UsageError(f'invalid --since "{text}": use a date such as 2026-10-01') from None


def _lines(view: StatsView) -> Iterator[Text]:
    progress = view.stats
    if progress.groups:
        width = max(len(_GROUP_HEADER), *(len(group.name) for group in progress.groups))
        yield Text(_row(_GROUP_HEADER, _COLUMNS, width), style="bold")
        for group in progress.groups:
            yield Text(_row(group.name, _cells(group), width))
        yield Text("")
    yield _line("attempts", _attempts_text(view))
    yield _line("reviews", f"{progress.due_today} due today · {progress.overdue} overdue")
    yield _line("bench", _bench_text(progress))


def _row(name: str, cells: tuple[str, ...], width: int) -> str:
    aligned = (cell.rjust(len(column)) for cell, column in zip(cells, _COLUMNS, strict=True))
    return COLUMN_GAP.join((name.ljust(width), *aligned))


def _cells(group: GroupStats) -> tuple[str, ...]:
    rate = group.pass_rate
    solve = group.median_solve
    return (
        str(group.problems),
        str(group.attempted),
        str(group.passed),
        str(group.mastered),
        f"{_round_half_up(rate * PERCENT)}%" if rate is not None else NO_VALUE,
        solve_time_text(solve) if solve is not None else NO_VALUE,
        f"{float(group.weakness):.2f}",
    )


def _attempts_text(view: StatsView) -> str:
    progress, since = view.stats, view.query.since
    finished = f"{progress.finished} finished" + (f" since {since.isoformat()}" if since else "")
    days = "day" if progress.streak_days == 1 else "days"
    week = f"{progress.last_7_days} in the last 7 days"
    return " · ".join((finished, week, f"streak {progress.streak_days} {days}"))


def _bench_text(progress: ProgressStats) -> str:
    counts = (f"{progress.bench[verdict]} {verdict.value}" for verdict in Verdict)
    return " · ".join((f"{progress.benched} benched", *counts))


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line


def _round_half_up(value: Fraction) -> int:
    return math.floor(value + Fraction(1, 2))


def _document(view: StatsView) -> dict[str, JsonValue]:
    progress, query = view.stats, view.query
    return {
        "today": query.today.isoformat(),
        "by": query.grouping.value,
        "since": query.since.isoformat() if query.since else None,
        "groups": [_group_document(group) for group in progress.groups],
        "attempts": {
            "finished": progress.finished,
            "last_7_days": progress.last_7_days,
            "streak_days": progress.streak_days,
        },
        "reviews": {"due_today": progress.due_today, "overdue": progress.overdue},
        "bench": {verdict.value: progress.bench[verdict] for verdict in Verdict},
    }


def _group_document(group: GroupStats) -> dict[str, JsonValue]:
    rate = group.pass_rate
    solve = group.median_solve
    return {
        "group": group.name,
        "problems": group.problems,
        "attempted": group.attempted,
        "passed": group.passed,
        "mastered": group.mastered,
        "recent_attempts": group.recent_attempts,
        "recent_passed": group.recent_passed,
        "pass_rate": round(float(rate), JSON_DECIMALS) if rate is not None else None,
        "median_solve_s": round(solve.total_seconds()) if solve is not None else None,
        "weakness": round(float(group.weakness), JSON_DECIMALS),
    }
