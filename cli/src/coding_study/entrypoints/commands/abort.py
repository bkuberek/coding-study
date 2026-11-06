"""`cstudy abort` (docs/specs/cli.md#cstudy-abort): stop working on a problem, after a question."""

from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.run_activity import ProcessRunActivity
from coding_study.application.abort_attempt import abort_attempt
from coding_study.application.active_attempt import find_attempt
from coding_study.application.resolve_target import Target, resolve_target
from coding_study.domain.attempts import Attempt
from coding_study.entrypoints.commands.done import solve_time_text
from coding_study.entrypoints.shared import (
    OPTIONAL_TARGET_HELP,
    add_command,
    command_environ,
    console,
)

NAME = "abort"
LABEL_WIDTH = 8
NOT_ABORTED = "not aborted"


def register(app: typer.Typer) -> None:
    add_command(app, abort, NAME)


def abort(
    context: typer.Context,
    slug: Annotated[str | None, typer.Argument(help=OPTIONAL_TARGET_HELP)] = None,
    yes: Annotated[
        bool, typer.Option("--yes", help="Abort without asking: for a shell with no one to answer.")
    ] = False,
) -> None:
    """Stop working on a problem: the attempt ends as abandoned and your files stay."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_target(environment, Target(slug), Path.cwd())
    attempt = find_attempt(environment.progress, target.slug, target.language)
    output = console(context)
    if not yes and not typer.confirm(abort_question(attempt), default=False):
        output.print(NOT_ABORTED)
        return
    ended = abort_attempt(environment, attempt, ProcessRunActivity(environment.root))
    assert ended.ended_at is not None
    parts = (
        ended.slug,
        ended.language or "",
        ended.status,
        solve_time_text(ended.solve_time(ended.ended_at)),
    )
    output.print(Text(" · ".join(part for part in parts if part), style="bold"))
    if ended.stub_path:
        output.print(_line("kept", ended.stub_path))
    output.print(_line("next", f"cstudy start {ended.slug}"))


def abort_question(attempt: Attempt) -> str:
    """What `cstudy abort` and the page ask before they end `attempt`."""
    where = f"{attempt.slug} in {attempt.language}" if attempt.language else attempt.slug
    return (
        f"Abort {where}? The attempt ends as abandoned. "
        "Your files stay; progress and the review schedule do not change."
    )


def _line(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
