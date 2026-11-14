"""`cstudy docs` (docs/specs/cli.md#cstudy-docs), and the command line it and `cstudy verify` read
the user docs against (docs/specs/user-docs.md#accuracy)."""

import io
import json
from pathlib import Path
from typing import Any

import pytest
import typer.main
from rich.console import Console
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.user_docs import doc_page
from coding_study.entrypoints import cli
from coding_study.entrypoints.command_table import command_spec
from coding_study.entrypoints.commands import docs
from coding_study.entrypoints.shared import ExitCode
from tests.doc_builders import write_docs
from tests.fakes import make_environment

runner = CliRunner()
HINT = "Read in the web UI: cstudy docs"


@pytest.fixture
def environment(content_root: Path, monkeypatch: pytest.MonkeyPatch) -> Environment:
    write_docs(content_root)
    environment = make_environment(content_root)
    monkeypatch.setattr(docs, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["docs", *arguments])


def test_the_list_shows_each_section_with_its_pages(environment: Environment):
    assert invoke().output.splitlines() == [
        "Start here",
        "  getting-started     Getting started",
        "  doctor              Check your setup",
        "Practise",
        "  practice            Work on a problem",
        "",
        "read      cstudy docs <topic>",
        f"{HINT} <topic> --open",
    ]


def test_a_page_piped_is_its_markdown_without_front_matter(environment: Environment):
    output = invoke("doctor").output
    assert output.splitlines() == [
        "# Check your setup",
        "",
        "It checks each tool.",
        "",
        "## The rows",
        "",
        "One per tool.",
        "",
        "### `--fix`",
        "",
        "It sets up the workspace.",
        "",
        f"{HINT} doctor --open",
    ]


def test_a_page_on_a_terminal_is_rendered_and_reads_without_colour(environment: Environment):
    terminal = io.StringIO()
    output = Console(file=terminal, force_terminal=True, no_color=True, width=60)
    docs.print_page(output, doc_page(environment, "doctor"), as_json=False)
    text = terminal.getvalue()
    assert ("Check your setup" in text, "# Check" in text, "\x1b[3" in text) == (True, False, False)


def test_the_list_as_json_has_every_page_with_its_headings(environment: Environment):
    document = json.loads(invoke("--json").output)
    assert (len(document["pages"]), document["pages"][1]) == (
        3,
        {
            "slug": "doctor",
            "title": "Check your setup",
            "summary": "What cstudy doctor checks.",
            "section": "Start here",
            "order": 20,
            "headings": [
                {"id": "the-rows", "title": "The rows", "level": 2},
                {"id": "--fix", "title": "--fix", "level": 3},
            ],
        },
    )


def test_a_page_as_json_adds_its_markdown(environment: Environment):
    document = json.loads(invoke("practice", "--json").output)
    assert (document["slug"], document["markdown"].splitlines()[1]) == (
        "practice",
        "# Work on a problem",
    )


def test_an_unknown_topic_exits_3_with_the_nearest(environment: Environment):
    result = invoke("doctr")
    assert (result.exit_code, result.stderr.strip()) == (
        ExitCode.USAGE_ERROR,
        'error: unknown topic "doctr"; did you mean doctor?',
    )


def test_open_serves_the_page_on_the_topic_or_the_list(
    environment: Environment, monkeypatch: pytest.MonkeyPatch
):
    served: list[dict[str, Any]] = []
    monkeypatch.setattr(docs, "run_server", lambda _context, **options: served.append(options))
    assert (invoke("doctor", "--open").exit_code, invoke("--open").exit_code) == (0, 0)
    assert served == [
        {"port": 0, "open_browser": True, "view": "/docs/doctor"},
        {"port": 0, "open_browser": True, "view": "/docs"},
    ]


def test_open_refuses_json_and_an_unknown_topic_before_serving(
    environment: Environment, monkeypatch: pytest.MonkeyPatch
):
    served: list[object] = []
    monkeypatch.setattr(docs, "run_server", lambda *_args, **_options: served.append(1))
    with_json, unknown = invoke("--open", "--json"), invoke("doctr", "--open")
    assert (with_json.exit_code, with_json.stderr.strip(), unknown.exit_code, served) == (
        ExitCode.USAGE_ERROR,
        "error: --open takes no --json: it serves the page and opens it",
        ExitCode.USAGE_ERROR,
        [],
    )


def test_a_content_root_without_docs_says_so(content_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(docs, "load_catalog_environment", lambda *_: make_environment(content_root))
    assert invoke().output.strip() == f"no docs in {content_root}"


def test_the_command_line_names_every_command_flag_and_subcommand():
    program = command_spec(typer.main.get_command(cli.app))
    test, docs_command, group = (program.subcommands[name] for name in ("test", "docs", "set"))
    assert (
        program.options["--workspace"],
        program.options["--no-color"],
        test.options["--lang"],
        test.options["--watch"],
        test.options["--help"],
        sorted(docs_command.options),
        sorted(group.subcommands),
        group.subcommands["add"].options["--level"],
    ) == (
        True,
        False,
        True,
        False,
        False,
        ["--help", "--json", "--open"],
        ["add", "create", "delete", "list", "move", "remove", "rename", "show"],
        True,
    )
