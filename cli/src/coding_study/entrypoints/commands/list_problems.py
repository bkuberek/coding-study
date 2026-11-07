"""`cstudy list` (docs/specs/cli.md#cstudy-list)."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment, load_environment
from coding_study.application.environment import Environment
from coding_study.application.list_items import ListedItem, list_items
from coding_study.application.list_problems import (
    JdkNote,
    ListedProblem,
    ListingContext,
    ProblemFilter,
    jdk_note,
    list_problems,
    listing_context,
)
from coding_study.application.problem_sets import in_named_set, missing_slugs
from coding_study.domain.attempts import Attempt
from coding_study.domain.cases import JsonValue
from coding_study.domain.errors import UsageError
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.jdk import SelectedJdk
from coding_study.domain.jdk_fit import jdk_range_of
from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.problem import ContentStatus, Difficulty, Language, ProblemMeta, Track
from coding_study.domain.scheduling import ProblemStatus
from coding_study.domain.taxonomy import Scope
from coding_study.domain.value_text import truncate
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "list"
COLUMN_GAP = 2
ID_WIDTH = 4
SLUG_WIDTH = 16
DIFFICULTY_WIDTH = 6
PATTERN_WIDTH = 15
STATUS_WIDTH = max(len(status.label) for status in ProblemStatus)
DUE_WIDTH = 10
NO_VALUE = "-"
NO_MATCH = "no problems match"
MISSING_NOTE = "missing from the catalog"
MARK = "!"
"""After the label of a language the selected JDK cannot run, and before the footer's list."""
CATALOG_SOURCE = "catalog"
WORKSPACE_SOURCE = "workspace"
REFERENCE_LABELS = {
    Language.PYTHON: "py",
    Language.TYPESCRIPT: "ts",
    Language.JAVA: "java",
    Language.KOTLIN: "kt",
    Language.GO: "go",
    Language.RUST: "rs",
}
_WIDTHS = (ID_WIDTH, SLUG_WIDTH, DIFFICULTY_WIDTH, PATTERN_WIDTH, STATUS_WIDTH, DUE_WIDTH)
TABLE_HEADER = ("ID", "SLUG", "DIFF", "PATTERN", "STATUS", "DUE", "REFS")


def register(app: typer.Typer) -> None:
    add_command(app, list_command, NAME)


def list_command(
    context: typer.Context,
    set_name: Annotated[
        str | None, typer.Option("--set", help="Only this set of yours, in its order.")
    ] = None,
    track: Annotated[Track | None, typer.Option("--track", help="Only this track.")] = None,
    pattern: Annotated[
        str | None, typer.Option("--pattern", help="Problems that list this pattern.")
    ] = None,
    difficulty: Annotated[
        Difficulty | None, typer.Option("--difficulty", help="Only this difficulty.")
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Only problems in this status: new, in_progress (or in-progress), attempted, "
            "passed, due or mastered.",
        ),
    ] = None,
    content: Annotated[
        ContentStatus | None, typer.Option("--content", help="Content status: draft or ready.")
    ] = None,
    language: Annotated[
        Language | None, typer.Option("--lang", help="Problems with a reference in it.")
    ] = None,
    kind: Annotated[
        EntryKind | None,
        typer.Option("--kind", help="Only this kind of problem, or item for the items."),
    ] = None,
    domain: Annotated[
        str | None, typer.Option("--domain", help="Problems that list this domain.")
    ] = None,
    role: Annotated[
        str | None, typer.Option("--role", help="Problems that list this job role.")
    ] = None,
    scope: Annotated[
        Scope | None, typer.Option("--scope", help="Only this scope: function, project or system.")
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the table.")
    ] = False,
) -> None:
    """Browse problems with filters."""
    labels = LabelFilter(domain, role, scope)
    problem_filter = ProblemFilter(
        track, pattern, difficulty, problem_status(status), content, language, kind, labels
    )
    load = load_catalog_environment if set_name is None else load_environment
    environment = load(Path.cwd(), command_environ(context), Path.home())
    problem_filter = in_named_set(environment, problem_filter, set_name)
    if as_json:
        typer.echo(json.dumps(list_document(environment, problem_filter), indent=2))
        return
    problems, items = _entries(environment, problem_filter)
    rows = _in_order(
        problem_filter,
        [(item.summary.meta.slug, problem_cells(item)) for item in problems]
        + [(item.meta.slug, item_cells(item)) for item in items],
    )
    output = console(context)
    if rows:
        output.print(Text(table_row(TABLE_HEADER), style="bold"))
    else:
        output.print(NO_MATCH)
    for cells in rows:
        output.print(Text(table_row(cells)))
    note = jdk_note(environment, problems)
    if note is not None:
        output.print(Text(_footer(note)))
    if problem_filter.in_set is not None:
        missing = missing_slugs(environment, problem_filter.in_set)
        if missing:
            output.print(Text(f"{MISSING_NOTE}: {', '.join(missing)}"))


def problem_status(text: str | None) -> ProblemStatus | None:
    """The status `--status` names: a value of `ProblemStatus`, with `-` allowed for `_`."""
    if text is None:
        return None
    try:
        return ProblemStatus(text.replace("-", "_"))
    except ValueError:
        raise UsageError(f"unknown status {text}; use {', '.join(ProblemStatus)}") from None


