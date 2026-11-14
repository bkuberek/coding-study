"""`cstudy docs` (docs/specs/cli.md#cstudy-docs) and the Docs view: the user docs in
`user-docs/` (docs/specs/user-docs.md), and their static checks in `cstudy verify` (D1 to D6)."""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.ports import UserDocs
from coding_study.domain.doc_checks import (
    CommandSpec,
    command_issues,
    folder_issues,
    order_issues,
    page_file,
    page_static_checks,
)
from coding_study.domain.errors import ContentError, ContentIssue, UnknownTopicError
from coding_study.domain.user_docs import DocPage, unknown_topic_message


@dataclass(frozen=True, slots=True)
class DocVerification:
    file: str
    """A page's file, or another entry of `user-docs/`, repository-relative."""
    static_errors: tuple[str, ...] = ()


def docs_listing(environment: Environment) -> tuple[DocPage, ...]:
    """Every page, by `order`. Raises ContentError for a page that does not load."""
    docs = environment.docs
    return tuple(sorted((docs.load(slug) for slug in docs.slugs()), key=lambda page: page.order))


def doc_page(environment: Environment, slug: str) -> DocPage:
    """Raises UnknownTopicError for a page that does not exist, ContentError for one that does
    not load."""
    known = environment.docs.slugs()
    if slug not in known:
        raise UnknownTopicError(unknown_topic_message(slug, known))
    return environment.docs.load(slug)


def verify_user_docs(
    environment: Environment, commands: CommandSpec | None
) -> tuple[DocVerification, ...]:
    """One result per page, then one per other entry of `user-docs/`. `commands` is `cstudy`'s
    command line, for D6; None leaves the commands unchecked."""
    return check_user_docs(environment.docs, commands)


def check_user_docs(docs: UserDocs, commands: CommandSpec | None) -> tuple[DocVerification, ...]:
    """`verify_user_docs` over any `user-docs/`, such as the checkout's, in the content tests."""
    pages: dict[str, DocPage] = {}
    failures: dict[str, list[ContentIssue]] = {}
    for slug in docs.slugs():
        try:
            pages[slug] = docs.load(slug)
        except ContentError as error:
            failures[slug] = list(error.issues)
    ordering = order_issues(tuple(pages.values()))
    found: dict[str, list[ContentIssue]] = {}
    for slug in docs.slugs():
        file = page_file(slug)
        page = pages.get(slug)
        if page is None:
            found[file] = failures[slug]
            continue
        found[file] = [
            *page_static_checks(file, page, pages),
            *ordering.get(slug, []),
            *(command_issues(file, page, commands) if commands is not None else []),
        ]
    for issue in folder_issues(docs.entries()):
        found.setdefault(issue.file, []).append(issue)
    return tuple(
        DocVerification(file, tuple(str(issue) for issue in issues))
        for file, issues in sorted(found.items())
    )
