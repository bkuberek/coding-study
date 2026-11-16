"""`cstudy list` (docs/specs/cli.md#cstudy-list)."""

import json
from collections.abc import Collection, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_catalog_environment, load_environment
from coding_study.application.environment import Environment
from coding_study.application.list_items import ListedItem, list_entries
from coding_study.application.list_problems import (
    JdkNote,
    ListedLevels,
    ListedProblem,
    ListingContext,
    ProblemFilter,
    jdk_note,
    listing_context,
)
from coding_study.application.problem_sets import in_named_set, missing_slugs
from coding_study.domain.attempts import Attempt
from coding_study.domain.cases import JsonValue
from coding_study.domain.checked_by import CheckedBy, checked_by_of
from coding_study.domain.content_ids import ContentType, content_id
from coding_study.domain.errors import UsageError
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.jdk import SelectedJdk
from coding_study.domain.jdk_fit import jdk_range_of
from coding_study.domain.labels import LabelFilter, Labels
from coding_study.domain.level_passes import status_cell
from coding_study.domain.problem import (
    ContentStatus,
    Difficulty,
    Language,
    ListingKey,
    ProblemMeta,
    Track,
)
from coding_study.domain.profile import (
    ALL_DIMENSIONS,
    Counted,
    Dimension,
    ProfileEffect,
    ProfileLineKind,
    Widening,
    learner_profile,
    profile_line,
    widening_from,
)
from coding_study.domain.scheduling import ProblemStatus
from coding_study.domain.service_project import need_markers, service_of
from coding_study.domain.taxonomy import Scope
from coding_study.domain.value_text import truncate
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "list"
COLUMN_GAP = 2
SLUG_WIDTH = 16
DIFFICULTY_WIDTH = 6
PATTERN_WIDTH = 15
STATUS_WIDTH = max(
    *(len(status.label) for status in ProblemStatus),
    len(status_cell(ProblemStatus.MASTERED, (8, 9))),
)
"""Wide enough for `mastered 2/4`, a problem mastered through level 2 of 4."""
DUE_WIDTH = 10
NO_VALUE = "-"
NO_MATCH = "no problems match"
PROBLEMS_NOUN = "problems"
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
REFS_WIDTH = len(" ".join(REFERENCE_LABELS.values()))
_WIDTHS = (SLUG_WIDTH, DIFFICULTY_WIDTH, PATTERN_WIDTH, STATUS_WIDTH, DUE_WIDTH)
_WIDTHS_WITH_NEEDS = (*_WIDTHS, REFS_WIDTH)
TABLE_HEADER = ("SLUG", "DIFF", "PATTERN", "STATUS", "DUE", "REFS")
NEEDS_HEADER = "NEEDS"


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
        typer.Option("--kind", help="Only this kind of problem."),
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
    search: Annotated[
        str | None, typer.Option("--search", help="Problems whose slug or title holds this text.")
    ] = None,
    needs: Annotated[
        str | None,
        typer.Option(
            "--needs",
            metavar="WHAT",
            help="none keeps problems that need nothing beyond the language's toolchain; "
            "docker or a service's name keeps those that need it.",
        ),
    ] = None,
    checked: Annotated[
        CheckedBy | None,
        typer.Option("--checked-by", help="Only problems checked this way: tests or rubric."),
    ] = None,
    widen: Annotated[
        list[str] | None,
        typer.Option(
            "--widen",
            metavar="lang|role|domain|all",
            help="Ignore your learner profile in this dimension for this run; repeatable.",
        ),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="One JSON document instead of the table.")
    ] = False,
) -> None:
    """Browse problems with filters."""
    widening = explicit_widening(widen or (), language, role, domain)
    labels = LabelFilter(domain, role, scope)
    problem_filter = ProblemFilter(
        track,
        pattern,
        difficulty,
        problem_status(status),
        content,
        language,
        kind,
        labels,
        search=search,
        needs=needs,
        checked_by=checked,
    )
    load = load_catalog_environment if set_name is None else load_environment
    environment = load(Path.cwd(), command_environ(context), Path.home())
    problem_filter = in_named_set(environment, problem_filter, set_name)
    if set_name is None:
        profile = learner_profile(environment.config.profile, environment.workspace_languages)
        problem_filter = replace(problem_filter, profile=profile, widening=widening)
    if as_json:
        typer.echo(json.dumps(list_document(environment, problem_filter), indent=2))
        return
    entries = list_entries(environment, problem_filter)
    problems, items = entries.problems, entries.items
    rows = _in_order(
        problem_filter,
        [
            (item.summary.meta.slug, item.summary.meta.listing_key(), problem_cells(item))
            for item in problems
        ]
        + [(item.meta.slug, item.meta.listing_key(), item_cells(item)) for item in items],
    )
    needs_column = any(need_markers(item.summary.meta) for item in problems)
    if needs_column:
        needed = {item.summary.meta.slug: _needs_cell(item) for item in problems}
        rows = [(*cells, needed.get(cells[0], NO_VALUE)) for cells in rows]
    output = console(context)
    if rows:
        header = (*TABLE_HEADER, NEEDS_HEADER) if needs_column else TABLE_HEADER
        output.print(Text(table_row(header), style="bold"))
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
    line = _profile_line(entries.profile)
    if line is not None:
        output.print(Text(line, style="dim"))


