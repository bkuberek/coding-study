"""`cstudy mock` (docs/specs/cli.md#cstudy-mock)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.mock_interview import (
    DEFAULT_COUNT,
    DEFAULT_MINUTES,
    MockProblem,
    MockRequest,
    MockSession,
    start_mock,
)
from coding_study.domain.problem import Language, Track
from coding_study.entrypoints.commands.next_problem import pick_summary
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "mock"
LABEL_WIDTH = 11
INDENT = "   "
NOTHING_TO_PICK = "no new medium or hard problems in scope"
LOCKED = "cstudy hint and cstudy solution, until the timer ends or every problem is done"


def register(app: typer.Typer) -> None:
    add_command(app, mock, NAME)


def mock(
    context: typer.Context,
    minutes: Annotated[
        int, typer.Option("--minutes", min=1, help="The shared timer, in minutes.")
    ] = DEFAULT_MINUTES,
    count: Annotated[
        int, typer.Option("--count", min=1, help="How many problems.")
    ] = DEFAULT_COUNT,
    tracks: Annotated[
        list[Track] | None,
        typer.Option("--track", help="Only this track (repeatable); default: config next.tracks."),
    ] = None,
    language: Annotated[
        Language | None, typer.Option("--lang", help="Language; default: config default_lang.")
    ] = None,
) -> None:
    """Timed mock interview."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    session = start_mock(environment, MockRequest(minutes, count, tuple(tracks or ()), language))
    output = console(context)
    if not session.problems:
        output.print(NOTHING_TO_PICK)
        return
    for line in _report(session):
        output.print(line)
    if environment.config.open_on_start:
        files = [path for problem in session.problems for path in _files(problem)]
        refused = environment.editor.open([environment.workspace.absolute(path) for path in files])
        if refused is not None:
            output.print(_line("editor", refused))


def _report(session: MockSession) -> Iterator[Text]:
    yield Text(_header(session), style="bold")
    for number, problem in enumerate(session.problems, start=1):
        yield Text(f"{number}  {pick_summary(problem.pick)}")
        user_label, statement_label = (
            ("stub", "statement") if problem.pick.candidate.autograded else ("notes", "prompt")
        )
        yield _line(user_label, problem.user_file, INDENT)
        yield _line(statement_label, problem.statement, INDENT)
    yield _line("locked", LOCKED)
    yield _line("next", _next_step(session.problems[0]))


def _header(session: MockSession) -> str:
    started, wanted = len(session.problems), session.request.count
    noun = "problem" if wanted == 1 else "problems"
    problems = f"{started} {noun}" if started == wanted else f"{started} of {wanted} {noun}"
    parts = ["mock interview", problems, f"{session.request.minutes} min shared timer"]
    if any(problem.pick.candidate.autograded for problem in session.problems):
        parts.append(session.language)
    return " · ".join(parts)


def _next_step(first: MockProblem) -> str:
    slug = first.pick.candidate.slug
    if first.pick.candidate.autograded:
        return f"cstudy test {slug} --watch"
    return f"answer in the notes, then cstudy done {slug} --rating easy|ok|hard"


def _files(problem: MockProblem) -> tuple[str, str]:
    return problem.user_file, problem.statement


def _line(label: str, value: str, indent: str = "") -> Text:
    line = Text(indent + label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
