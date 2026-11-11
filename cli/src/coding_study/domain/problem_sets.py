"""Problem sets: a name, an optional description and an ordered list of slugs, of problems and
items alike, and the shape of `sets.yaml`, which schemas/sets.schema.json states too
(docs/decisions/0023-problem-sets.md). What the catalog holds is not this file's concern: a slug it
no longer has stays in the set and shows as missing. An entry may name the level a progressive or
project problem is done at (docs/decisions/0024-level-passes.md#target-levels-in-sets)."""

import difflib
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, replace
from typing import cast

from coding_study.domain.errors import ConfigError, UsageError
from coding_study.domain.scheduling import ProblemProgress

SETS_FILE = "sets.yaml"
SETS_KEY = "sets"
DESCRIPTION_KEY = "description"
PROBLEMS_KEY = "problems"
SLUG_KEY = "slug"
LEVEL_KEY = "level"
EXAMPLE_NAME = "backend-loop"
_NAME = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_NAME_LENGTH = 64
_SET_KEYS = (DESCRIPTION_KEY, PROBLEMS_KEY)
_ENTRY_KEYS = (SLUG_KEY, LEVEL_KEY)
_SUGGESTIONS = 3
_SUGGESTION_CUTOFF = 0.75


@dataclass(frozen=True, slots=True)
class ProblemSet:
    name: str
    description: str | None = None
    slugs: tuple[str, ...] = ()
    levels: tuple[tuple[str, int], ...] = ()
    """The entries that name a target level, by slug, in the set's order. Another entry of a
    problem with levels is done at its last level."""

    def holds(self, slug: str) -> bool:
        return slug in self.slugs

    @property
    def targets(self) -> dict[str, int]:
        return dict(self.levels)

    def target_of(self, slug: str) -> int | None:
        return self.targets.get(slug)

    def with_targets(self, targets: Mapping[str, int]) -> "ProblemSet":
        """These entries done at these levels; the others keep theirs."""
        return replace(self, levels=_in_order(self.slugs, {**self.targets, **targets}))

    def position_of(self, slug: str) -> int:
        """Where a slug it holds stands, from 1."""
        return self.slugs.index(slug) + 1

    def with_slugs(self, slugs: Iterable[str]) -> "ProblemSet":
        """`slugs` appended, in the order given."""
        return replace(self, slugs=(*self.slugs, *slugs))

    def without_slugs(self, slugs: Collection[str]) -> "ProblemSet":
        kept = tuple(slug for slug in self.slugs if slug not in slugs)
        return replace(self, slugs=kept, levels=_in_order(kept, self.targets))

    def moved(self, slug: str, position: int) -> "ProblemSet":
        """`slug` at `position`, from 1. Raises UsageError for a slug it does not hold or a
        position outside the list."""
        if not self.holds(slug):
            raise UsageError(f"{slug} is not in {self.name}")
        issue = position_issue(self, position)
        if issue is not None:
            raise UsageError(issue)
        others = [other for other in self.slugs if other != slug]
        others.insert(position - 1, slug)
        return replace(self, slugs=tuple(others), levels=_in_order(others, self.targets))


