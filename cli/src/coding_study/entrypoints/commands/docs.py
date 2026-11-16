"""`cstudy docs` (docs/specs/cli.md#cstudy-docs): read the user docs, how to use `cstudy`
(docs/specs/user-docs.md), in the terminal or in the web UI's Docs view."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment
from coding_study.application.environment import Environment
from coding_study.application.user_docs import doc_page, docs_listing
from coding_study.domain.cases import JsonValue
from coding_study.domain.content_ids import ContentType, content_id
from coding_study.domain.errors import UsageError
from coding_study.domain.user_docs import DocPage, in_sections
from coding_study.entrypoints.commands.serve import run_server
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "docs"
LABEL_WIDTH = 10
SLUG_WIDTH = 20
INDENT = "  "
COLUMN_GAP = 2
WEB_HINT = "Read in the web UI: cstudy docs {slug} --open"
OPEN_PRINTS_NOTHING = "--open takes no --json: it serves the page and opens it"
DOCS_VIEW = "/docs"
"""The Docs view (docs/specs/web-ui.md#docs-view), and `/docs/<topic>` a page of it."""
FREE_PORT = 0


def register(app: typer.Typer) -> None:
    add_command(app, docs, NAME)


def docs(
    context: typer.Context,
    topic: Annotated[
        str | None, typer.Argument(help="The topic to read; default: list the topics.")
    ] = None,
    open_page: Annotated[
        bool,
        typer.Option("--open", help="Serve the web UI and open the docs, or the topic, there."),
    ] = False,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the text.")
    ] = False,
) -> None:
    """Read how to use cstudy: install, workspace, practice, web UI, settings, troubleshooting."""
    if open_page and as_json:
        raise UsageError(OPEN_PRINTS_NOTHING)
    environment = load_catalog_environment(Path.cwd(), command_environ(context), Path.home())
    if open_page:
        view = DOCS_VIEW if topic is None else f"{DOCS_VIEW}/{doc_page(environment, topic).slug}"
        run_server(context, port=FREE_PORT, open_browser=True, view=view)
        return
    output = console(context)
    if topic is None:
        print_listing(output, environment, docs_listing(environment), as_json)
    else:
        print_page(output, doc_page(environment, topic), as_json)


def print_listing(
    output: Console, environment: Environment, pages: tuple[DocPage, ...], as_json: bool
) -> None:
    if as_json:
        typer.echo(json.dumps(listing_document(pages), indent=2))
        return
    if not pages:
        output.print(Text(f"no docs in {environment.content_root}"))
        return
    width = max(SLUG_WIDTH, *(len(page.slug) + COLUMN_GAP for page in pages))
    for section, members in in_sections(pages):
        output.print(Text(section, style="bold"))
        for page in members:
            output.print(Text(f"{INDENT}{page.slug.ljust(width)}{page.title}"))
    output.print(Text(""))
    output.print(_labeled("read", f"cstudy {NAME} <topic>"))
    output.print(Text(WEB_HINT.format(slug="<topic>"), style="dim"))


def print_page(output: Console, page: DocPage, as_json: bool) -> None:
    """Rendered by Rich on a terminal, which reads without color too; the Markdown as written
    otherwise, piped or redirected."""
    if as_json:
        typer.echo(json.dumps(page_document(page), indent=2))
        return
    text = page.markdown.lstrip("\n")
    if output.is_terminal:
        output.print(Markdown(text), soft_wrap=False)
    else:
        output.print(Text(text), end="")
    output.print(Text(""))
    output.print(Text(WEB_HINT.format(slug=page.slug), style="dim"))


def listing_document(pages: tuple[DocPage, ...]) -> dict[str, JsonValue]:
    return {"pages": [page_fields(page) for page in pages]}


def page_document(page: DocPage) -> dict[str, JsonValue]:
    return {**page_fields(page), "markdown": page.markdown}


def page_fields(page: DocPage) -> dict[str, JsonValue]:
    return {
        "id": content_id(ContentType.DOC, page.slug),
        "slug": page.slug,
        "title": page.title,
        "summary": page.summary,
        "section": page.section,
        "order": page.order,
        "headings": [
            {"id": heading.id, "title": heading.title, "level": heading.level}
            for heading in page.headings
        ],
    }


def _labeled(label: str, value: str) -> Text:
    line = Text(label.ljust(LABEL_WIDTH), style="dim")
    line.append(value)
    return line
