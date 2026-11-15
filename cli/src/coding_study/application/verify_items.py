"""`cstudy verify` on rubric-checked problems (docs/specs/authoring.md#rubric-checked-problems):
static checks only.
"""

from collections.abc import Collection, Iterator
from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.domain.errors import ContentError
from coding_study.domain.item_checks import ItemContent, item_ready_problems, item_static_checks
from coding_study.domain.items import (
    CHANGE_DIRECTORY,
    CHANGE_FILE,
    PROMPT_FILE,
    REFERENCE_FILE,
    TEMPLATE_FILE,
    ItemMeta,
)
from coding_study.domain.problem import Track
from coding_study.domain.problem_files import META_FILE, RUBRIC_FILE


@dataclass(frozen=True, slots=True)
class ItemSelection:
    slugs: tuple[str, ...] = ()
    """Empty: every rubric problem."""
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
    """`known_slugs` are every problem slug, for the `related` warnings."""
    verified: list[ItemVerification] = []
    for slug in environment.items.slugs():
        if selection.slugs and slug not in selection.slugs:
            continue
        verification = _verify(environment, slug, selection, known_slugs)
        if verification is not None:
            verified.append(verification)
    return tuple(verified)


def _verify(
    environment: Environment, slug: str, selection: ItemSelection, known_slugs: Collection[str]
) -> ItemVerification | None:
    """None when the problem is outside `selection.track`."""
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
            yield f'{directory}/{META_FILE}: related: "{slug}" is not a problem (yet)'
