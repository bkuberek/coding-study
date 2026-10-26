"""`cstudy list` rows for non-autograded items (docs/specs/cli.md#cstudy-list).

Items have no patterns and no reference languages, so `--pattern` and `--lang` leave them out.
"""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.application.list_problems import ProblemFilter
from coding_study.domain.items import ITEM_TRACKS, ItemMeta
from coding_study.domain.problem import Track
from coding_study.domain.scheduling import ProblemProgress, ProblemStatus

_TRACK_RANK = {track: rank for rank, track in enumerate(Track)}


@dataclass(frozen=True, slots=True)
class ListedItem:
    meta: ItemMeta
    status: ProblemStatus
    due_on: date | None


def list_items(environment: Environment, problem_filter: ProblemFilter) -> tuple[ListedItem, ...]:
    """Matching items by track, then curriculum order, then slug."""
    if not _may_match(problem_filter):
        return ()
    progress = environment.progress.problem_progress()
    today = environment.clock.local_date(environment.clock.now())
    listed = (
        _listed(meta, progress.get(meta.slug, ProblemProgress()), today)
        for meta in sorted(environment.items.list_items(), key=_catalog_order)
    )
    return tuple(item for item in listed if _matches(problem_filter, item))


def _may_match(problem_filter: ProblemFilter) -> bool:
    return (
        problem_filter.pattern is None
        and problem_filter.language is None
        and problem_filter.track in (None, *ITEM_TRACKS)
    )


def _matches(problem_filter: ProblemFilter, item: ListedItem) -> bool:
    meta = item.meta
    checks = (
        problem_filter.track in (None, meta.track),
        problem_filter.difficulty in (None, meta.difficulty),
        problem_filter.status in (None, item.status),
        problem_filter.content in (None, meta.status),
    )
    return all(checks)


def _catalog_order(meta: ItemMeta) -> tuple[int, int, str]:
    return (_TRACK_RANK[meta.track], meta.order, meta.slug)


def _listed(meta: ItemMeta, progress: ProblemProgress, today: date) -> ListedItem:
    due_on = progress.schedule.due_on if progress.schedule else None
    return ListedItem(meta, progress.status(today), due_on)
