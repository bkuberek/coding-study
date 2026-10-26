"""The practice catalog: autograded problems in problems/ and non-autograded items in tracks/.

Slugs are unique across both (docs/specs/content.md#tracks); a slug that names both is a content
error that `cstudy verify` reports, and commands treat it as the problem.
"""

from collections.abc import Collection

from coding_study.application.environment import Environment
from coding_study.domain.items import ITEM_TRACKS
from coding_study.domain.next_selection import Candidate, candidate_of, item_candidate_of
from coding_study.domain.problem import Track
from coding_study.domain.scheduling import ProblemProgress

_UNTOUCHED = ProblemProgress()


def is_item(environment: Environment, slug: str) -> bool:
    """Whether `slug` names a non-autograded item rather than a problem."""
    return slug in environment.items.slugs() and slug not in environment.files.slugs()


def practice_candidates(
    environment: Environment, tracks: Collection[Track]
) -> tuple[Candidate, ...]:
    """Every problem, then every item, of `tracks`, each in catalog order, with its progress.

    Only the directories `tracks` need are read, so a broken problem never hides the items.
    """
    progress = environment.progress.problem_progress()
    problems = (
        tuple(
            candidate_of(summary.meta, progress.get(summary.meta.slug, _UNTOUCHED))
            for summary in environment.problems.list_summaries()
        )
        if any(track not in ITEM_TRACKS for track in tracks)
        else ()
    )
    items = (
        tuple(
            item_candidate_of(meta, progress.get(meta.slug, _UNTOUCHED))
            for meta in environment.items.list_items()
        )
        if any(track in ITEM_TRACKS for track in tracks)
        else ()
    )
    return tuple(candidate for candidate in (*problems, *items) if candidate.track in tracks)
