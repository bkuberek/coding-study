"""`cstudy set` (docs/specs/cli.md#cstudy-set): your own named lists of problems and items, in
`sets.yaml`, to study from without searching."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.environment import Environment
from coding_study.application.list_items import ListedItem
from coding_study.application.list_problems import ListedProblem, ListingContext, listing_context
from coding_study.application.problem_sets import (
    SetRow,
    SetView,
    add_to_set,
    create_set,
    delete_set,
    find_set,
    move_in_set,
    remove_from_set,
    rename_set,
    set_view,
    sets_with_standing,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem_sets import ProblemSet, SetStanding
from coding_study.entrypoints.commands.list_problems import (
    NO_VALUE,
    TABLE_HEADER,
    item_cells,
    item_entry,
    problem_cells,
    problem_entry,
    table_row,
)
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "set"
LABEL_WIDTH = 8
POSITION_WIDTH = 4
NAME_WIDTH = 24
COUNTS_WIDTH = 28
MISSING_STATUS = "missing"
NO_SETS = "no sets yet: create one with cstudy set create <name>"
NOT_DELETED = "not deleted"
_NAME_HELP = "The set, a kebab-case slug such as backend-loop."
_SLUGS_HELP = "Problems or items, by slug."


def register(app: typer.Typer) -> None:
    group = typer.Typer(help="Make named lists of problems to study from.", no_args_is_help=True)
    add_command(group, list_sets, "list")
    add_command(group, show, "show")
    add_command(group, create, "create")
    add_command(group, add, "add")
    add_command(group, remove, "remove")
    add_command(group, move, "move")
    add_command(group, rename, "rename")
    add_command(group, delete, "delete")
    app.add_typer(group, name=NAME)


def _environment(context: typer.Context) -> Environment:
    return load_environment(Path.cwd(), command_environ(context), Path.home())


def list_sets(
    context: typer.Context,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the lines.")
    ] = False,
) -> None:
    """List your sets, with passed of total."""
    environment = _environment(context)
    if as_json:
        typer.echo(json.dumps(sets_document(environment), indent=2))
        return
    found = sets_with_standing(environment)
    output = console(context)
    if not found:
        output.print(Text(NO_SETS))
    for problem_set, standing in found:
        output.print(Text(_set_line(problem_set, standing).rstrip()))


def show(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the table.")
    ] = False,
) -> None:
    """Show a set's rows, in its order."""
    environment = _environment(context)
    if as_json:
        typer.echo(json.dumps(set_document(environment, name), indent=2))
        return
    _print_view(console(context), set_view(environment, name))


def create(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    description: Annotated[
        str | None, typer.Option("--description", help="What the set is for.")
    ] = None,
) -> None:
    """Create an empty set."""
    created = create_set(_environment(context), name, description)
    output = console(context)
    output.print(Text(f"created {created.name}"))
    output.print(_labelled("next", f"cstudy set add {created.name} <slug>"))


def add(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    slugs: Annotated[list[str], typer.Argument(help=_SLUGS_HELP)],
    level: Annotated[
        int | None,
        typer.Option(
            "--level",
            min=1,
            help="Progressive and project problems: done in the set once a pass reaches this "
            "level; every level without it.",
        ),
    ] = None,
) -> None:
    """Add problems or items to the end of a set."""
    change = add_to_set(_environment(context), name, slugs, level)
    output = console(context)
    target = "" if level is None else f", {target_text(level)}"
    for slug in change.changed:
        output.print(Text(f"added {slug} to {name}{target}"))
    for slug in change.retargeted:
        output.print(Text(f"{slug} in {name} now targets level {level}"))
    for slug in change.unchanged:
        output.print(Text(f"{slug} is already in {name}"))


def target_text(level: int) -> str:
    """`through level 2 (target)`: what an entry is done at, as the Sets view says it."""
    return f"through level {level} (target)"


def remove(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    slugs: Annotated[list[str], typer.Argument(help=_SLUGS_HELP)],
) -> None:
    """Take problems or items out of a set."""
    change = remove_from_set(_environment(context), name, slugs)
    output = console(context)
    for slug in change.changed:
        output.print(Text(f"removed {slug} from {name}"))
    for slug in change.unchanged:
        output.print(Text(f"{slug} is not in {name}"))


def move(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    slug: Annotated[str, typer.Argument(help="The problem or item to move.")],
    position: Annotated[int, typer.Argument(help="Where it goes, from 1.")],
) -> None:
    """Move a problem or item within a set."""
    moved = move_in_set(_environment(context), name, slug, position)
    console(context).print(Text(f"moved {slug} to {position} of {len(moved.slugs)} in {name}"))


