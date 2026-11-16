"""`cstudy mock` (docs/specs/cli.md#cstudy-mock)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
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
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Language, Track
from coding_study.domain.profile import (
    PICK_DIMENSIONS,
    Counted,
    ProfileLineKind,
    learner_profile,
    profile_line,
)
from coding_study.entrypoints.commands.list_problems import explicit_widening
from coding_study.entrypoints.commands.next_problem import (
    pick_summary,
    profile_nothing_message,
)
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "mock"
LABEL_WIDTH = 11
INDENT = "   "
NO_NEW_PROBLEMS = "no new medium or hard problems"
NOTHING_TO_PICK = f"{NO_NEW_PROBLEMS} in scope"
PICKED_FROM = "new medium and hard problems"
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
        Language | None,
        typer.Option("--lang", help="Only problems available in it, started in it."),
    ] = None,
    domain: Annotated[
        str | None, typer.Option("--domain", help="Problems that list this domain.")
    ] = None,
    role: Annotated[
        str | None, typer.Option("--role", help="Problems that list this job role.")
    ] = None,
    widen: Annotated[
        list[str] | None,
        typer.Option(
            "--widen",
            metavar="role|domain|all",
            help="Ignore your learner profile in this dimension for this run; repeatable.",
        ),
    ] = None,
) -> None:
    """Timed mock interview."""
    widening = explicit_widening(widen or (), language, role, domain, PICK_DIMENSIONS)
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    request = MockRequest(
        minutes,
        count,
        tuple(tracks or ()),
        language,
        LabelFilter(domain, role),
        learner_profile(environment.config.profile, environment.workspace_languages),
        widening,
    )
    session = start_mock(environment, request)
    output = console(context)
    if not session.problems:
        output.print(nothing_message(session))
        _print_profile_line(output, session)
        return
    for line in _report(session):
        output.print(line)
    if environment.config.open_on_start:
        files = [path for problem in session.problems for path in _files(problem)]
        refused = environment.editor.open([environment.workspace.absolute(path) for path in files])
        if refused is not None:
            output.print(_line("editor", refused))
    _print_profile_line(output, session)


def _print_profile_line(output: Console, session: MockSession) -> None:
    """The dim line that ends the report while the profile hid a problem from the picks' scope;
    the message says it instead when the profile is what left nothing."""
    if session.profile_left_nothing:
        return
    effect = session.profile
    counted = Counted(effect.shown, effect.total, PICKED_FROM)
    line = profile_line(ProfileLineKind.PICKS, [counted], effect.narrowed)
    if line is not None:
        output.print(Text(line, style="dim"))


def nothing_message(session: MockSession) -> str:
    """`NOTHING_TO_PICK`, with the selected JDK's reason when that left nothing; the profile's
    message when the profile did."""
    if session.jdk_reason is not None:
        return f"{NOTHING_TO_PICK}: {session.jdk_reason}"
    if session.profile_left_nothing:
        return profile_nothing_message(NO_NEW_PROBLEMS, "mock", session.profile)
    return NOTHING_TO_PICK


def _report(session: MockSession) -> Iterator[Text]:
    yield Text(_header(session), style="bold")
    for number, problem in enumerate(session.problems, start=1):
        yield Text(f"{number}  {pick_summary(problem.pick)}")
        user_label, statement_label = _labels(problem)
        yield _line(user_label, problem.user_file, INDENT)
        yield _line(statement_label, problem.statement, INDENT)
    yield _line("locked", LOCKED)
    yield _line("next", _next_step(session.problems[0]))


def _labels(problem: MockProblem) -> tuple[str, str]:
    """The user's file and the statement: a stub, a project folder, or the notes of a rubric
    problem."""
    if not problem.pick.candidate.autograded:
        return "notes", "prompt"
    return ("project" if problem.is_project else "stub"), "statement"


def _header(session: MockSession) -> str:
    started, wanted = len(session.problems), session.request.count
    noun = "problem" if wanted == 1 else "problems"
    problems = f"{started} {noun}" if started == wanted else f"{started} of {wanted} {noun}"
    parts = ["mock interview", problems, f"{session.request.minutes} min shared timer"]
    languages = _languages(session)
    if languages:
        parts.append(", ".join(languages))
    return " · ".join(parts)


def _languages(session: MockSession) -> tuple[Language, ...]:
    """The languages the problems started in, in the order of the first problem that used each."""
    started = (problem.language for problem in session.problems if problem.language is not None)
    return tuple(dict.fromkeys(started))


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
