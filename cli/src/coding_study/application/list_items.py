"""`cstudy list` rows for rubric-checked problems (docs/specs/cli.md#cstudy-list).

They have no patterns and no reference languages, so `--pattern` and `--lang` leave them out, as
`--kind` does unless it names a rubric kind.
"""

from dataclasses import dataclass
from datetime import date

from coding_study.application.environment import Environment
from coding_study.application.list_problems import ProblemFilter
from coding_study.domain.items import ItemMeta, is_rubric_track
from coding_study.domain.scheduling import ProblemProgress, ProblemStatus


@dataclass(frozen=True, slots=True)
class ListedItem:
    meta: ItemMeta
    status: ProblemStatus
    due_on: date | None


def list_items(environment: Environment, problem_filter: ProblemFilter) -> tuple[ListedItem, ...]:
    """The matching rubric problems in the order of `cstudy list`."""
    if not _may_match(problem_filter):
        return ()
    progress = environment.progress.problem_progress()
    today = environment.clock.local_date(environment.clock.now())
    listed = (
        _listed(meta, progress.get(meta.slug, ProblemProgress()), today)
        for meta in sorted(environment.items.list_items(), key=lambda meta: meta.listing_key())
    )
    return tuple(item for item in listed if _matches(problem_filter, item))


def _may_match(problem_filter: ProblemFilter) -> bool:
    return (
        problem_filter.lists_rubric_problems
        and problem_filter.pattern is None
        and problem_filter.language is None
        and (problem_filter.track is None or is_rubric_track(problem_filter.track))
    )


def _matches(problem_filter: ProblemFilter, item: ListedItem) -> bool:
    meta = item.meta
    checks = (
        problem_filter.track in (None, meta.track),
        problem_filter.kind in (None, meta.kind),
        problem_filter.difficulty in (None, meta.difficulty),
        problem_filter.status in (None, item.status),
        problem_filter.content in (None, meta.status),
        problem_filter.labels.matches(meta.labels),
        problem_filter.holds(meta.slug),
        problem_filter.finds(meta.slug, meta.title),
    )
    return all(checks)


def _listed(meta: ItemMeta, progress: ProblemProgress, today: date) -> ListedItem:
    due_on = progress.schedule.due_on if progress.schedule else None
    return ListedItem(meta, progress.status(today), due_on)
