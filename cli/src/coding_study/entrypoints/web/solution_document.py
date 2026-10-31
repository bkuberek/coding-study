"""The solution document (docs/specs/web-ui.md#solutions): what `cstudy solution` pages, as
Markdown, with its HTML. The order and wording follow the command's: the title, the rubric, the
overview, then each approach's section and its code, a project's reference files, or a broken
reference."""

import re
from collections.abc import Iterator

from coding_study.application.item_solution import ItemSolutionView
from coding_study.application.reveal_solution import (
    ApproachSolution,
    BrokenSolution,
    SolutionView,
)
from coding_study.domain.cases import JsonValue
from coding_study.domain.items import REFERENCE_FILE, EntryKind, entry_kind
from coding_study.domain.problem import Language
from coding_study.domain.problem_files import RUBRIC_FILE
from coding_study.domain.project_reference import ReferenceFile
from coding_study.entrypoints.commands.solution import DIFF_LEXER, LEXERS
from coding_study.entrypoints.web.documents import markdown_document

FENCE = "```"
BACKTICK_RUNS = re.compile(r"`+")


def solution_document(view: SolutionView, marked_attempt_id: int | None) -> dict[str, JsonValue]:
    meta = view.meta
    return {
        "slug": meta.slug,
        "kind": entry_kind(meta.kind).value,
        "language": view.language.value,
        "approaches": [part.approach.id for part in view.approaches],
        "marked_attempt_id": marked_attempt_id,
        **markdown_document(_joined(_problem_blocks(view))),
    }


def item_solution_document(view: ItemSolutionView) -> dict[str, JsonValue]:
    """An item's rubric and reference: revealing them never lowers its grade, so no attempt
    counts as marked."""
    meta = view.meta
    blocks = [f"# {meta.title} · {meta.track}"]
    for name, text in ((RUBRIC_FILE, view.rubric), (REFERENCE_FILE, view.reference)):
        blocks.append(text if text else _note(f"no {name}"))
    return {
        "slug": meta.slug,
        "kind": EntryKind.ITEM.value,
        "language": None,
        "approaches": [],
        "marked_attempt_id": None,
        **markdown_document(_joined(blocks)),
    }


def _problem_blocks(view: SolutionView) -> Iterator[str]:
    yield f"# {view.meta.title} · {view.language}"
    if view.rubric:
        yield view.rubric
    if view.overview:
        yield view.overview
    for part in view.approaches:
        yield from _approach(part, view.language)
    for file in view.project_files:
        yield from _reference_file(file, view.language)
    if view.broken is not None:
        yield from _broken(view.broken, view.language)


def _approach(part: ApproachSolution, language: Language) -> Iterator[str]:
    yield part.explanation or _note(f"{part.approach.id}: no explanation")
    if part.code is not None:
        yield _fenced(part.code, LEXERS[language])
    elif part.available and language not in part.available:
        yield _note(f"no {language} reference; available: {', '.join(part.available)}")


def _reference_file(file: ReferenceFile, language: Language) -> Iterator[str]:
    """An added file in full, a changed one as its diff against the starter."""
    yield f"**{file.path}** ({'added' if file.added else 'changed'})"
    yield _fenced(file.text, LEXERS[language] if file.added else DIFF_LEXER)


def _broken(part: BrokenSolution, language: Language) -> Iterator[str]:
    broken = part.broken
    yield f"**broken reference {broken.id}: {broken.bug}**"
    if part.code is not None:
        yield _fenced(part.code, LEXERS[language])
    elif part.available:
        yield _note(f"no {language} file for {broken.id}; available: {', '.join(part.available)}")
    if part.explanation:
        yield part.explanation


def _fenced(code: str, lexer: str) -> str:
    """A fenced block one backtick longer than the longest run in `code`, so no line of the code
    can close it."""
    longest = max((len(run) for run in BACKTICK_RUNS.findall(code)), default=0)
    fence = "`" * max(len(FENCE), longest + 1)
    body = code.rstrip("\n")
    return f"{fence}{lexer}\n{body}\n{fence}"


def _note(text: str) -> str:
    return f"_{text}_"


def _joined(blocks: Iterator[str] | list[str]) -> str:
    return "\n\n".join(block.strip("\n") for block in blocks) + "\n"
