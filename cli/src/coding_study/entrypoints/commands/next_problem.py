"""`cstudy next` (docs/specs/cli.md#cstudy-next)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.next_problem import (
    NextRequest,
    NothingToPick,
    Recommendation,
    next_source,
    recommend,
)
from coding_study.application.start_attempt import StartRequest
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.labels import LabelFilter
from coding_study.domain.next_selection import (
    NewPick,
    NextPick,
    OpenAttempt,
    ResumePick,
    ReviewPick,
)
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.taxonomy import Scope
from coding_study.entrypoints.commands.start import open_in_editor, start_and_report
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "next"
LABEL_WIDTH = 8
NOTHING_TO_PICK = "nothing due and no new problems in scope"
NOTHING_FOR_THE_JDK = "nothing to pick: "
"""Before the reason the selected JDK gives, when it left nothing to pick."""
REVIEW_PICK = "review"
NEW_PICK = "new"
RESUME_PICK = "resume"


def register(app: typer.Typer) -> None:
    add_command(app, next_command, NAME)


def next_command(
    context: typer.Context,
    tracks: Annotated[
        list[Track] | None,
        typer.Option(
            "--track",
            help="Only this track (repeatable); default: config next.tracks, or every track "
            "with --domain, --role or --scope.",
        ),
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
    domain: Annotated[
        str | None, typer.Option("--domain", help="Problems that list this domain.")
    ] = None,
    role: Annotated[
        str | None, typer.Option("--role", help="Problems that list this job role.")
    ] = None,
    scope: Annotated[
        Scope | None, typer.Option("--scope", help="Only this scope: function, project or system.")
    ] = None,
    new: Annotated[bool, typer.Option("--new", help="Skip reviews.")] = False,
    review: Annotated[bool, typer.Option("--review", help="Skip new problems.")] = False,
    start: Annotated[bool, typer.Option("--start", help="Run cstudy start on the pick.")] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the report.")
    ] = False,
) -> None:
    """Pick what to practice."""
    if as_json and start:
        raise UsageError("--json excludes --start")
    request = NextRequest(
        tuple(tracks or ()),
        pattern,
        difficulty,
        language,
        next_source(new, review),
        LabelFilter(domain, role, scope),
    )
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    recommendation = recommend(environment, request)
    if as_json:
        typer.echo(json.dumps(next_document(recommendation), indent=2))
        return
    output = console(context)
    if isinstance(recommendation, NothingToPick):
        output.print(nothing_message(recommendation))
        return
    output.print(_pick_line(recommendation.pick))
    slug = recommendation.pick.candidate.slug
    if not start:
        output.print(_line("start", _start_command(slug, recommendation.language)))
        if isinstance(recommendation.pick, ResumePick) and recommendation.pick.others:
            output.print(_line("also", _also_open(recommendation.pick.others)))
        return
    files = start_and_report(output, environment, StartRequest(slug, recommendation.language))
    if environment.config.open_on_start:
        open_in_editor(output, environment, files)


def nothing_message(nothing: NothingToPick) -> str:
    """Why there is no pick: the selected JDK's reason, else the scope's."""
    if nothing.jdk_reason is None:
        return NOTHING_TO_PICK
    return f"{NOTHING_FOR_THE_JDK}{nothing.jdk_reason}"


def next_document(recommendation: Recommendation | NothingToPick) -> dict[str, JsonValue]:
    """`cstudy next --json`."""
    if isinstance(recommendation, NothingToPick):
        return {"pick": None, "message": nothing_message(recommendation)}
    picked = recommendation.pick
    candidate = picked.candidate
    language = recommendation.language
    document: dict[str, JsonValue] = {
        "pick": _pick_label(picked),
        "slug": candidate.slug,
        "title": recommendation.title,
        "kind": recommendation.kind.value,
        "difficulty": candidate.difficulty.value,
        "group": candidate.group.name,
        "reason": pick_reason(picked),
        "language": language.value if language else None,
        "start": _start_command(candidate.slug, language),
    }
    if isinstance(picked, ResumePick):
        also_open: list[JsonValue] = [_open_value(other) for other in picked.others]
        document |= {"attempt_id": picked.attempt.attempt_id, "also_open": also_open}
    return document


def _open_value(attempt: OpenAttempt) -> JsonValue:
    return {
        "attempt_id": attempt.attempt_id,
        "slug": attempt.candidate.slug,
        "language": attempt.language.value if attempt.language else None,
    }


def _also_open(others: tuple[OpenAttempt, ...]) -> str:
    """`two-sum (python) · url-shortener`: the other attempts in progress."""
    return " · ".join(
        f"{other.candidate.slug} ({other.language})" if other.language else other.candidate.slug
        for other in others
    )


def _start_command(slug: str, language: Language | None) -> str:
    """Items take no `--lang`."""
    command = f"cstudy start {slug}"
    return command if language is None else f"{command} --lang {language}"


def _pick_line(picked: NextPick | ResumePick) -> Text:
    return _line(_pick_label(picked), pick_summary(picked))


def _pick_label(picked: NextPick | ResumePick) -> str:
    match picked:
        case ResumePick():
            return RESUME_PICK
        case ReviewPick():
            return REVIEW_PICK
        case NewPick():
            return NEW_PICK


def pick_summary(picked: NextPick | ResumePick) -> str:
    """`koko-eating-bananas  (medium · binary-search)  weakest pattern: binary-search (0.75)`."""
    candidate = picked.candidate
    topic = candidate.patterns[0] if candidate.patterns else candidate.track
    return f"{candidate.slug}  ({candidate.difficulty} · {topic})  {pick_reason(picked)}"


def pick_reason(picked: NextPick | ResumePick) -> str:
    """The text after the parentheses: `overdue 3d, interval 7d`."""
    match picked:
        case ResumePick(attempt=OpenAttempt(attempt_id=number, language=language, used_on=used_on)):
            where = f" in {language}" if language else ""
            return f"attempt {number}{where}, last used {used_on.isoformat()}"
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
