"""The rendered statement in `.statements/<slug>.md` (docs/specs/authoring.md#problemmd).

Rendering keeps problem.md's sections, replaces each `<!-- case: <id> -->` marker with that case's
input and expected output (so example data has one source, tests.json), never shows hints, and
hides the locked levels of progressive problems.
"""

import re
from collections.abc import Iterator, Sequence

from coding_study.domain.cases import Case, FunctionInput, JsonValue, OperationSequence
from coding_study.domain.levels import LevelProgress, level_heading, level_progress
from coding_study.domain.markdown import MarkdownDocument, MarkdownSection
from coding_study.domain.problem import ComparatorType, Problem, ProblemMeta
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Signature,
    output_type,
)
from coding_study.domain.stress_statement import CONCURRENCY_SECTION, stress_table
from coding_study.domain.type_dsl import ValueType
from coding_study.domain.value_text import display_text, json_text

HINTS_SECTION = "Hints"
EXAMPLES_SECTION = "Examples"
FOOTER = "<!-- Rendered by cstudy from the problem's problem.md; edits here are overwritten. -->"
_EXAMPLE_MARKER = re.compile(r"\s*<!--\s*case:\s*(?P<case_id>\S+?)\s*-->\s*")


def example_marker(line: str) -> str | None:
    """The case id of a `<!-- case: <id> -->` line, or None for any other line."""
    marker = _EXAMPLE_MARKER.fullmatch(line)
    return marker["case_id"] if marker else None


def render_statement(
    problem: Problem, problem_markdown: str | None, unlocked_level: int | None
) -> str:
    """`problem_markdown` None renders the title, metadata and the visible cases as examples.

    Progressive problems show levels 1 to `unlocked_level` (level 1 when None); a notice stands
    in for the locked levels. Other problems ignore `unlocked_level`.
    """
    meta = problem.meta
    view = _StatementView(meta, level_progress(meta, unlocked_level))
    if problem_markdown is None:
        lines = list(view.from_cases(problem.cases))
    else:
        lines = list(view.from_markdown(MarkdownDocument(problem_markdown), problem.cases))
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join((*lines, "", FOOTER)) + "\n"


def metadata_line(meta: ProblemMeta) -> str:
    parts = (meta.difficulty, meta.track, ", ".join(meta.patterns))
    return " · ".join(part for part in parts if part)


class _StatementView:
    def __init__(self, meta: ProblemMeta, progress: LevelProgress | None) -> None:
        self._meta = meta
        self._progress = progress

    def from_markdown(self, document: MarkdownDocument, cases: Sequence[Case]) -> Iterator[str]:
        by_id = {case.id: case for case in cases}
        locked = self._locked_sections(document)
        hidden = {
            index
            for section in (document.section(HINTS_SECTION), *locked)
            for index in _line_range(section)
        }
        notice_at = locked[0].start if locked else None
        table = stress_table(_problem_of(self._meta, cases))
        concurrency = document.section(CONCURRENCY_SECTION)
        table_at = concurrency.end if table and concurrency else None
        if document.title is None:
            yield from (f"# {self._meta.title}", "", self._metadata(), "")
        title_seen = False
        for index, line in enumerate(document.lines):
            if index == notice_at:
                yield from (self._locked_notice(), "")
            if index == table_at:
                yield from (*table, "")
            if index in hidden:
                continue
            case = by_id.get(example_marker(line) or "")
            yield from example_block(self._meta, case) if case else (line,)
            if not title_seen and line.startswith("# "):
                title_seen = True
                yield from ("", self._metadata())
        if table_at == len(document.lines):
            yield from ("", *table)

    def from_cases(self, cases: Sequence[Case]) -> Iterator[str]:
        yield from (f"# {self._meta.title}", "", self._metadata())
        visible = [case for case in cases if case.visible]
        progress = self._progress
        if progress is None:
            yield from ("", f"## {EXAMPLES_SECTION}")
            yield from self._examples(visible)
            return
        for number in range(1, progress.unlocked + 1):
            yield from ("", f"## Level {number}: {progress.title(number)}")
            yield from self._examples([case for case in visible if case.level == number])
        if progress.locked:
            yield from ("", self._locked_notice())

    def _examples(self, cases: Sequence[Case]) -> Iterator[str]:
        for number, case in enumerate(cases, start=1):
            yield from ("", f"### Example {number}", "", *example_block(self._meta, case))

    def _metadata(self) -> str:
        progress = self._progress
        if progress is None:
            return metadata_line(self._meta)
        return f"{metadata_line(self._meta)} · level {progress.unlocked} of {progress.last}"

    def _locked_sections(self, document: MarkdownDocument) -> list[MarkdownSection]:
        progress = self._progress
        if progress is None:
            return []
        return [
            section
            for section in document.sections(2)
            if (number := level_heading(section.title)) is not None and number in progress.locked
        ]

    def _locked_notice(self) -> str:
        progress = self._progress
        assert progress is not None
        locked, passing = progress.locked, f"Pass every case up to level {progress.unlocked}"
        opener = f"`{progress.opened_by}`"
        if len(locked) == 1:
            return f"> Level {locked[0]} is locked. {passing} with {opener} to unlock it."
        return (
            f"> Levels {locked[0]} to {locked[-1]} are locked. {passing} with {opener} to "
            "unlock the next one."
        )


