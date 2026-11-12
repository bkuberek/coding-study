"""`cstudy learn` (docs/specs/cli.md#cstudy-learn): read the concept guides and follow the
learning paths (docs/specs/guides.md)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment, load_environment
from coding_study.application.environment import Environment
from coding_study.application.learn import (
    GuideEntry,
    GuidePage,
    LearnListing,
    MarkedRead,
    PathView,
    guide_page,
    learn_listing,
    mark_read,
    path_view,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.concept_guides import StepKind, StepProgress
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands.serve import run_server
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "learn"
LABEL_WIDTH = 10
SLUG_WIDTH = 28
LEVEL_WIDTH = 10
READ_WIDTH = 6
POSITION_WIDTH = 4
KIND_WIDTH = 9
STEP_WIDTH = 27
COLUMN_GAP = 2
TARGET_WIDTH = 9
STATUS_WIDTH = 16
NOT_READ = "-"
NO_TARGET = ""
WEB_HINT = "Read with rendered diagrams in the web UI: cstudy learn {slug} --open"
BOTH = "give a guide or --path, not both"
DONE_NEEDS_GUIDE = "--done needs a guide: cstudy learn <guide> --done"
OPEN_NEEDS_GUIDE = (
    "--open needs a guide or a path: cstudy learn <guide> --open, "
    "or cstudy learn --path <path> --open"
)
OPEN_PRINTS_NOTHING = "--open takes no --done or --json: it serves the page and opens it"
GUIDE_VIEW = "/guides/{slug}"
PATH_VIEW = "/paths/{slug}"
"""The Guides page's views of a guide and of a path (docs/specs/web-ui.md#guides-view)."""
FREE_PORT = 0


def register(app: typer.Typer) -> None:
    add_command(app, learn, NAME)


def learn(
    context: typer.Context,
    guide: Annotated[
        str | None, typer.Argument(help="The guide to read; default: list guides and paths.")
    ] = None,
    path: Annotated[
        str | None, typer.Option("--path", help="Show a path's steps and progress.")
    ] = None,
    done: Annotated[bool, typer.Option("--done", help="Mark the guide read.")] = False,
    open_page: Annotated[
        bool,
        typer.Option("--open", help="Serve the web UI and open the guide or the path there."),
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the text.")
    ] = False,
) -> None:
    """Read concept guides and follow learning paths."""
    if guide is not None and path is not None:
        raise UsageError(BOTH)
    if guide is None and done:
        raise UsageError(DONE_NEEDS_GUIDE)
    if open_page:
        _open(context, guide, path, done or as_json)
        return
    output = console(context)
    if guide is not None and done:
        environment = load_environment(Path.cwd(), command_environ(context), Path.home())
        _print_marked(output, mark_read(environment, guide), as_json)
        return
    environment = load_catalog_environment(Path.cwd(), command_environ(context), Path.home())
    if path is not None:
        _print_path(output, path_view(environment, path), as_json)
    elif guide is not None:
        _print_guide(output, guide_page(environment, guide), as_json)
    else:
        _print_listing(output, environment, learn_listing(environment), as_json)


def _open(context: typer.Context, guide: str | None, path: str | None, printing: bool) -> None:
    """`cstudy serve --open`, landing on the guide's or the path's view of the Guides page, once
    the guide or the path is found; `printing` is `--done` or `--json`, which it refuses."""
    if guide is None and path is None:
        raise UsageError(OPEN_NEEDS_GUIDE)
    if printing:
        raise UsageError(OPEN_PRINTS_NOTHING)
    environment = load_catalog_environment(Path.cwd(), command_environ(context), Path.home())
    if guide is not None:
        view = GUIDE_VIEW.format(slug=guide_page(environment, guide).entry.meta.slug)
    else:
        view = PATH_VIEW.format(slug=path_view(environment, path or "").path.slug)
    run_server(context, port=FREE_PORT, open_browser=True, view=view)


def _print_listing(
    output: Console, environment: Environment, listing: LearnListing, as_json: bool
) -> None:
    if as_json:
        typer.echo(json.dumps(listing_document(listing), indent=2))
        return
    if not listing.guides and not listing.paths:
        output.print(Text(f"no guides in {environment.content_root}"))
        return
    slugs = [entry.meta.slug for entry in listing.guides]
    slugs += [view.path.slug for view in listing.paths]
    slug_width = max(SLUG_WIDTH, *(len(slug) + COLUMN_GAP for slug in slugs))
    output.print(Text("GUIDES", style="bold"))
    header = f"{'SLUG'.ljust(slug_width)}{'LEVEL'.ljust(LEVEL_WIDTH)}{'READ'.ljust(READ_WIDTH)}"
    output.print(Text(f"{header}TITLE", style="bold"))
    for entry in listing.guides:
        read = "yes" if entry.read_at else NOT_READ
        output.print(
            Text(
                f"{entry.meta.slug.ljust(slug_width)}{entry.meta.level.ljust(LEVEL_WIDTH)}"
                f"{read.ljust(READ_WIDTH)}{entry.meta.title}"
            )
        )
    if listing.paths:
        output.print(Text(""))
        output.print(Text("PATHS", style="bold"))
        for view in listing.paths:
            counts = f"{view.done} of {view.total} done"
            output.print(Text(f"{view.path.slug.ljust(slug_width)}{counts:<16}{view.path.title}"))
        unfinished = next((view for view in listing.paths if view.next_step is not None), None)
        if unfinished is not None:
            output.print(_labelled("next", f"cstudy learn --path {unfinished.path.slug}"))
    if listing.guides:
        output.print(Text(WEB_HINT.format(slug="<guide>"), style="dim"))


