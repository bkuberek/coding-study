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
    NO_SCOPE,
    GuideEntry,
    GuidePage,
    LabelScope,
    LearnListing,
    ListingFilter,
    MarkedRead,
    PathView,
    ProfiledListing,
    guide_page,
    label_scope,
    learn_listing,
    mark_read,
    path_view,
    profiled_listing,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.concept_guides import GuideLevel, GuideStatus, StepKind, StepProgress
from coding_study.domain.content_ids import ContentType, content_id
from coding_study.domain.errors import UsageError
from coding_study.domain.guide_examples import TAB_ORDER
from coding_study.domain.labels import LabelFilter
from coding_study.domain.profile import (
    WIDEN_ALL,
    WIDEN_DIMENSIONS,
    ProfileLineKind,
    Widening,
    profile_line,
    widening_from,
)
from coding_study.domain.taxonomy import DOMAINS, JOB_ROLES
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
NO_LEVEL = "-"
"""The level of a path without guides."""
NO_TARGET = ""
WEB_HINT = "Read with rendered diagrams in the web UI: cstudy learn {slug} --open"
BOTH = "give a guide or --path, not both"
DONE_NEEDS_GUIDE = "--done needs a guide: cstudy learn <guide> --done"
OPEN_NEEDS_GUIDE = (
    "--open needs a guide or a path: cstudy learn <guide> --open, "
    "or cstudy learn --path <path> --open"
)
OPEN_PRINTS_NOTHING = "--open takes no --done or --json: it serves the page and opens it"
FILTERS_NARROW_THE_LIST = (
    "--search, --level and --status narrow the list: cstudy learn --search <words>, "
    "without a guide or --path"
)
LABELS_APPLY_TO_THE_LIST = (
    "--domain, --role and --widen apply to the list: cstudy learn --domain <domain>, "
    "without a guide or --path"
)
WIDEN_VALUES = tuple(value for value in (*WIDEN_DIMENSIONS, WIDEN_ALL) if value != "lang")
"""A guide has no language, so `cstudy learn` widens roles, domains or all of them."""
LANG_PRINTS = (
    "--lang picks the language of a printed guide's examples: "
    "cstudy learn <guide> --lang <language>"
)
UNKNOWN_LANGUAGE = 'unknown language "{language}"; one of {languages}'
OTHER_LANGUAGES = "`cstudy learn {slug} --lang <language>`"
"""What follows an example's other languages: the command that shows one."""
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
    search: Annotated[
        str | None,
        typer.Option(
            "--search", help="List the guides and paths with every word in title, summary or slug."
        ),
    ] = None,
    level: Annotated[
        GuideLevel | None, typer.Option("--level", help="List the guides and paths at this level.")
    ] = None,
    status: Annotated[
        GuideStatus | None,
        typer.Option(
            "--status", help="List what is read, or not: a path once all its guides are read."
        ),
    ] = None,
    domain: Annotated[
        str | None, typer.Option("--domain", help="List the guides and paths on this domain.")
    ] = None,
    role: Annotated[
        str | None, typer.Option("--role", help="List the guides and paths for this job role.")
    ] = None,
    widen: Annotated[
        list[str] | None,
        typer.Option(
            "--widen",
            help="Drop the learner profile's roles or domains for this run: "
            f"{', '.join(WIDEN_VALUES)}. Repeatable.",
        ),
    ] = None,
    open_page: Annotated[
        bool,
        typer.Option("--open", help="Serve the web UI and open the guide or the path there."),
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the text.")
    ] = False,
    language: Annotated[
        str | None,
        typer.Option(
            "--lang",
            help="The language of the guide's examples, where they have it: "
            f"{', '.join(TAB_ORDER)}.",
        ),
    ] = None,
) -> None:
    """Read concept guides and follow learning paths."""
    if guide is not None and path is not None:
        raise UsageError(BOTH)
    if guide is None and done:
        raise UsageError(DONE_NEEDS_GUIDE)
    wanted = ListingFilter(search or "", level, status)
    labels = label_filter(domain, role)
    widening = learn_widening(widen or [])
    if guide is not None or path is not None:
        if wanted.narrows:
            raise UsageError(FILTERS_NARROW_THE_LIST)
        if labels.is_set or widen:
            raise UsageError(LABELS_APPLY_TO_THE_LIST)
    if language is not None:
        _check_language(language, guide is None or done or open_page or as_json)
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
        _print_guide(output, guide_page(environment, guide, language), as_json)
    else:
        scope = label_scope(environment, labels, widening)
        _print_listing(output, environment, learn_listing(environment), as_json, wanted, scope)


