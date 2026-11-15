"""The practice catalog: the problems checked by tests and those checked by a rubric, which share
`problems/` (docs/specs/compatibility.md#rubric-checked-problems).

Slugs are unique across both, because they are directory names.
"""

from collections.abc import Collection

from coding_study.application.environment import Environment
from coding_study.domain.checked_by import CheckedBy, checked_by_of
from coding_study.domain.items import EntryKind, is_rubric_track
from coding_study.domain.next_selection import Candidate, candidate_of, item_candidate_of
from coding_study.domain.problem import Track
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.scheduling import ProblemProgress

_UNTOUCHED = ProblemProgress()


def is_item(environment: Environment, slug: str) -> bool:
    """Whether `slug` names a problem checked by a rubric rather than by tests."""
    return environment.items.contains(slug)


def checked_by_slug(environment: Environment, slug: str, kind: EntryKind) -> tuple[CheckedBy, ...]:
    """How the problem `slug` of `kind` is checked, from the files of its folder."""
    return checked_by_of(kind, RUBRIC_FILE in environment.files.file_names(slug))


def catalog_slugs(environment: Environment) -> frozenset[str]:
    """Every slug `cstudy start` knows: the catalog's problems and your own."""
    return frozenset(environment.files.slugs())


def practice_candidates(
    environment: Environment, tracks: Collection[Track]
) -> tuple[Candidate, ...]:
    """Every autograded problem, then every rubric problem, of `tracks`, each in catalog order,
    with its progress.

    Only the directories `tracks` need are read, so a broken problem never hides the rubric
    problems.
    """
    progress = environment.progress.problem_progress()
    problems = (
        tuple(
            candidate_of(summary.meta, progress.get(summary.meta.slug, _UNTOUCHED))
            for summary in environment.problems.list_summaries()
        )
        if any(not is_rubric_track(track) for track in tracks)
        else ()
    )
    items = (
        tuple(
            item_candidate_of(meta, progress.get(meta.slug, _UNTOUCHED))
            for meta in environment.items.list_items()
        )
        if any(is_rubric_track(track) for track in tracks)
        else ()
    )
    return tuple(candidate for candidate in (*problems, *items) if candidate.track in tracks)
