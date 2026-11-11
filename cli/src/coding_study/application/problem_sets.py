"""`cstudy set` and the Sets view (docs/specs/cli.md#cstudy-set): each change to a set, under a lock
so a change from the terminal and one from the page never lose each other's work, and how far a set
has come, which is read from the progress each time and stored nowhere. An entry may name the
level a progressive or project problem is done at (docs/decisions/0024-level-passes.md).
"""

from collections.abc import Iterable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.list_items import ListedItem, list_items
from coding_study.application.list_problems import ListedProblem, ProblemFilter, list_problems
from coding_study.application.practice_catalog import catalog_slugs, is_item
from coding_study.domain.errors import UnknownSetError, UsageError
from coding_study.domain.levels import level_progress
from coding_study.domain.problem_sets import (
    ProblemSet,
    SetStanding,
    one_line,
    set_name_issue,
    standing_of,
    target_reached,
    unknown_slug_message,
)
from coding_study.domain.scheduling import ProblemProgress

SETS_LOCK = ".cs/sets.lock"


@dataclass(frozen=True, slots=True)
class SetChange:
    """What an `add` or a `remove` did."""

    problem_set: ProblemSet
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]
    """The slugs that were already there, or not there, which change nothing."""
    retargeted: tuple[str, ...] = ()
    """The slugs already there whose target level changed."""


@dataclass(frozen=True, slots=True)
class SetRow:
    position: int
    """From 1."""
    slug: str
    passed: bool
    """Done: a pass reached the entry's target level, every level by default."""
    listed: ListedProblem | ListedItem | None
    """What `cstudy list` says of the entry; None for a slug the catalog does not have."""
    level: int | None = None
    """The target level the entry names; None for every level."""


@dataclass(frozen=True, slots=True)
class SetView:
    problem_set: ProblemSet
    standing: SetStanding
    rows: tuple[SetRow, ...]


def read_sets(environment: Environment) -> tuple[ProblemSet, ...]:
    return environment.problem_sets.read()


def find_set(environment: Environment, name: str) -> ProblemSet:
    """Raises UnknownSetError, naming the sets there are."""
    sets = read_sets(environment)
    found = next((problem_set for problem_set in sets if problem_set.name == name), None)
    if found is None:
        raise UnknownSetError(name, tuple(problem_set.name for problem_set in sets))
    return found


def in_named_set(
    environment: Environment, problem_filter: ProblemFilter, name: str | None
) -> ProblemFilter:
    """`--set`: the filter narrowed to the set named `name`, if any. Raises UnknownSetError."""
    return (
        problem_filter
        if name is None
        else replace(problem_filter, in_set=find_set(environment, name))
    )


def create_set(environment: Environment, name: str, description: str | None = None) -> ProblemSet:
    """Raises UsageError for a name that is not a slug or that exists: it never merges."""
    _require_name(name)
    created = ProblemSet(name, one_line(description))
    with _changing(environment):
        _require_free(environment, name)
        environment.problem_sets.add(created)
    return created


def add_to_set(
    environment: Environment, name: str, slugs: Iterable[str], level: int | None = None
) -> SetChange:
    """Appends the slugs it does not hold, in the order given; with `level`, each is done at that
    level, which also changes the target of one it holds. Raises UsageError, adding none, for one
    the catalog does not have or, with `level`, one without that level."""
    with _changing(environment):
        found = find_set(environment, name)
        wanted = tuple(dict.fromkeys(slugs))
        new = tuple(slug for slug in wanted if not found.holds(slug))
        _require_in_catalog(environment, new)
        targets = {} if level is None else _targets(environment, wanted, level)
        changed = found.with_slugs(new).with_targets(targets)
        retargeted = tuple(
            slug for slug in targets if found.holds(slug) and found.target_of(slug) != level
        )
        if new or retargeted:
            _write(environment, changed)
    unchanged = tuple(slug for slug in wanted if found.holds(slug) and slug not in retargeted)
    return SetChange(changed, new, unchanged, retargeted)


def _targets(environment: Environment, slugs: Iterable[str], level: int) -> dict[str, int]:
    """Each slug's target `level`; raises UsageError for one without levels, or without that
    level."""
    targets: dict[str, int] = {}
    for slug in slugs:
        last = _last_level(environment, slug)
        if last is None:
            raise UsageError(
                f"{slug} has no levels; --level is for progressive and project problems"
            )
        if not 1 <= level <= last:
            raise UsageError(f"{slug} has levels 1 to {last}")
        targets[slug] = level
    return targets


def _last_level(environment: Environment, slug: str) -> int | None:
    if is_item(environment, slug):
        return None
    levels = level_progress(environment.problems.load(slug).meta, None)
    return levels.last if levels else None