def label_filter(domain: str | None, role: str | None) -> LabelFilter:
    """`--domain` and `--role`, each a value of the closed lists of content.md#labels."""
    if domain is not None and domain not in DOMAINS:
        raise UsageError(f'unknown domain "{domain}"; use one of {", ".join(DOMAINS)}')
    if role is not None and role not in JOB_ROLES:
        raise UsageError(f'unknown job role "{role}"; use one of {", ".join(JOB_ROLES)}')
    return LabelFilter(domain, role)


def learn_widening(values: list[str]) -> Widening:
    """`--widen` values: `role`, `domain` or `all`; `lang` is the list command's."""
    for value in values:
        if value not in WIDEN_VALUES:
            raise UsageError(
                f'unknown widening "{value}"; cstudy learn takes {", ".join(WIDEN_VALUES)}'
            )
    return widening_from(values)


def _check_language(language: str, printing_no_guide: bool) -> None:
    """`--lang` takes a guide that is printed, and one of the example languages."""
    if printing_no_guide:
        raise UsageError(LANG_PRINTS)
    if language not in TAB_ORDER:
        languages = ", ".join(TAB_ORDER)
        raise UsageError(UNKNOWN_LANGUAGE.format(language=language, languages=languages))


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
    output: Console,
    environment: Environment,
    whole: LearnListing,
    as_json: bool,
    wanted: ListingFilter = ListingFilter(),  # noqa: B008 - frozen, so one shared default is safe
    scope: LabelScope = NO_SCOPE,
) -> None:
    profiled = profiled_listing(whole, wanted, scope)
    listing = profiled.listing
    if as_json:
        typer.echo(json.dumps(listing_document(listing, profiled), indent=2))
        return
    if not whole.guides and not whole.paths:
        output.print(Text(f"no guides in {environment.content_root}"))
        return
    slugs = [entry.meta.slug for entry in listing.guides]
    slugs += [view.path.slug for view in listing.paths]
    slug_width = max([SLUG_WIDTH, *(len(slug) + COLUMN_GAP for slug in slugs)])
    output.print(Text("GUIDES", style="bold"))
    if not listing.guides:
        output.print(Text(_no_match("guides", wanted)))
    else:
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
    if whole.paths:
        output.print(Text(""))
        output.print(Text("PATHS", style="bold"))
        if not listing.paths:
            output.print(Text(_no_match("paths", wanted)))
        for view in listing.paths:
            level = view.level or NO_LEVEL
            counts = f"{view.done} of {view.total} done"
            output.print(
                Text(
                    f"{view.path.slug.ljust(slug_width)}{level.ljust(LEVEL_WIDTH)}"
                    f"{counts:<16}{view.path.title}"
                )
            )
        unfinished = next((view for view in listing.paths if view.next_step is not None), None)
        if unfinished is not None:
            output.print(_labeled("next", f"cstudy learn --path {unfinished.path.slug}"))
    if listing.guides:
        output.print(Text(WEB_HINT.format(slug="<guide>"), style="dim"))
    line = profile_line(
        ProfileLineKind.SHOWS_THEM, (profiled.guides, profiled.paths), profiled.narrowed
    )
    if line is not None:
        output.print(Text(line, style="dim"))