def list_document(environment: Environment, problem_filter: ProblemFilter) -> dict[str, JsonValue]:
    """`cstudy list --json`: the rows, problems then items."""
    problems, items = _entries(environment, problem_filter)
    listing = listing_context(environment)
    rows: list[tuple[str, JsonValue]] = [
        (problem.summary.meta.slug, problem_entry(problem, listing)) for problem in problems
    ]
    rows += [(item.meta.slug, item_entry(item, listing)) for item in items]
    document: dict[str, JsonValue] = {
        "today": listing.today.isoformat(),
        "entries": _in_order(problem_filter, rows),
        "selected_jdk": selected_jdk_value(environment.jdk.selected()),
    }
    chosen = problem_filter.in_set
    if chosen is not None:
        missing: list[JsonValue] = list(missing_slugs(environment, chosen))
        document["set"] = {"name": chosen.name, "missing": missing}
    return document


def selected_jdk_value(selected: SelectedJdk | None) -> JsonValue:
    """The selected JDK as the documents hold it; null when none is found."""
    if selected is None:
        return None
    return {
        "version": selected.version,
        "feature": selected.feature,
        "source": selected.source.value,
        "supported": selected.supported,
    }


def _entries(
    environment: Environment, problem_filter: ProblemFilter
) -> tuple[tuple[ListedProblem, ...], tuple[ListedItem, ...]]:
    return list_problems(environment, problem_filter), list_items(environment, problem_filter)


def _in_order[Row](problem_filter: ProblemFilter, rows: list[tuple[str, Row]]) -> list[Row]:
    """Each row of `(slug, row)`: problems then items, or the set's order under `--set`."""
    chosen = problem_filter.in_set
    if chosen is not None:
        rows = sorted(rows, key=lambda row: chosen.position_of(row[0]))
    return [row for _, row in rows]


def problem_entry(problem: ListedProblem, listing: ListingContext) -> dict[str, JsonValue]:
    meta = problem.summary.meta
    return {
        "id": meta.id,
        "slug": meta.slug,
        "title": meta.title,
        "track": meta.track.value,
        "kind": entry_kind(meta.kind).value,
        "difficulty": meta.difficulty.value,
        "patterns": list(meta.patterns),
        **_label_fields(meta.labels),
        "languages": [language.value for language in problem.summary.reference_languages],
        "content": meta.status.value,
        "source": WORKSPACE_SOURCE if meta.workspace else CATALOG_SOURCE,
        "status": problem.status.value,
        "due_on": problem.due_on.isoformat() if problem.due_on else None,
        "in_progress": _in_progress(listing, meta.slug),
        "jdk": _jdk_range_value(meta),
    }


def _label_fields(labels: Labels) -> dict[str, JsonValue]:
    """`domains`, `job_roles` and `scope`; a workspace problem without labels has none."""
    return {
        "domains": list(labels.domains),
        "job_roles": list(labels.job_roles),
        "scope": labels.scope.value if labels.scope else None,
    }


def _jdk_range_value(meta: ProblemMeta) -> JsonValue:
    wanted = jdk_range_of(meta)
    return None if wanted is None else {"min": wanted.minimum, "max": wanted.maximum}


def item_entry(item: ListedItem, listing: ListingContext) -> dict[str, JsonValue]:
    meta = item.meta
    return {
        "id": None,
        "slug": meta.slug,
        "title": meta.title,
        "track": meta.track.value,
        "kind": EntryKind.ITEM.value,
        "difficulty": meta.difficulty.value,
        "patterns": [],
        **_label_fields(meta.labels),
        "languages": [],
        "content": meta.status.value,
        "source": CATALOG_SOURCE,
        "status": item.status.value,
        "due_on": item.due_on.isoformat() if item.due_on else None,
        "in_progress": _in_progress(listing, meta.slug),
        "jdk": None,
    }


def _in_progress(listing: ListingContext, slug: str) -> list[JsonValue]:
    return [_attempt_value(attempt) for attempt in listing.in_progress.get(slug, ())]


def _attempt_value(attempt: Attempt) -> JsonValue:
    return {
        "attempt_id": attempt.id,
        "language": attempt.language.value if attempt.language else None,
        "mode": attempt.mode.value,
    }


def problem_cells(item: ListedProblem) -> tuple[str, ...]:
    meta = item.summary.meta
    references = " ".join(
        _reference_label(language, item) for language in item.summary.reference_languages
    )
    return (
        meta.id,
        meta.slug,
        meta.difficulty,
        meta.patterns[0] if meta.patterns else NO_VALUE,
        item.status.label,
        item.due_on.isoformat() if item.due_on else NO_VALUE,
        references or NO_VALUE,
    )


def _reference_label(language: Language, item: ListedProblem) -> str:
    label = REFERENCE_LABELS[language]
    return f"{label}{MARK}" if language in item.blocked else label


def _footer(note: JdkNote) -> str:
    """`! java, kt: not run on JDK 27 (JAVA_HOME): cstudy supports JDK 21 to 26`."""
    labels = ", ".join(REFERENCE_LABELS[language] for language in note.languages)
    return f"{MARK} {labels}: {note.reason}"


def item_cells(item: ListedItem) -> tuple[str, ...]:
    """Items have no id, pattern or references; their track takes the pattern column."""
    meta = item.meta
    due = item.due_on.isoformat() if item.due_on else NO_VALUE
    return (NO_VALUE, meta.slug, meta.difficulty, meta.track, item.status.label, due, NO_VALUE)


def table_row(cells: tuple[str, ...]) -> str:
    padded = (
        _fit(cell, width).ljust(width + COLUMN_GAP)
        for cell, width in zip(cells, _WIDTHS, strict=False)
    )
    return "".join(padded) + cells[-1]


def _fit(cell: str, width: int) -> str:
    """A value too long for its column ends in "..." one character short of the column."""
    return cell if len(cell) <= width else truncate(cell, width - 1)
