"""Every `--json` document has a schema in `schemas/cli/`, and every schema there describes one
(docs/specs/compatibility.md#json-documents).

A command or subcommand with a `--json` flag in `command_spec`, and `cstudy export`, name the
schemas of their documents in `DOCUMENTS`. A new `--json` flag fails here until its document has
a schema file and an entry; `test_json_documents.py` then validates real output against it.

A spec that defines documents ahead of their commands lists their schemas in `PLANNED`. An entry
there may name only a command that does not exist yet, so the commit that adds the command must
move it to `DOCUMENTS`, where its real output is validated.
"""

from collections.abc import Iterator

import pytest
import typer.main

from coding_study.domain.doc_checks import CommandSpec
from coding_study.entrypoints import cli
from coding_study.entrypoints.command_table import command_spec
from tests.helpers import REPOSITORY_ROOT

SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas" / "cli"
JSON_FLAG = "--json"
EXPORT = "export"
DOCUMENTS: dict[str, tuple[str, ...]] = {
    "list": ("list",),
    "next": ("next",),
    "status": ("status",),
    "history": ("history",),
    "set list": ("set-list",),
    "set show": ("set-show",),
    "learn": ("learn-list", "learn-guide", "learn-done", "learn-path"),
    "docs": ("docs-list", "docs-page"),
    "test": ("test",),
    "submit": ("submit",),
    "stats": ("stats",),
    "doctor": ("doctor",),
    "ai status": ("ai-status",),
    "ai usage": ("ai-usage",),
    "ai review": ("ai-review", "ai-review-list"),
    EXPORT: ("export",),
}
"""The command, or `cstudy export` for the file it writes, and the schemas of its documents."""
PLANNED: dict[str, tuple[str, ...]] = {}
"""Documents that docs/specs/ai.md defines before their commands exist, with their schemas."""


def program() -> CommandSpec:
    return command_spec(typer.main.get_command(cli.app))


def commands_with_json(spec: CommandSpec, path: tuple[str, ...] = ()) -> Iterator[str]:
    if JSON_FLAG in spec.options:
        yield " ".join(path)
    for name, subcommand in spec.subcommands.items():
        yield from commands_with_json(subcommand, (*path, name))


def schema_names() -> set[str]:
    return {
        path.name.removesuffix(".schema.json") for path in SCHEMA_DIRECTORY.glob("*.schema.json")
    }


def test_every_command_with_a_json_flag_names_its_schemas():
    unnamed = sorted(set(commands_with_json(program())) - DOCUMENTS.keys())
    assert unnamed == []


def test_every_command_that_names_schemas_has_a_json_flag_or_is_the_export():
    commands = set(commands_with_json(program()))
    stale = sorted(set(DOCUMENTS) - commands - {EXPORT})
    assert stale == []


def test_the_export_is_a_command():
    assert EXPORT in program().subcommands


@pytest.mark.parametrize(
    ("command", "name"),
    [(command, name) for command, names in DOCUMENTS.items() for name in names],
    ids=lambda value: str(value),
)
def test_every_document_has_a_schema(command, name):
    assert name in schema_names(), f"cstudy {command}: no schemas/cli/{name}.schema.json"


def test_every_schema_is_the_schema_of_a_document():
    used = {name for names in (*DOCUMENTS.values(), *PLANNED.values()) for name in names}
    assert sorted(schema_names() - used) == []


def test_no_two_commands_share_a_schema():
    named = [name for names in (*DOCUMENTS.values(), *PLANNED.values()) for name in names]
    assert sorted(name for name in set(named) if named.count(name) > 1) == []


@pytest.mark.parametrize(
    ("command", "name"),
    [(command, name) for command, names in PLANNED.items() for name in names],
    ids=lambda value: str(value),
)
def test_every_planned_document_has_a_schema(command, name):
    assert name in schema_names(), f"cstudy {command}: no schemas/cli/{name}.schema.json"


def test_a_planned_document_names_no_command_that_exists():
    """Once its command exists, a document moves to DOCUMENTS, where its output is validated."""
    built = sorted(set(PLANNED) & set(commands_with_json(program())))
    assert built == []