def _write(environment: Environment, changed: ProblemSet) -> None:
    environment.problem_sets.set_problems(changed.name, changed.slugs, changed.targets)


def remove_from_set(environment: Environment, name: str, slugs: Iterable[str]) -> SetChange:
    """Takes out the slugs it holds, whether or not the catalog still has them."""
    with _changing(environment):
        found = find_set(environment, name)
        wanted = tuple(dict.fromkeys(slugs))
        held = tuple(slug for slug in wanted if found.holds(slug))
        changed = found.without_slugs(held)
        if held:
            _write(environment, changed)
    return SetChange(changed, held, tuple(slug for slug in wanted if not found.holds(slug)))


def move_in_set(environment: Environment, name: str, slug: str, position: int) -> ProblemSet:
    """`slug` at `position`, from 1. Raises UsageError for one it does not hold or a position
    outside the list."""
    with _changing(environment):
        moved = find_set(environment, name).moved(slug, position)
        _write(environment, moved)
    return moved


def rename_set(environment: Environment, name: str, new_name: str) -> ProblemSet:
    """Raises UsageError for a name that is not a slug or that exists."""
    _require_name(new_name)
    with _changing(environment):
        found = find_set(environment, name)
        _require_free(environment, new_name)
        environment.problem_sets.rename(name, new_name)
    return replace(found, name=new_name)


def delete_set(environment: Environment, name: str) -> ProblemSet:
    """Takes the set out of the file; what you practised stays in the progress."""
    with _changing(environment):
        found = find_set(environment, name)
        environment.problem_sets.delete(name)
    return found


def set_standing(environment: Environment, problem_set: ProblemSet) -> SetStanding:
    done = _done(problem_set, _entry_progress(environment))
    return standing_of(problem_set, catalog_slugs(environment), done)


def sets_with_standing(
    environment: Environment,
) -> tuple[tuple[ProblemSet, SetStanding], ...]:
    catalog, progress = catalog_slugs(environment), _entry_progress(environment)
    return tuple(
        (problem_set, standing_of(problem_set, catalog, _done(problem_set, progress)))
        for problem_set in read_sets(environment)
    )


type _EntryProgress = Mapping[str, tuple[ProblemProgress, int | None]]
"""Each slug's progress, and its last level; None for one without levels."""


def _entry_progress(environment: Environment) -> _EntryProgress:
    progress = environment.progress.problem_progress()
    lasts = {
        summary.meta.slug: levels.last
        for summary in environment.problems.list_summaries()
        if summary.meta.slug in progress
        and (levels := level_progress(summary.meta, None)) is not None
    }
    return {slug: (found, lasts.get(slug)) for slug, found in progress.items()}


def _done(problem_set: ProblemSet, progress: _EntryProgress) -> frozenset[str]:
    """The entries done: a pass reached the target level, every level by default."""
    return frozenset(
        slug
        for slug in problem_set.slugs
        if slug in progress and target_reached(*progress[slug], problem_set.target_of(slug))
    )


def missing_slugs(environment: Environment, problem_set: ProblemSet) -> tuple[str, ...]:
    catalog = catalog_slugs(environment)
    return tuple(slug for slug in problem_set.slugs if slug not in catalog)


def set_view(environment: Environment, name: str) -> SetView:
    """The set's rows, in its order, each with what `cstudy list` says of it."""
    problem_set = find_set(environment, name)
    everything = ProblemFilter()
    listed: dict[str, ListedProblem | ListedItem] = {
        item.meta.slug: item for item in list_items(environment, everything)
    }
    listed |= {
        problem.summary.meta.slug: problem for problem in list_problems(environment, everything)
    }
    passed = _done(problem_set, _entry_progress(environment))
    rows = tuple(
        SetRow(
            position,
            slug,
            slug in listed and slug in passed,
            listed.get(slug),
            problem_set.target_of(slug),
        )
        for position, slug in enumerate(problem_set.slugs, start=1)
    )
    standing = standing_of(problem_set, frozenset(listed), passed)
    return SetView(problem_set, standing, rows)


def _changing(environment: Environment) -> AbstractContextManager[None]:
    return environment.workspace.locked(SETS_LOCK)


def _require_name(name: str) -> None:
    issue = set_name_issue(name)
    if issue is not None:
        raise UsageError(issue)


def _require_free(environment: Environment, name: str) -> None:
    if any(problem_set.name == name for problem_set in read_sets(environment)):
        raise UsageError(f"set {name} already exists")


def _require_in_catalog(environment: Environment, slugs: Iterable[str]) -> None:
    catalog = catalog_slugs(environment)
    unknown = [slug for slug in slugs if slug not in catalog]
    if unknown:
        raise UsageError("; ".join(unknown_slug_message(slug, catalog) for slug in unknown))
