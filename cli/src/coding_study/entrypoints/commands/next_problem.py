"""`cstudy next` (docs/specs/cli.md#cstudy-next)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.next_problem import NextRequest, next_problem
from coding_study.application.start_attempt import StartRequest
from coding_study.domain.errors import UsageError
from coding_study.domain.next_selection import NewPick, NextPick, NextSource, ReviewPick
from coding_study.domain.precedence import resolve_language
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.entrypoints.commands.start import open_in_editor, start_and_report
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "next"
LABEL_WIDTH = 8
NOTHING_TO_PICK = "nothing due and no new problems in scope"


def register(app: typer.Typer) -> None:
    add_command(app, next_command, NAME)


def next_command(
    context: typer.Context,
    tracks: Annotated[
        list[Track] | None,
        typer.Option("--track", help="Only this track (repeatable); default: config next.tracks."),
    ] = None,
    pattern: Annotated[
        str | None, typer.Option("--pattern", help="Problems that list this pattern.")
    ] = None,
    difficulty: Annotated[
        Difficulty | None, typer.Option("--difficulty", help="Only this difficulty.")
    ] = None,
    language: Annotated[
        Language | None,
        typer.Option("--lang", help="Problems available in it; the language for cstudy start."),
    ] = None,
    new: Annotated[bool, typer.Option("--new", help="Skip reviews.")] = False,
    review: Annotated[bool, typer.Option("--review", help="Skip new problems.")] = False,
    start: Annotated[bool, typer.Option("--start", help="Run cstudy start on the pick.")] = False,
) -> None:
    """Pick what to practice."""
    request = NextRequest(tuple(tracks or ()), pattern, difficulty, language, _source(new, review))
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    picked = next_problem(environment, request)
    output = console(context)
    if picked is None:
        output.print(NOTHING_TO_PICK)
        return
    output.print(_pick_line(picked))
    candidate = picked.candidate
    start_language = (
        resolve_language(language, environment.config) if candidate.autograded else None
    )
    if not start:
        output.print(_line("start", _start_command(candidate.slug, start_language)))
        return
    files = start_and_report(output, environment, StartRequest(candidate.slug, start_language))
    if environment.config.open_on_start:
        open_in_editor(output, environment, files)


def _source(new: bool, review: bool) -> NextSource:
    if new and review:
        raise UsageError("--new and --review exclude each other")
    if new:
        return NextSource.NEW_ONLY
    return NextSource.REVIEWS_ONLY if review else NextSource.ANY


def _start_command(slug: str, language: Language | None) -> str:
    """Items take no `--lang`."""
    command = f"cstudy start {slug}"
    return command if language is None else f"{command} --lang {language}"


def _pick_line(picked: NextPick) -> Text:
    label = "review" if isinstance(picked, ReviewPick) else "new"
    return _line(label, pick_summary(picked))


def pick_summary(picked: NextPick) -> str:
    """`koko-eating-bananas  (medium · binary-search)  weakest pattern: binary-search (0.75)`."""
    candidate = picked.candidate
    topic = candidate.patterns[0] if candidate.patterns else candidate.track
    return f"{candidate.slug}  ({candidate.difficulty} · {topic})  {_reason(picked)}"


def _reason(picked: NextPick) -> str:
    match picked:
        case ReviewPick(overdue_days=0, interval_days=interval):
            return f"due today, interval {interval}d"
        case ReviewPick(overdue_days=overdue, interval_days=interval):
            return f"overdue {overdue}d, interval {interval}d"
        case NewPick(group=group, weakness=weakness):
            kind = "pattern" if group.pattern else "track"
            return f"weakest {kind}: {group.name} ({float(weakness):.2f})"


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
