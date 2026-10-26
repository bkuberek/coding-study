"""`cstudy verify` on non-autograded items (docs/specs/authoring.md#items): static checks only.

Slugs are unique across problems/ and tracks/ (S2), because progress.db keys on the slug. Like
problems, a duplicated slug is verified once, in its first directory, which reports the others.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator
from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.domain.errors import ContentError
from coding_study.domain.item_checks import ItemContent, item_ready_problems, item_static_checks
from coding_study.domain.items import (
    CHANGE_DIRECTORY,
    CHANGE_FILE,
    ITEM_FILE,
    PROMPT_FILE,
    REFERENCE_FILE,
    TEMPLATE_FILE,
    ItemMeta,
)
from coding_study.domain.problem import Track
from coding_study.domain.problem_files import RUBRIC_FILE


@dataclass(frozen=True, slots=True)
class ItemSelection:
    slugs: tuple[str, ...] = ()
    """Empty: every item."""
    track: Track | None = None
    require_ready: bool = False


@dataclass(frozen=True, slots=True)
class ItemVerification:
    directory: str
    static_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    ready_errors: tuple[str, ...] = ()


def verify_items(
    environment: Environment, selection: ItemSelection, known_slugs: Collection[str]
) -> tuple[ItemVerification, ...]:
    """`known_slugs` are every problem and item slug, for the `related` warnings."""
    conflicts = _SlugConflicts(environment)
    verified: list[ItemVerification] = []
    for slug in dict.fromkeys(environment.items.slugs()):
        if selection.slugs and slug not in selection.slugs:
            continue
        verification = _verify(environment, slug, selection, known_slugs)
        if verification is not None:
            duplicates = (*conflicts.of_item(slug), *verification.static_errors)
            verified.append(replace(verification, static_errors=duplicates))
    return tuple(verified)


def problem_slug_conflicts(environment: Environment) -> dict[str, tuple[str, ...]]:
    """S2 for problem slugs that an item also uses, keyed by slug."""
    conflicts = _SlugConflicts(environment)
    return {
        slug: issues
        for slug in dict.fromkeys(environment.files.slugs())
        if (issues := conflicts.of_problem(slug))
    }


class _SlugConflicts:
    def __init__(self, environment: Environment) -> None:
        files, items = environment.files, environment.items
        problem_directories = (f"{files.directory}/{name}" for name in files.directory_names())
        self._problems = _by_slug(zip(files.slugs(), problem_directories, strict=True))
        self._items = _by_slug(zip(items.slugs(), items.directories(), strict=True))

    def of_problem(self, slug: str) -> tuple[str, ...]:
        """The first problem directory with `slug` against every item that uses it."""
        problems = self._problems.get(slug, [])
        if not problems:
            return ()
        return _messages(problems[0], slug, self._items.get(slug, []))

    def of_item(self, slug: str) -> tuple[str, ...]:
        """The first item directory with `slug` against every other directory that uses it."""
        items = self._items[slug]
        return _messages(items[0], slug, [*self._problems.get(slug, []), *items[1:]])


def _by_slug(pairs: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    directories: defaultdict[str, list[str]] = defaultdict(list)
    for slug, directory in pairs:
        directories[slug].append(directory)
    return directories


def _messages(directory: str, slug: str, others: list[str]) -> tuple[str, ...]:
    return tuple(f'{directory}: slug "{slug}" is also used by {other}' for other in others)


def _verify(
    environment: Environment, slug: str, selection: ItemSelection, known_slugs: Collection[str]
) -> ItemVerification | None:
    """None when the item is outside `selection.track`."""
    directory = environment.items.item_directory(slug)
    try:
        meta = environment.items.load(slug)
    except ContentError as error:
        return ItemVerification(directory, static_errors=tuple(map(str, error.issues)))
    if selection.track not in (None, meta.track):
        return None
    content = _item_content(environment, directory, meta)
    return ItemVerification(
        directory=directory,
        static_errors=tuple(map(str, item_static_checks(content))),
        warnings=tuple(_related_warnings(directory, meta, known_slugs)),
        ready_errors=item_ready_problems(content) if selection.require_ready else (),
    )


def _item_content(environment: Environment, directory: str, meta: ItemMeta) -> ItemContent:
    items = environment.items
    return ItemContent(
        directory=directory,
        meta=meta,
        prompt=items.read_text(meta.slug, PROMPT_FILE),
        rubric=items.read_text(meta.slug, RUBRIC_FILE),
        reference=items.read_text(meta.slug, REFERENCE_FILE),
        template=items.read_text(meta.slug, TEMPLATE_FILE),
        change=items.read_text(meta.slug, CHANGE_FILE),
        change_files=items.file_names(meta.slug, CHANGE_DIRECTORY),
    )


def _related_warnings(
    directory: str, meta: ItemMeta, known_slugs: Collection[str]
) -> Iterator[str]:
    for slug in meta.related:
        if slug not in known_slugs:
            yield f'{directory}/{ITEM_FILE}: related: "{slug}" is not a problem or item (yet)'