def _print_guide(output: Console, page: GuidePage, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(guide_document(page), indent=2))
        return
    if output.is_terminal:
        output.print(Markdown(page.terminal_text), soft_wrap=False)
    else:
        output.print(Text(page.terminal_text), end="")
    output.print(Text(""))
    if page.examples_folder is not None:
        output.print(_labelled("examples", str(page.examples_folder)))
    slug = page.entry.meta.slug
    read_at = page.entry.read_at
    if read_at is None:
        output.print(_labelled("done", f"cstudy learn {slug} --done"))
    else:
        output.print(_labelled("read", read_at.date().isoformat()))
    output.print(Text(WEB_HINT.format(slug=slug), style="dim"))


def _print_marked(output: Console, marked: MarkedRead, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(marked_document(marked), indent=2))
    elif marked.already:
        output.print(Text(f"{marked.slug} was marked read on {marked.read_at.date().isoformat()}"))
    else:
        output.print(Text(f"marked {marked.slug} read"))


def _print_path(output: Console, view: PathView, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(path_document(view), indent=2))
        return
    output.print(Text(f"{view.path.slug}  {view.path.title}", style="bold"))
    output.print(Text(view.path.summary))
    output.print(Text(f"{view.done} of {view.total} done"))
    step_width = max(STEP_WIDTH, *(len(step.step.slug) + COLUMN_GAP for step in view.steps))
    header = (
        f"{'#'.ljust(POSITION_WIDTH)}{'KIND'.ljust(KIND_WIDTH)}{'STEP'.ljust(step_width)}"
        f"{'TARGET'.ljust(TARGET_WIDTH)}{'STATUS'.ljust(STATUS_WIDTH)}TITLE"
    )
    output.print(Text(header, style="bold"))
    for position, step in enumerate(view.steps, start=1):
        output.print(Text(_step_line(position, step, step_width)))
    if view.next_step is not None:
        output.print(_labelled("next", _command(view.next_step)))


def _step_line(position: int, step: StepProgress, step_width: int) -> str:
    target = f"level {step.step.level}" if step.step.level is not None else NO_TARGET
    return (
        f"{str(position).ljust(POSITION_WIDTH)}{step.step.kind.ljust(KIND_WIDTH)}"
        f"{step.step.slug.ljust(step_width)}{target.ljust(TARGET_WIDTH)}"
        f"{step.status.ljust(STATUS_WIDTH)}{step.title}"
    )


def _command(step: StepProgress) -> str:
    if step.step.kind is StepKind.GUIDE:
        return f"cstudy learn {step.step.slug}"
    return f"cstudy start {step.step.slug}"


def _labelled(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line


def listing_document(listing: LearnListing) -> dict[str, JsonValue]:
    return {
        "guides": [_guide_fields(entry) for entry in listing.guides],
        "paths": [
            {
                "slug": view.path.slug,
                "title": view.path.title,
                "summary": view.path.summary,
                "done": view.done,
                "total": view.total,
            }
            for view in listing.paths
        ],
    }


def guide_document(page: GuidePage) -> dict[str, JsonValue]:
    return {
        **_guide_fields(page.entry),
        "markdown": page.markdown,
        "examples": [str(example) for example in page.examples],
    }


def marked_document(marked: MarkedRead) -> dict[str, JsonValue]:
    return {"slug": marked.slug, "read_at": marked.read_at.isoformat(), "already": marked.already}


def path_document(view: PathView) -> dict[str, JsonValue]:
    steps = [_step_fields(position, step) for position, step in enumerate(view.steps, start=1)]
    following = next((fields for fields in steps if not fields["done"]), None)
    return {
        "slug": view.path.slug,
        "title": view.path.title,
        "summary": view.path.summary,
        "done": view.done,
        "total": view.total,
        "next": following,
        "steps": list[JsonValue](steps),
    }


def _guide_fields(entry: GuideEntry) -> dict[str, JsonValue]:
    meta = entry.meta
    return {
        "slug": meta.slug,
        "title": meta.title,
        "summary": meta.summary,
        "level": meta.level.value,
        "prerequisites": list(meta.prerequisites),
        "related": list(meta.related),
        "problems": list(meta.problems),
        "read": entry.read_at is not None,
        "read_at": None if entry.read_at is None else entry.read_at.isoformat(),
    }


def _step_fields(position: int, step: StepProgress) -> dict[str, JsonValue]:
    return {
        "position": position,
        "kind": step.step.kind.value,
        "slug": step.step.slug,
        "title": step.title,
        "level": step.step.level,
        "done": step.done,
        "status": step.status,
        "level_passed": step.level_passed,
    }