def rename(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    new_name: Annotated[str, typer.Argument(help="The new name.")],
) -> None:
    """Rename a set, keeping its rows."""
    rename_set(_environment(context), name, new_name)
    console(context).print(Text(f"renamed {name} to {new_name}"))


def delete(
    context: typer.Context,
    name: Annotated[str, typer.Argument(help=_NAME_HELP)],
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Delete without asking: for a shell with no one to answer."),
    ] = False,
) -> None:
    """Delete a set, after a question. Your progress stays."""
    environment = _environment(context)
    question = delete_question(find_set(environment, name))
    output = console(context)
    if not yes and not typer.confirm(question, default=False):
        output.print(NOT_DELETED)
        return
    delete_set(environment, name)
    output.print(Text(f"deleted {name}"))


def delete_question(problem_set: ProblemSet) -> str:
    """What `cstudy set delete` and the page ask first."""
    held = len(problem_set.slugs)
    return (
        f"Delete the set {problem_set.name}, with {held} {'entry' if held == 1 else 'entries'}? "
        "Your progress stays."
    )


def sets_document(environment: Environment) -> dict[str, JsonValue]:
    """`cstudy set list --json`."""
    sets: list[JsonValue] = [
        {
            **_set_value(problem_set, standing),
            "slugs": list(problem_set.slugs),
            "levels": dict(problem_set.levels),
        }
        for problem_set, standing in sets_with_standing(environment)
    ]
    return {"sets": sets}


def set_document(environment: Environment, name: str) -> dict[str, JsonValue]:
    """`cstudy set show --json`."""
    view = set_view(environment, name)
    listing = listing_context(environment)
    rows: list[JsonValue] = [_row_value(row, listing) for row in view.rows]
    return {
        **_set_value(view.problem_set, view.standing),
        "today": listing.today.isoformat(),
        "rows": rows,
    }


def _set_value(problem_set: ProblemSet, standing: SetStanding) -> dict[str, JsonValue]:
    missing: list[JsonValue] = list(standing.missing)
    return {
        "name": problem_set.name,
        "description": problem_set.description,
        "passed": standing.passed,
        "total": standing.total,
        "missing": missing,
    }


def _row_value(row: SetRow, listing: ListingContext) -> dict[str, JsonValue]:
    entry: JsonValue
    match row.listed:
        case ListedProblem() as problem:
            entry = problem_entry(problem, listing)
        case ListedItem() as item:
            entry = item_entry(item, listing)
        case None:
            entry = None
    return {
        "position": row.position,
        "slug": row.slug,
        "level": row.level,
        "passed": row.passed,
        "missing": row.listed is None,
        "entry": entry,
    }


def _counts(standing: SetStanding) -> str:
    """`1 of 3 passed · 1 missing`."""
    counts = f"{standing.passed} of {standing.total} passed"
    return f"{counts} · {len(standing.missing)} missing" if standing.missing else counts


def _set_line(problem_set: ProblemSet, standing: SetStanding) -> str:
    return (
        f"{problem_set.name.ljust(NAME_WIDTH)}  {_counts(standing).ljust(COUNTS_WIDTH)}"
        f"{problem_set.description or ''}"
    )


def _print_view(output: Console, view: SetView) -> None:
    problem_set = view.problem_set
    heading = "  ".join(part for part in (problem_set.name, problem_set.description) if part)
    output.print(Text(heading, style="bold"))
    output.print(Text(_counts(view.standing)))
    if view.rows:
        output.print(Text(_position("#") + table_row(TABLE_HEADER), style="bold"))
    for row in view.rows:
        output.print(Text(_position(str(row.position)) + table_row(_cells(row))))
        if row.level is not None:
            output.print(Text(f"{_position('')}target  through level {row.level}"))
    output.print(_labelled("next", f"cstudy next --set {problem_set.name}"))


def _position(text: str) -> str:
    return text.ljust(POSITION_WIDTH)


def _cells(row: SetRow) -> tuple[str, ...]:
    match row.listed:
        case ListedProblem() as problem:
            return problem_cells(problem)
        case ListedItem() as item:
            return item_cells(item)
        case None:
            return (NO_VALUE, row.slug, NO_VALUE, NO_VALUE, MISSING_STATUS, NO_VALUE, NO_VALUE)


def _labelled(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
