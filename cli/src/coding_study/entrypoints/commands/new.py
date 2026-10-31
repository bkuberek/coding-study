"""`cstudy new` (docs/specs/cli.md#cstudy-new)."""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.problem_templates import PackagedProblemTemplates
from coding_study.application.new_problem import CreatedProblem, create_problem
from coding_study.domain.problem import Difficulty, Track
from coding_study.domain.scaffold import ScaffoldRequest, TemplateName
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "new"
STEP_INDENT = "     "
FIRST_STEP = 2
WORKFLOW = (
    (
        "Write problem.md: statement, input, output, constraints, in original wording",
        "cstudy verify {slug} --static",
    ),
    ("Set signature and comparator in meta.yaml", "cstudy verify {slug} --static"),
    (
        "Add visible examples to tests.json and their explanations in problem.md; "
        "add hidden edge cases",
        "cstudy verify {slug} --static",
    ),
    ("Write the brute-force approach in Python with oracle: true", "cstudy verify {slug}"),
    ("Write generator.py (and validate)", "cstudy verify {slug} --oracle"),
    (
        "Write the optimal approach(es): Python first, then TypeScript, Java, Kotlin",
        "cstudy verify {slug} --oracle",
    ),
    ("Write solutions/explanation.md, one section per approach", "cstudy verify {slug} --static"),
    (
        "Add the perf block and generate cases at the largest ladder size",
        "cstudy verify {slug} --ladder",
    ),
    ("Set status: ready", "cstudy verify {slug} --oracle --ladder --require-ready"),
)
"""docs/specs/authoring.md#workflow, from step 2; `cstudy new` is step 1."""
PROJECT_WORKFLOW = (
    (
        "Write problem.md, with ## Project and one ## Level section per level, and tests.json, "
        "with at least 2 visible and 2 hidden cases per level",
        "cstudy verify {slug} --static",
    ),
    (
        "Shape the starter: the entry class with level 1's methods, the seeded files, the build "
        "files, README.md",
        "cstudy verify {slug}",
    ),
    (
        "Write the reference overlay in solutions/<approach>/, level by level",
        "cstudy verify {slug}",
    ),
    (
        "Write solutions/explanation.md with ### Design; set status: ready",
        "cstudy verify {slug} --require-ready",
    ),
)
"""docs/specs/authoring.md#project-problems, from step 2: a project problem's own workflow."""
PROJECT_TEMPLATES = frozenset({TemplateName.PROJECT_PYTHON})
"""A project problem is written in its one language, so no languages need trimming."""
LANGUAGES_HINT = (
    "languages  meta.yaml lists the languages to write references in; remove the ones you "
    "do not practice, and their reference files"
)


def register(app: typer.Typer) -> None:
    add_command(app, new, NAME)


def new(
    context: typer.Context,
    slug: Annotated[str, typer.Argument(help="The new problem's slug, e.g. max-gap.")],
    track: Annotated[
        Track | None, typer.Option("--track", help="Track; default: the template's (dsa).")
    ] = None,
    template: Annotated[
        TemplateName, typer.Option("--from-template", help="Signature shape to start from.")
    ] = TemplateName.ARRAY,
    title: Annotated[
        str | None, typer.Option("--title", help="Title; default: from the slug.")
    ] = None,
    difficulty: Annotated[
        Difficulty | None, typer.Option("--difficulty", help="Difficulty; default: medium.")
    ] = None,
    pattern: Annotated[
        str | None, typer.Option("--pattern", help="Primary pattern; default: the template's.")
    ] = None,
) -> None:
    """Scaffold a new problem."""
    request = ScaffoldRequest(slug, template, track, title, difficulty, pattern)
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    created = create_problem(environment, PackagedProblemTemplates(), request)
    output = console(context)
    for line in _report(created):
        output.print(line)


def _report(created: CreatedProblem) -> Iterator[Text]:
    yield Text(f"created  {created.directory}  ({created.template} template, draft)", "bold")
    if created.template in PROJECT_TEMPLATES:
        yield Text("next steps (docs/specs/authoring.md#project-problems)")
        yield from _steps(PROJECT_WORKFLOW, created.slug)
        return
    yield Text(LANGUAGES_HINT)
    yield Text("next steps (docs/specs/authoring.md#workflow)")
    yield from _steps(WORKFLOW, created.slug)


def _steps(workflow: Iterable[tuple[str, str]], slug: str) -> Iterator[Text]:
    for number, (action, check) in enumerate(workflow, start=FIRST_STEP):
        yield Text(f"  {number}. {action}")
        yield Text(f"{STEP_INDENT}{check.format(slug=slug)}", "dim")
