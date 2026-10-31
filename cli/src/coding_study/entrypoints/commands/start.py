"""`cstudy start` (docs/specs/cli.md#cstudy-start)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.environment import Environment
from coding_study.application.practice_catalog import is_item
from coding_study.application.project_start import StartedProject
from coding_study.application.resolve_target import ProblemTarget, resolve_problem
from coding_study.application.start_attempt import StartedAttempt, StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import parse_timer
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from coding_study.entrypoints.shared import (
    PROBLEM_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "start"
LABEL_WIDTH = 11
NEXT_STEP = "cstudy test --watch"
PROJECT_NEXT_STEP = "cstudy test --watch, then cstudy submit"
PROJECT_KIND = "project"

type OpenFiles = tuple[str, str]
"""The user's file (stub or notes), then the statement."""


def register(app: typer.Typer) -> None:
    add_command(app, start, NAME)


def start(
    context: typer.Context,
    slug: Annotated[str, typer.Argument(help=PROBLEM_TARGET_HELP)],
    language: Annotated[
        Language | None, typer.Option("--lang", help="Language; default: config default_lang.")
    ] = None,
    fresh: Annotated[
        bool, typer.Option("--fresh", help="Archive the existing file and write a new stub.")
    ] = False,
    timer: Annotated[
        str | None,
        typer.Option("--timer", metavar="DURATION", help="Time box, for example 25m or 1h."),
    ] = None,
    no_open: Annotated[bool, typer.Option("--no-open", help="Do not launch the editor.")] = False,
) -> None:
    """Create or reopen a stub, open the statement, begin an attempt."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_problem(environment, ProblemTarget(slug, language), Path.cwd())
    request = StartRequest(target.slug, target.language, fresh, _timer_seconds(timer))
    output = console(context)
    files = start_and_report(output, environment, request)
    if not no_open and environment.config.open_on_start:
        open_in_editor(output, environment, files)


def start_and_report(output: Console, environment: Environment, request: StartRequest) -> OpenFiles:
    """Starts the problem or item `request` names and prints the report; returns its two files."""
    if is_item(environment, request.slug):
        lines, files = _start_item(environment, request)
    else:
        started = start_attempt(environment, request)
        lines, files = _report(started), (started.stub_path, started.statement_path)
    for line in lines:
        output.print(line)
    return files


def open_in_editor(output: Console, environment: Environment, files: OpenFiles) -> None:
    """Opens the user's file and the statement; says why when no editor could run."""
    problem = environment.editor.open([environment.workspace.absolute(path) for path in files])
    if problem is not None:
        output.print(_line("editor", problem))


def _timer_seconds(timer: str | None) -> int | None:
    if timer is None:
        return None
    try:
        return parse_timer(timer)
    except ValueError as error:
        raise UsageError(str(error)) from None


def _report(started: StartedAttempt) -> Iterator[Text]:
    meta = started.problem.meta
    topic = meta.patterns[0] if meta.patterns else meta.track
    header = [meta.slug, meta.difficulty, topic, started.attempt.language or ""]
    project = started.project
    if project is None:
        yield Text(" · ".join(header), style="bold")
        yield _line("stub", started.stub_path)
    else:
        yield Text(" · ".join((*header, PROJECT_KIND)), style="bold")
        yield from _project_lines(project)
    yield _line("statement", started.statement_path)
    levels = started.levels
    if levels is not None:
        unlocked = levels.unlocked
        yield _line("level", f"{unlocked} of {levels.last}: {levels.title(unlocked)}")
    if started.resumed:
        yield _line("attempt", "resumed")
    if started.archived_to:
        yield _line("archived", started.archived_to)
    yield _line("next", NEXT_STEP if project is None else PROJECT_NEXT_STEP)


def _project_lines(project: StartedProject) -> Iterator[Text]:
    """`project`, `entry` and `tests` lines in place of the stub."""
    files = f"{project.files} {'file' if project.files == 1 else 'files'}"
    yield _line("project", f"{project.folder} ({files})")
    yield _line("entry", f"{project.entry_file}: {project.entry_class}")
    tests = project.tests
    count = f"{tests.tests} {'test' if tests.tests == 1 else 'tests'}"
    yield _line("tests", f"{tests.path} ({count})")


def _start_item(environment: Environment, request: StartRequest) -> tuple[list[Text], OpenFiles]:
    """Non-autograded items: the answer goes in a notes file, so there is no language."""
    if request.language is not None:
        raise UsageError(f"{request.slug} is not autograded; --lang applies to problems")
    item_request = ItemStartRequest(request.slug, request.fresh, request.timer_s)
    started = start_item_attempt(environment, item_request)
    meta = started.meta
    header = (meta.slug, meta.difficulty, meta.track, f"{meta.estimate_minutes} min")
    lines = [Text(" · ".join(header), style="bold")]
    lines += [_line("notes", started.notes_path), _line("prompt", started.statement_path)]
    lines += [_line("guide", guide.target) for guide in started.guides]
    if started.resumed:
        lines.append(_line("attempt", "resumed"))
    if started.archived_to:
        lines.append(_line("archived", started.archived_to))
    lines.append(_line("next", f"answer in the notes, then cstudy solution {meta.slug}"))
    return lines, (started.notes_path, started.statement_path)


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
