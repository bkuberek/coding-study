"""Every shipped user page passes the static checks of `cstudy verify` (docs/specs/user-docs.md),
and every `cstudy` command it names, with each flag, is one the real command line has
(docs/specs/user-docs.md#accuracy). A renamed command or flag fails here until the pages follow
it, and a new command until the command reference lists it (D7)."""

import re
from dataclasses import replace

import pytest
import typer.main

from coding_study.adapters.fs_user_docs import FsUserDocs
from coding_study.application.user_docs import check_user_docs
from coding_study.domain.doc_checks import command_issues, command_mentions, page_file
from coding_study.entrypoints import cli
from coding_study.entrypoints.command_table import command_spec
from tests.helpers import REPOSITORY_ROOT

DOCS = FsUserDocs(REPOSITORY_ROOT)
PROGRAM = command_spec(typer.main.get_command(cli.app))
TOPICS = (
    "getting-started",
    "toolchains",
    "doctor",
    "workspace",
    "upgrading",
    "practice",
    "problem-kinds",
    "levels",
    "service-projects",
    "ide-and-debugging",
    "guides",
    "planning",
    "own-problems",
    "web-ui",
    "editor",
    "settings",
    "ai",
    "commands",
    "troubleshooting",
)
"""docs/specs/user-docs.md#topics, in order."""
COMMANDS = "commands"
"""The command reference: its tables have a row per command, with the command, its flags and
what it does."""
_COMMAND_ROW = re.compile(
    r"^\| `(?P<command>cstudy [^`]*)` \| (?P<flags>[^|]*) \| (?:[^|\\]|\\.)* \|$", re.MULTILINE
)
_CODE_SPAN = re.compile(r"`([^`]+)`")


def test_the_topics_are_those_of_the_spec_in_order():
    pages = sorted((DOCS.load(slug) for slug in DOCS.slugs()), key=lambda page: page.order)
    assert tuple(page.slug for page in pages) == TOPICS


def test_every_page_passes_the_static_checks():
    failures = {
        result.file: result.static_errors
        for result in check_user_docs(DOCS, PROGRAM)
        if result.static_errors
    }
    assert failures == {}


@pytest.mark.parametrize("slug", DOCS.slugs())
def test_every_command_and_flag_a_page_names_exists(slug: str):
    page = DOCS.load(slug)
    assert [str(issue) for issue in command_issues(page_file(slug), page, PROGRAM)] == []


def test_the_pages_name_commands_for_the_check_to_read():
    """The check reads something: the pages name dozens of commands, `cstudy docs` among them."""
    mentions = [
        mention.text
        for slug in DOCS.slugs()
        for mention in command_mentions(DOCS.load(slug).markdown)
    ]
    assert (len(mentions) > 100, any("cstudy docs" in text for text in mentions)) == (True, True)


def test_the_command_reference_has_a_row_for_every_command_with_flags_it_takes():
    """D7: every command and subcommand of `cstudy` has a row, and each flag in a row's Flags
    column is one its command takes, so the reference stays complete as D6 keeps it true."""
    page = DOCS.load(COMMANDS)
    rows = [(row["command"], row["flags"]) for row in _COMMAND_ROW.finditer(page.markdown)]
    listed = {path for command, _flags in rows for path in _command_paths(command)}
    flags = "\n".join(
        f"`{command} {flag}`" for command, cell in rows for flag in _CODE_SPAN.findall(cell)
    )
    issues = command_issues(page_file(COMMANDS), replace(page, markdown=flags), PROGRAM)
    assert (sorted(_every_command() - listed), [str(issue) for issue in issues]) == ([], [])


def _every_command() -> set[tuple[str, ...]]:
    return {
        path
        for name, spec in PROGRAM.subcommands.items()
        for path in ((name,), *((name, sub) for sub in spec.subcommands))
    }


def _command_paths(command: str) -> tuple[tuple[str, ...], ...]:
    """`cstudy set add <name> <slug>...` names `set` and `set add`: the words that are no
    placeholder, a group's first two."""
    name, *rest = (word for word in command.split()[1:] if word[0] not in "-<[")
    spec = PROGRAM.subcommands.get(name)
    if spec is not None and spec.subcommands and rest:
        return ((name,), (name, rest[0]))
    return ((name,),)
