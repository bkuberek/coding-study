"""`cstudy solution` (docs/specs/cli.md#cstudy-solution)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.item_solution import ItemSolutionView, reveal_item_solution
from coding_study.application.practice_catalog import is_item
from coding_study.application.resolve_target import ProblemTarget, resolve_problem
from coding_study.application.reveal_solution import (
    ApproachSolution,
    BrokenSolution,
    SolutionRequest,
    SolutionView,
    attempt_to_mark,
    mark_revealed,
    show_solution,
)
from coding_study.domain.errors import UsageError
from coding_study.domain.items import REFERENCE_FILE
from coding_study.domain.problem import Language
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.entrypoints.shared import (
    PROBLEM_TARGET_HELP,
    add_command,
    command_environ,
    console,
    optional_value_command,
)

NAME = "solution"
REVEAL_QUESTION = "Reveal the solution? The attempt will be graded as again."
NOT_REVEALED = "not revealed"
LEXERS = {
    Language.PYTHON: "python",
    Language.TYPESCRIPT: "typescript",
    Language.JAVA: "java",
    Language.KOTLIN: "kotlin",
    Language.GO: "go",
    Language.RUST: "rust",
}


BROKEN_OPTION = "--broken"


def register(app: typer.Typer) -> None:
    """A bare `--broken` shows the first broken reference; `--broken=ID` picks one."""
    add_command(app, solution, NAME, optional_value_command(BROKEN_OPTION))


def solution(
    context: typer.Context,
    slug: Annotated[str, typer.Argument(help=PROBLEM_TARGET_HELP)],
    language: Annotated[
        Language | None, typer.Option("--lang", help="Language of the reference code.")
    ] = None,
    approach: Annotated[
        str | None, typer.Option("--approach", metavar="ID", help="This approach only.")
    ] = None,
    all_approaches: Annotated[
        bool, typer.Option("--all", help="Every approach, in ladder order.")
    ] = False,
    explanation_only: Annotated[
        bool, typer.Option("--explanation-only", help="Explanations without code.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Reveal without asking, even before a pass.")
    ] = False,
    broken: Annotated[
        str | None,
        typer.Option(
            BROKEN_OPTION,
            metavar="[=ID]",
            help="Concurrent problems: a deliberately broken reference, to spot the bug.",
        ),
    ] = None,
) -> None:
    """Show reference code with its explanation."""
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    target = resolve_problem(environment, ProblemTarget(slug, language), Path.cwd())
    request = SolutionRequest(
        target.slug, target.language, approach, all_approaches, explanation_only, broken
    )
    output = console(context)
    if is_item(environment, target.slug):
        _require_item_options(request)
        _page(output, list(_item_renderables(reveal_item_solution(environment, target.slug))))
        return
    view = show_solution(environment, request)
    attempt = attempt_to_mark(environment, target.slug)
    if attempt is not None:
        if not yes and not typer.confirm(REVEAL_QUESTION, default=False):
            output.print(NOT_REVEALED)
            return
        mark_revealed(environment, attempt)
    _show(output, view)


def _show(output: Console, view: SolutionView) -> None:
    _page(output, list(_renderables(view)))


def _page(output: Console, renderables: list[RenderableType]) -> None:
    """Through the pager on a terminal."""
    if not output.is_terminal:
        output.print(*renderables)
        return
    with output.pager(styles=True):
        output.print(*renderables)


def _renderables(view: SolutionView) -> Iterator[RenderableType]:
    yield Text(f"{view.meta.title} · {view.language}", style="bold")
    if view.rubric:
        yield Markdown(view.rubric)
    if view.overview:
        yield Markdown(view.overview)
    for part in view.approaches:
        yield from _approach(part, view.language)
    if view.broken is not None:
        yield from _broken(view.broken, view.language)


def _broken(part: BrokenSolution, language: Language) -> Iterator[RenderableType]:
    broken = part.broken
    yield Text(f"broken reference {broken.id}: {broken.bug}", style="bold yellow")
    if part.code is not None:
        yield Syntax(part.code, LEXERS[language], line_numbers=False)
    elif part.available:
        available = ", ".join(part.available)
        yield Text(f"no {language} file for {broken.id}; available: {available}", style="dim")
    if part.explanation:
        yield Text("")
        yield Markdown(part.explanation)


def _approach(part: ApproachSolution, language: Language) -> Iterator[RenderableType]:
    if part.explanation:
        yield Markdown(part.explanation)
    else:
        yield Text(f"{part.approach.id}: no explanation", style="dim")
    if part.code is not None:
        yield Text("")
        yield Syntax(part.code, LEXERS[language], line_numbers=False)
    elif part.available and language not in part.available:
        available = ", ".join(part.available)
        yield Text(f"no {language} reference; available: {available}", style="dim")


def _require_item_options(request: SolutionRequest) -> None:
    """Items have one rubric and one reference: no languages and no approaches."""
    has_problem_options = (
        request.language is not None
        or request.approach_id is not None
        or request.all_approaches
        or request.explanation_only
        or request.broken is not None
    )
    if has_problem_options:
        raise UsageError(
            f"{request.slug} is not autograded; "
            "--lang, --approach, --all and --explanation-only apply to problems"
        )


def _item_renderables(view: ItemSolutionView) -> Iterator[RenderableType]:
    yield Text(f"{view.meta.title} · {view.meta.track}", style="bold")
    for name, text in ((RUBRIC_FILE, view.rubric), (REFERENCE_FILE, view.reference)):
        yield Markdown(text) if text else Text(f"no {name}", style="dim")