def problem_status(text: str | None) -> ProblemStatus | None:
    """The status `--status` names: a value of `ProblemStatus`, with `-` allowed for `_`."""
    if text is None:
        return None
    try:
        return ProblemStatus(text.replace("-", "_"))
    except ValueError:
        raise UsageError(f"unknown status {text}; use {', '.join(ProblemStatus)}") from None


def list_document(environment: Environment, problem_filter: ProblemFilter) -> dict[str, JsonValue]:
    """`cstudy list --json`: the rows, in the order of the table."""
    entries = list_entries(environment, problem_filter)
    problems, items = entries.problems, entries.items
    listing = listing_context(environment)
    rows: list[tuple[str, ListingKey, JsonValue]] = [
        (
            problem.summary.meta.slug,
            problem.summary.meta.listing_key(),
            problem_entry(problem, listing),
        )
        for problem in problems
    ]
    rows += [(item.meta.slug, item.meta.listing_key(), item_entry(item, listing)) for item in items]
    document: dict[str, JsonValue] = {
        "today": listing.today.isoformat(),
        "entries": _in_order(problem_filter, rows),
        "selected_jdk": selected_jdk_value(environment.jdk.selected()),
        "profile": profile_value(entries.profile),
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


def profile_value(effect: ProfileEffect) -> JsonValue:
    """`profile` of the documents: the profile values that narrowed the rows, null for a dimension
    that did not, and how many rows the profile hid (cli.md#explicit-filters-and-widening)."""
    narrowed = effect.narrowed
    hidden: JsonValue = {"problems": effect.hidden}
    return {
        "languages": _values_value(narrowed.languages),
        "job_roles": _values_value(narrowed.job_roles),
        "domains": _values_value(narrowed.domains),
        "hidden": hidden,
    }


def _values_value(values: tuple[str, ...] | None) -> JsonValue:
    return None if values is None else [str(value) for value in values]


def _profile_line(effect: ProfileEffect) -> str | None:
    counts = [Counted(effect.shown, effect.total, PROBLEMS_NOUN)]
    return profile_line(ProfileLineKind.SHOWS, counts, effect.narrowed)


def explicit_widening(
    values: Sequence[str],
    language: Language | None,
    role: str | None,
    domain: str | None,
    widenable: Collection[Dimension] = ALL_DIMENSIONS,
) -> Widening:
    """`--widen`, plus the dimension of each explicit filter, which replaces the profile there.
    Raises UsageError for a value that is none of those `widenable` names and `all`."""
    try:
        widening = widening_from(values, widenable)
    except ValueError as error:
        raise UsageError(str(error)) from None
    explicit = (
        (Dimension.LANGUAGES, language),
        (Dimension.JOB_ROLES, role),
        (Dimension.DOMAINS, domain),
    )
    return widening.plus(*(dimension for dimension, given in explicit if given is not None))


def _in_order[Row](
    problem_filter: ProblemFilter, rows: list[tuple[str, ListingKey, Row]]
) -> list[Row]:
    """Each row of `(slug, key, row)` in one list: the order of `cstudy list`
    (docs/specs/compatibility.md#order), or the set's order under `--set`."""
    chosen = problem_filter.in_set
    if chosen is not None:
        ordered = sorted(rows, key=lambda row: chosen.position_of(row[0]))
    else:
        ordered = sorted(rows, key=lambda row: row[1])
    return [row for _, _, row in ordered]


def problem_entry(problem: ListedProblem, listing: ListingContext) -> dict[str, JsonValue]:
    meta = problem.summary.meta
    kind = entry_kind(meta.kind)
    return {
        "id": content_id(ContentType.PROBLEM, meta.slug),
        "slug": meta.slug,
        "title": meta.title,
        "track": meta.track.value,
        "kind": kind.value,
        "checked_by": checked_by_value(checked_by_of(kind, problem.summary.has_rubric)),
        "difficulty": meta.difficulty.value,
        "patterns": list(meta.patterns),
        **_label_fields(meta.labels),
        "languages": [language.value for language in problem.summary.reference_languages],
        "content": meta.status.value,
        "source": WORKSPACE_SOURCE if meta.workspace else CATALOG_SOURCE,
        "status": problem.status.value,
        "levels": _levels_value(problem.levels),
        "due_on": problem.due_on.isoformat() if problem.due_on else None,
        "in_progress": _in_progress(listing, meta.slug),
        "jdk": _jdk_range_value(meta),
        "requires": _requires_value(meta),
    }


def checked_by_value(checked: tuple[CheckedBy, ...]) -> JsonValue:
    return [how.value for how in checked]


def _requires_value(meta: ProblemMeta) -> JsonValue:
    """What a service project depends on, as its manifest declares it; null for other problems."""
    service = service_of(meta)
    if service is None:
        return None
    requires = service.requires
    sizes = requires.sizes
    return {
        "docker": True,
        "services": list(requires.services),
        "mocks": [mock.name for mock in service.mocks],
        "lock": requires.lock,
        "install_mb": sizes.install_mb,
        "images_mb": dict(sizes.images_mb),
        "memory_mb": sizes.memory_mb,
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
        "id": content_id(ContentType.PROBLEM, meta.slug),
        "slug": meta.slug,
        "title": meta.title,
        "track": meta.track.value,
        "kind": meta.kind.value,
        "checked_by": checked_by_value(checked_by_of(meta.kind, has_rubric=True)),
        "difficulty": meta.difficulty.value,
        "patterns": [],
        **_label_fields(meta.labels),
        "languages": [],
        "content": meta.status.value,
        "source": CATALOG_SOURCE,
        "status": item.status.value,
        "levels": None,
        "due_on": item.due_on.isoformat() if item.due_on else None,
        "in_progress": _in_progress(listing, meta.slug),
        "jdk": None,
        "requires": None,
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
        meta.slug,
        meta.difficulty,
        meta.patterns[0] if meta.patterns else NO_VALUE,
        status_cell(item.status, _mastered_of(item.levels)),
        item.due_on.isoformat() if item.due_on else NO_VALUE,
        references or NO_VALUE,
    )


def _mastered_of(levels: ListedLevels | None) -> tuple[int, int] | None:
    return None if levels is None else (levels.mastered, levels.last)


def _levels_value(levels: ListedLevels | None) -> JsonValue:
    if levels is None:
        return None
    return {"last": levels.last, "passed": levels.passed, "mastered": levels.mastered}


def _needs_cell(item: ListedProblem) -> str:
    return " ".join(need_markers(item.summary.meta)) or NO_VALUE


def _reference_label(language: Language, item: ListedProblem) -> str:
    label = REFERENCE_LABELS[language]
    return f"{label}{MARK}" if language in item.blocked else label


def _footer(note: JdkNote) -> str:
    """`! java, kt: not run on JDK 27 (JAVA_HOME): cstudy supports JDK 21 to 26`."""
    labels = ", ".join(REFERENCE_LABELS[language] for language in note.languages)
    return f"{MARK} {labels}: {note.reason}"


def item_cells(item: ListedItem) -> tuple[str, ...]:
    """A rubric problem has no pattern or references; its track takes the pattern column."""
    meta = item.meta
    due = item.due_on.isoformat() if item.due_on else NO_VALUE
    return (meta.slug, meta.difficulty, meta.track, item.status.label, due, NO_VALUE)


def table_row(cells: tuple[str, ...]) -> str:
    widths = _WIDTHS_WITH_NEEDS if len(cells) == len(_WIDTHS_WITH_NEEDS) + 1 else _WIDTHS
    padded = (
        _fit(cell, width).ljust(width + COLUMN_GAP)
        for cell, width in zip(cells, widths, strict=False)
    )
    return "".join(padded) + cells[-1]


def _fit(cell: str, width: int) -> str:
    """A value too long for its column ends in "..." one character short of the column."""
    return cell if len(cell) <= width else truncate(cell, width - 1)
