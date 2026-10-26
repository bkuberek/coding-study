""".statements/<slug>.md for a non-autograded item (docs/specs/cli.md#cstudy-start).

`cstudy start` writes it; `cstudy show` prints the same text without writing it.
"""

from coding_study.application.environment import Environment
from coding_study.domain import layout
from coding_study.domain.item_statement import (
    Change,
    ChangeFile,
    ItemStatementParts,
    render_item_statement,
)
from coding_study.domain.items import (
    CHANGE_DIRECTORY,
    CHANGE_FILE,
    PROMPT_FILE,
    GuideLink,
    ItemMeta,
    guide_path,
)


def guide_links(environment: Environment, meta: ItemMeta) -> tuple[GuideLink, ...]:
    """The item's study-guide references whose file exists under the user's study-guides root,
    in `references.study_guides` order."""
    links: list[GuideLink] = []
    for reference in meta.references.study_guides:
        location = environment.study_guides.locate(guide_path(reference))
        if location is not None:
            links.append(GuideLink(reference, location))
    return tuple(links)


def item_statement_text(
    environment: Environment, meta: ItemMeta, guides: tuple[GuideLink, ...]
) -> str:
    items = environment.items
    change = Change(
        diff=items.read_text(meta.slug, CHANGE_FILE),
        files=tuple(
            ChangeFile(name, items.read_text(meta.slug, f"{CHANGE_DIRECTORY}/{name}") or "")
            for name in items.file_names(meta.slug, CHANGE_DIRECTORY)
        ),
    )
    parts = ItemStatementParts(items.read_text(meta.slug, PROMPT_FILE), change, guides)
    return render_item_statement(meta, parts)


def write_item_statement(
    environment: Environment, meta: ItemMeta, guides: tuple[GuideLink, ...]
) -> str:
    """Writes the statement file; returns its path."""
    path = layout.statement_path(meta.slug)
    environment.workspace.write_text(path, item_statement_text(environment, meta, guides))
    return path
