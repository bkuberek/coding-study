"""S26: no two problems carry the same external judge reference (docs/specs/authoring.md#static).

A reference names the judge's problem a catalog problem is based on. Two problems with the same
one are the same problem written twice, so each of them reports the others. Items have no
`references.leetcode`, so only problems take part. A problem whose files do not load has no
reference to compare: its own load error is reported instead. Like S2, it is an error.
"""

from collections import defaultdict

from coding_study.application.environment import Environment
from coding_study.domain.errors import ContentError, ContentIssue
from coding_study.domain.problem_files import META_FILE

REFERENCE_FIELD = "references.leetcode"


def reference_conflicts(environment: Environment) -> dict[str, tuple[str, ...]]:
    """The issues of every problem that shares its reference, keyed by slug. A duplicated slug is
    judged once, by its first directory, which S2 already reports."""
    files = environment.files
    by_number: defaultdict[int, list[str]] = defaultdict(list)
    for slug in dict.fromkeys(files.slugs()):
        number = _leetcode_number(environment, slug)
        if number is not None:
            by_number[number].append(slug)
    conflicts: dict[str, tuple[str, ...]] = {}
    for number, slugs in by_number.items():
        for slug in slugs:
            others = [files.problem_directory(other) for other in slugs if other != slug]
            if others:
                issue = _issue(files.problem_directory(slug), number, others)
                conflicts[slug] = (*conflicts.get(slug, ()), str(issue))
    return conflicts


def _leetcode_number(environment: Environment, slug: str) -> int | None:
    try:
        reference = environment.problems.load(slug).meta.references.leetcode
    except ContentError:
        return None
    return None if reference is None else reference.number


def _issue(directory: str, number: int, others: list[str]) -> ContentIssue:
    return ContentIssue(
        f"{directory}/{META_FILE}",
        REFERENCE_FIELD,
        f"number {number} is also used by {', '.join(others)}",
    )