def _no_match(noun: str, wanted: ListingFilter) -> str:
    """`no guides match "zebra", level: advanced`, as the Guides page says it."""
    asked = [f'"{wanted.search.strip()}"'] if wanted.search.strip() else []
    if wanted.level is not None:
        asked.append(f"level: {wanted.level}")
    if wanted.status is not None:
        asked.append(f"status: {wanted.status.replace('_', ' ')}")
    return f"no {noun} match {', '.join(asked)}" if asked else f"no {noun}"


def _print_guide(output: Console, page: GuidePage, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(guide_document(page), indent=2))
        return
    text = page.terminal_text(OTHER_LANGUAGES.format(slug=page.entry.meta.slug))
    if output.is_terminal:
        output.print(Markdown(text), soft_wrap=False)
    else:
        output.print(Text(text), end="")
    output.print(Text(""))
    if page.examples_folder is not None:
        output.print(_labeled("examples", str(page.examples_folder)))
    slug = page.entry.meta.slug
    read_at = page.entry.read_at
    if read_at is None:
        output.print(_labeled("done", f"cstudy learn {slug} --done"))
    else:
        output.print(_labeled("read", read_at.date().isoformat()))
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
        output.print(_labeled("next", _command(view.next_step)))


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


def _labeled(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line


def listing_document(
    listing: LearnListing, profiled: ProfiledListing | None = None
) -> dict[str, JsonValue]:
    """`profiled` adds `profile`, with what the learner profile hid."""
    document: dict[str, JsonValue] = {
        "guides": [_guide_fields(entry) for entry in listing.guides],
        "paths": [
            {
                "id": content_id(ContentType.PATH, view.path.slug),
                "slug": view.path.slug,
                "title": view.path.title,
                "summary": view.path.summary,
                "level": None if view.level is None else view.level.value,
                "guides": [step.slug for step in view.path.steps if step.kind is StepKind.GUIDE],
                "done": view.done,
                "total": view.total,
            }
            for view in listing.paths
        ],
    }
    if profiled is not None:
        document["profile"] = profile_document(profiled)
    return document


def profile_document(profiled: ProfiledListing) -> dict[str, JsonValue]:
    """The profile's values that narrowed the lists, null where one did not, and what it hid
    (docs/specs/cli.md#explicit-filters-and-widening); a guide has no language."""
    narrowed = profiled.narrowed
    return {
        "languages": None,
        "job_roles": None if narrowed.job_roles is None else list(narrowed.job_roles),
        "domains": None if narrowed.domains is None else list(narrowed.domains),
        "hidden": {"guides": profiled.hidden_guides, "paths": profiled.hidden_paths},
    }


def guide_document(page: GuidePage) -> dict[str, JsonValue]:
    return {
        **_guide_fields(page.entry),
        "markdown": page.markdown,
        "examples": [str(example) for example in page.examples],
    }


def marked_document(marked: MarkedRead) -> dict[str, JsonValue]:
    return {
        "id": content_id(ContentType.GUIDE, marked.slug),
        "slug": marked.slug,
        "read_at": marked.read_at.isoformat(),
        "already": marked.already,
    }


def path_document(view: PathView) -> dict[str, JsonValue]:
    steps = [_step_fields(position, step) for position, step in enumerate(view.steps, start=1)]
    following = next((fields for fields in steps if not fields["done"]), None)
    return {
        "id": content_id(ContentType.PATH, view.path.slug),
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
        "id": content_id(ContentType.GUIDE, meta.slug),
        "slug": meta.slug,
        "title": meta.title,
        "summary": meta.summary,
        "level": meta.level.value,
        "domains": list(meta.domains),
        "job_roles": list(meta.job_roles),
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
        "id": content_id(ContentType(step.step.kind.value), step.step.slug),
        "slug": step.step.slug,
        "title": step.title,
        "level": step.step.level,
        "done": step.done,
        "status": step.status,
        "level_passed": step.level_passed,
    }