def _problem_of(meta: ProblemMeta, cases: Sequence[Case]) -> Problem:
    return Problem(meta, tuple(cases))


def _line_range(section: MarkdownSection | None) -> range:
    return range(section.start, section.end) if section else range(0)


def example_block(meta: ProblemMeta, case: Case) -> tuple[str, ...]:
    """A fenced block with the case's input and expected output.

    Values print as JSON, except `decimal` and `date` values, which print unquoted by the types
    the signature declares (`premium = 2500.50`, `[2026-01-01, 2026-07-01]`).
    """
    signature = meta.signature
    return ("```text", *_input_lines(signature, case), *_output_lines(meta, case), "```")


def _input_lines(signature: Signature, case: Case) -> tuple[str, ...]:
    match case.input:
        case FunctionInput(arguments=arguments):
            types = _function_param_types(signature)
            listed = ", ".join(
                f"{name} = {display_text(value, types.get(name))}"
                for name, value in arguments.items()
            )
            return (f"Input:  {listed}",)
        case OperationSequence(ops=ops, args=args):
            rows = (
                _typed_list_text(arguments, _operation_param_types(signature, ops, index))
                for index, arguments in enumerate(args)
            )
            return (
                f"Operations: {json_text(list(ops))}",
                f"Arguments:  [{', '.join(rows)}]",
            )
        case _:
            return ()


def _output_lines(meta: ProblemMeta, case: Case) -> tuple[str, ...]:
    label = "Output:     " if isinstance(case.input, OperationSequence) else "Output: "
    if case.expected is None:
        return (f"{label}any valid answer",)
    is_checker = meta.comparator.type is ComparatorType.CHECKER
    suffix = "  (one valid answer)" if is_checker else ""
    return (f"{label}{_expected_text(meta.signature, case, case.expected.value)}{suffix}",)


def _expected_text(signature: Signature, case: Case, expected: JsonValue) -> str:
    """Design cases expect one output per operation, typed by that method's return."""
    sequence = case.input
    if isinstance(signature, FunctionSignature) and isinstance(sequence, FunctionInput):
        return display_text(expected, output_type(signature))
    if not (
        isinstance(signature, ClassSignature)
        and isinstance(sequence, OperationSequence)
        and isinstance(expected, list)
    ):
        return json_text(expected)
    methods = {method.name: method for method in signature.methods}
    types = [
        output_type(methods[operation]) if index and operation in methods else None
        for index, operation in enumerate(sequence.ops)
    ]
    return _typed_list_text(expected, types)


def _function_param_types(signature: Signature) -> dict[str, ValueType]:
    if isinstance(signature, ClassSignature):
        return {}
    return {param.name: param.type for param in signature.params}


def _operation_param_types(signature: Signature, ops: Sequence[str], index: int) -> list[ValueType]:
    """The parameter types of `ops[index]`: the constructor's first, then a method's."""
    if not isinstance(signature, ClassSignature):
        return []
    if index == 0:
        return [param.type for param in signature.constructor_params]
    operation = ops[index] if index < len(ops) else None
    found = next((method for method in signature.methods if method.name == operation), None)
    return [param.type for param in found.params] if found else []


def _typed_list_text(values: Sequence[JsonValue], types: Sequence[ValueType | None]) -> str:
    """A JSON array whose item `i` is shown by `types[i]`, and as plain JSON past the types."""
    shown = (
        display_text(value, types[index] if index < len(types) else None)
        for index, value in enumerate(values)
    )
    return f"[{', '.join(shown)}]"