def _in_order(slugs: Iterable[str], targets: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple((slug, targets[slug]) for slug in slugs if slug in targets)


@dataclass(frozen=True, slots=True)
class SetStanding:
    """How far a set has come, read from the progress each time: a set stores none of it."""

    name: str
    passed: int
    total: int
    """The entries the catalog has; a set can finish after the catalog dropped a slug."""
    missing: tuple[str, ...]
    """The slugs the catalog does not have."""

    @property
    def finished(self) -> bool:
        return self.total > 0 and self.passed == self.total


def target_reached(progress: ProblemProgress, last: int | None, target: int | None) -> bool:
    """Whether a set entry is done: for a problem with `last` levels, once a pass reached its
    target level, the last by default and at most; for anything else, once it passed."""
    if last is None:
        return progress.has_passed
    goal = last if target is None else min(target, last)
    return progress.levels_passed(last) >= goal


def standing_of(
    problem_set: ProblemSet, catalog: Collection[str], passed: Collection[str]
) -> SetStanding:
    """`passed`: the slugs done, as `target_reached` judges each."""
    present = [slug for slug in problem_set.slugs if slug in catalog]
    missing = tuple(slug for slug in problem_set.slugs if slug not in catalog)
    return SetStanding(
        problem_set.name, sum(slug in passed for slug in present), len(present), missing
    )


def set_name_issue(name: str) -> str | None:
    """Why `name` can't name a set; None when it can."""
    if _NAME.fullmatch(name) and len(name) <= _NAME_LENGTH:
        return None
    return (
        f'invalid set name "{name}": use lowercase letters, digits and hyphens, starting with a '
        f"letter, at most {_NAME_LENGTH} characters, such as {EXAMPLE_NAME}"
    )


def position_issue(problem_set: ProblemSet, position: int) -> str | None:
    if 1 <= position <= len(problem_set.slugs):
        return None
    return (
        f"position {position} is outside {problem_set.name}, which holds {len(problem_set.slugs)}"
    )


def unknown_slug_message(slug: str, catalog: Iterable[str]) -> str:
    """Refuses a slug the catalog does not have, naming the nearest ones."""
    near = difflib.get_close_matches(slug, list(catalog), _SUGGESTIONS, _SUGGESTION_CUTOFF)
    hint = f"did you mean {', '.join(near)}?" if near else "see cstudy list"
    return f'unknown problem "{slug}"; {hint}'


def one_line(description: str | None) -> str | None:
    """A description as one line, or None for one that holds nothing."""
    if description is None:
        return None
    return " ".join(description.split()) or None


def parse_sets(document: object) -> tuple[ProblemSet, ...]:
    """The sets of a parsed `sets.yaml`, in the file's order; None is a file with none in it.
    Raises ConfigError naming everything wrong with it."""
    issues: list[str] = []
    sets = _parsed(document, issues)
    if issues:
        raise ConfigError(SETS_FILE, issues)
    return sets


def _parsed(document: object, issues: list[str]) -> tuple[ProblemSet, ...]:
    if document is None:
        return ()
    if not isinstance(document, Mapping):
        issues.append(f"the file must be a mapping with the key {SETS_KEY}")
        return ()
    top = cast(Mapping[object, object], document)
    issues.extend(_unknown_keys(top, (SETS_KEY,)))
    named = top.get(SETS_KEY)
    if named is None:
        return ()
    if not isinstance(named, Mapping):
        issues.append(f"{SETS_KEY} must be a mapping of names to sets")
        return ()
    entries = cast(Mapping[object, object], named)
    return tuple(_set(name, entry, issues) for name, entry in entries.items())


def _unknown_keys(mapping: Mapping[object, object], known: tuple[str, ...]) -> list[str]:
    return [f'unknown key "{key}"; use {" or ".join(known)}' for key in mapping if key not in known]


def _set(name: object, entry: object, issues: list[str]) -> ProblemSet:
    if not isinstance(name, str):
        issues.append(f"the set name {name} is not text: quote it")
        return ProblemSet(str(name))
    issue = set_name_issue(name)
    if issue is not None:
        issues.append(issue)
    if entry is None:
        return ProblemSet(name)
    if not isinstance(entry, Mapping):
        issues.append(f"set {name} must be a mapping with {' and '.join(_SET_KEYS)}")
        return ProblemSet(name)
    fields = cast(Mapping[object, object], entry)
    issues.extend(f"set {name}: {issue}" for issue in _unknown_keys(fields, _SET_KEYS))
    description = fields.get(DESCRIPTION_KEY)
    if description is not None and not isinstance(description, str):
        issues.append(f"set {name}: {DESCRIPTION_KEY} must be text")
        description = None
    slugs, targets = _entries(name, fields.get(PROBLEMS_KEY), issues)
    return ProblemSet(name, description, slugs, _in_order(slugs, targets))


def _entries(
    name: str, listed: object, issues: list[str]
) -> tuple[tuple[str, ...], dict[str, int]]:
    """The slugs, and the target level of each entry that names one."""
    if listed is None:
        return (), {}
    if not isinstance(listed, list):
        issues.append(f"set {name}: {PROBLEMS_KEY} must be a list of slugs")
        return (), {}
    slugs: list[str] = []
    targets: dict[str, int] = {}
    for entry in cast(list[object], listed):
        slug, level = _entry(name, entry, issues)
        if slug is None:
            continue
        if slug in slugs:
            issues.append(f"set {name} lists {slug} twice")
            continue
        slugs.append(slug)
        if level is not None:
            targets[slug] = level
    return tuple(slugs), targets


def _entry(name: str, entry: object, issues: list[str]) -> tuple[str | None, int | None]:
    """A slug, or `{slug: ..., level: ...}`; (None, None) for an entry that is neither."""
    if not isinstance(entry, Mapping):
        if isinstance(entry, str) and entry:
            return entry, None
        issues.append(f'set {name}: "{entry}" is not a slug')
        return None, None
    fields = cast(Mapping[object, object], entry)
    issues.extend(f"set {name}: {issue}" for issue in _unknown_keys(fields, _ENTRY_KEYS))
    slug = fields.get(SLUG_KEY)
    if not isinstance(slug, str) or not slug:
        issues.append(f'set {name}: an entry needs "{SLUG_KEY}", the slug of a problem or item')
        return None, None
    level = fields.get(LEVEL_KEY)
    if level is None:
        return slug, None
    if isinstance(level, bool) or not isinstance(level, int) or level < 1:
        issues.append(f"set {name}: the level of {slug} must be a whole number from 1")
        return slug, None
    return slug, level
