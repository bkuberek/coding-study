"""Every shipped user page passes the static checks of `cstudy verify` (docs/specs/user-docs.md),
and every `cstudy` command it names, with each flag, is one the real command line has
(docs/specs/user-docs.md#accuracy). A renamed command or flag fails here until the pages follow
it."""

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
    "levels",
    "service-projects",
    "guides",
    "planning",
    "web-ui",
    "editor",
    "settings",
    "troubleshooting",
)
"""docs/specs/user-docs.md#topics, in order."""


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
