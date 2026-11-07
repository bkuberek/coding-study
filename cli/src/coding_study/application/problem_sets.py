"""`cstudy set` and the Sets view (docs/specs/cli.md#cstudy-set): each change to a set, under a lock
so a change from the terminal and one from the page never lose each other's work, and how far a set
has come, which is read from the progress each time and stored nowhere."""

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.list_items import ListedItem, list_items
from coding_study.application.list_problems import ListedProblem, ProblemFilter, list_problems
from coding_study.application.practice_catalog import catalog_slugs
from coding_study.domain.errors import UnknownSetError, UsageError
from coding_study.domain.problem_sets import (
    ProblemSet,
    SetStanding,
    one_line,
    set_name_issue,
    standing_of,
    unknown_slug_message,
)

SETS_LOCK = ".cs/sets.lock"


@dataclass(frozen=True, slots=True)
class SetChange:
    """What an `add` or a `remove` did."""

    problem_set: ProblemSet
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]
    """The slugs that were already there, or not there, which change nothing."""


@dataclass(frozen=True, slots=True)
class SetRow:
    position: int
    """From 1."""
    slug: str
    passed: bool
    listed: ListedProblem | ListedItem | None
    """What `cstudy list` says of the entry; None for a slug the catalog does not have."""


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


def add_to_set(environment: Environment, name: str, slugs: Iterable[str]) -> SetChange:
    """Appends the slugs it does not hold, in the order given. Raises UsageError, adding none, for
    one the catalog does not have."""
    with _changing(environment):
        found = find_set(environment, name)
        wanted = tuple(dict.fromkeys(slugs))
        new = tuple(slug for slug in wanted if not found.holds(slug))
        _require_in_catalog(environment, new)
        changed = found.with_slugs(new)
        if new:
            environment.problem_sets.set_problems(name, changed.slugs)
    return SetChange(changed, new, tuple(slug for slug in wanted if found.holds(slug)))


def remove_from_set(environment: Environment, name: str, slugs: Iterable[str]) -> SetChange:
    """Takes out the slugs it holds, whether or not the catalog still has them."""
    with _changing(environment):
        found = find_set(environment, name)
        wanted = tuple(dict.fromkeys(slugs))
        held = tuple(slug for slug in wanted if found.holds(slug))
        changed = found.without_slugs(held)
        if held:
            environment.problem_sets.set_problems(name, changed.slugs)
    return SetChange(changed, held, tuple(slug for slug in wanted if not found.holds(slug)))


def move_in_set(environment: Environment, name: str, slug: str, position: int) -> ProblemSet:
    """`slug` at `position`, from 1. Raises UsageError for one it does not hold or a position
    outside the list."""
    with _changing(environment):
        moved = find_set(environment, name).moved(slug, position)
        environment.problem_sets.set_problems(name, moved.slugs)
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
    return standing_of(problem_set, catalog_slugs(environment), _passed_slugs(environment))


def sets_with_standing(
    environment: Environment,
) -> tuple[tuple[ProblemSet, SetStanding], ...]:
    catalog, passed = catalog_slugs(environment), _passed_slugs(environment)
    return tuple(
        (problem_set, standing_of(problem_set, catalog, passed))
        for problem_set in read_sets(environment)
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
    passed = _passed_slugs(environment)
    rows = tuple(
        SetRow(position, slug, slug in listed and slug in passed, listed.get(slug))
        for position, slug in enumerate(problem_set.slugs, start=1)
    )
    standing = standing_of(problem_set, frozenset(listed), passed)
    return SetView(problem_set, standing, rows)


def _changing(environment: Environment) -> AbstractContextManager[None]:
    return environment.workspace.locked(SETS_LOCK)


def _passed_slugs(environment: Environment) -> frozenset[str]:
    progress = environment.progress.problem_progress()
    return frozenset(slug for slug, found in progress.items() if found.has_passed)


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
