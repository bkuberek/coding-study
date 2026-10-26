"""`cstudy verify --static` checks S3 to S12 on one problem (docs/specs/authoring.md#static).

S1 (schemas) and S2 (directory name) fail while loading the problem; uniqueness across problems
needs every problem and is checked by the caller.
"""

import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import pairwise

from coding_study.domain.buggy_stubs import buggy_file_name
from coding_study.domain.cases import Case, GeneratedInput, OperationSequence
from coding_study.domain.concurrency_checks import ConcurrencyContent, concurrency_issues
from coding_study.domain.errors import ContentIssue
from coding_study.domain.explanation import ApproachSection, Explanation
from coding_study.domain.generated_cases import expected_source
from coding_study.domain.layout import SOURCE_EXTENSIONS, language_of_extension
from coding_study.domain.levels import level_heading
from coding_study.domain.markdown import MarkdownDocument, MarkdownSection
from coding_study.domain.naming import reserved_name_conflicts, shadowed_python_builtins
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorType,
    Language,
    Problem,
    ProblemKind,
    ProblemMeta,
    StubSource,
    Track,
)
from coding_study.domain.problem_files import (
    BUGGY_DIRECTORY,
    CHECKER_FILE,
    EXPLANATION_FILE,
    EXPLANATION_NAME,
    META_FILE,
    PROBLEM_FILE,
    RUBRIC_FILE,
    TESTS_FILE,
    solution_file,
)
from coding_study.domain.rubric import LLD_RUBRIC_SECTIONS, rubric_issues
from coding_study.domain.signature import ClassSignature
from coding_study.domain.statement import example_marker
from coding_study.domain.value_checks import case_issues

PROBLEM_SECTIONS = (
    "Statement",
    "Input",
    "Output",
    "Examples",
    "Constraints",
    "Follow-ups",
    "Hints",
)
REQUIRED_SECTIONS = ("Statement", "Input", "Output", "Examples", "Constraints")
EXAMPLES_SECTION = "Examples"
HINTS_SECTION = "Hints"
PLACEHOLDER = "TODO"
APPROACH_SUBSECTIONS = (
    "Intuition",
    "Algorithm",
    "Correctness",
    "Complexity",
    "Trade-offs",
    "Pitfalls and edge cases",
)
COMPLEXITY_SUBSECTION = "Complexity"
LANGUAGE_NOTES = "Language notes"
_TABLE_SEPARATOR = re.compile(r":?-+:?")


@dataclass(frozen=True, slots=True)
class ProblemContent:
    """Everything the static checks read, gathered from one problem directory."""

    directory: str
    """Repository-relative, e.g. `problems/0001-two-sum`."""
    problem: Problem
    problem_markdown: str | None
    explanation: str | None
    files: tuple[str, ...] = ()
    """File names directly in the problem directory."""
    solution_files: tuple[str, ...] = ()
    buggy_files: tuple[str, ...] = ()
    rubric: str | None = None
    """rubric.md, when the problem has one."""
    broken_files: tuple[str, ...] = ()
    """Concurrent problems: file names in solutions/broken/."""


@dataclass(frozen=True, slots=True)
class StaticReport:
    errors: tuple[ContentIssue, ...]
    warnings: tuple[ContentIssue, ...]


def static_checks(content: ProblemContent) -> StaticReport:
    issues = _Issues(content.directory)
    meta = content.problem.meta
    _names(issues, content)
    _case_values(issues, content)
    if content.problem_markdown is None:
        issues.error(PROBLEM_FILE, "missing")
    else:
        _ProblemMarkdown(
            issues, content.problem, MarkdownDocument(content.problem_markdown)
        ).check()
    if content.explanation is None:
        issues.error(EXPLANATION_FILE, "missing")
    else:
        _ExplanationChecks(issues, meta, Explanation(content.explanation)).check()
    _solution_files(issues, content)
    _companion_files(issues, content)
    _perf(issues, content)
    _levels(issues, content.problem)
    issues.errors += concurrency_issues(_concurrency_content(content))
    return StaticReport(tuple(issues.errors), tuple(issues.warnings))


def _concurrency_content(content: ProblemContent) -> ConcurrencyContent:
    return ConcurrencyContent(
        directory=content.directory,
        meta=content.problem.meta,
        cases=content.problem.cases,
        problem_markdown=content.problem_markdown,
        explanation=content.explanation,
        files=content.files,
        broken_files=content.broken_files,
    )


class _Issues:
    def __init__(self, directory: str) -> None:
        self._directory = directory
        self.errors: list[ContentIssue] = []
        self.warnings: list[ContentIssue] = []

    def error(self, name: str, message: str, location: str = "") -> None:
        self.errors.append(ContentIssue(f"{self._directory}/{name}", location, message))

    def warn(self, name: str, message: str, location: str = "") -> None:
        self.warnings.append(ContentIssue(f"{self._directory}/{name}", location, message))


def _names(issues: _Issues, content: ProblemContent) -> None:
    """S3: no reserved words after per-language conversion; warn on shadowed builtins."""
    signature = content.problem.meta.signature
    for conflict in reserved_name_conflicts(signature):
        converted = f' (as "{conflict.symbol}")' if conflict.symbol != conflict.name else ""
        message = f'"{conflict.name}" is a reserved word in {conflict.language}{converted}'
        issues.error(META_FILE, message, "signature")
    for name in shadowed_python_builtins(signature):
        issues.warn(META_FILE, f'"{name}" shadows the Python builtin', "signature")


def _case_values(issues: _Issues, content: ProblemContent) -> None:
    """S4: every input and expected value conforms to the signature."""
    signature = content.problem.meta.signature
    for index, case in enumerate(content.problem.cases):
        for issue in case_issues(signature, case):
            issues.error(TESTS_FILE, issue, f"cases[{index}] {case.id}")


def _solution_files(issues: _Issues, content: ProblemContent) -> None:
    """S7: files map to approaches, approaches have files, one Python oracle at most."""
    approaches = content.problem.meta.approaches
    declared = {approach.id for approach in approaches}
    present: set[str] = set()
    for name in content.solution_files:
        if name == EXPLANATION_NAME or name.startswith("."):
            continue
        stem, _, extension = name.rpartition(".")
        if stem in declared and language_of_extension(extension) is not None:
            present.add(stem)
        else:
            issues.error(solution_file(name), "maps to no declared approach")
    for approach in approaches:
        if approach.id not in present:
            issues.error(
                META_FILE, f"{approach.id} has no reference file in solutions/", "approaches"
            )
    oracles = [approach.id for approach in approaches if approach.oracle]
    if len(oracles) > 1:
        issues.error(META_FILE, "at most one approach may be the oracle", "approaches")
    python = _python_approaches(content)
    for oracle in oracles:
        if oracle not in python:
            issues.error(META_FILE, f"oracle {oracle} needs solutions/{oracle}.py", "approaches")


def _companion_files(issues: _Issues, content: ProblemContent) -> None:
    """S8: checker.py with the checker comparator, buggy files, the lld rubric's sections."""
    meta = content.problem.meta
    files = set(content.files)
    is_checker = meta.comparator.type is ComparatorType.CHECKER
    if is_checker and CHECKER_FILE not in files:
        issues.error(CHECKER_FILE, "missing (comparator: checker)")
    if not is_checker and CHECKER_FILE in files:
        issues.error(CHECKER_FILE, f"present but the comparator is {meta.comparator.type}")
    if meta.stub is StubSource.BUGGY:
        expected = {buggy_file_name(language) for language in meta.languages}
        for name in sorted(expected - set(content.buggy_files)):
            issues.error(f"{BUGGY_DIRECTORY}/{name}", "missing (stub: buggy)")
        for name in sorted(set(content.buggy_files) - expected):
            issues.error(f"{BUGGY_DIRECTORY}/{name}", "maps to no language in languages")
    elif content.buggy_files:
        issues.error(BUGGY_DIRECTORY, f"present but stub is {meta.stub}")
    if meta.track is Track.LLD and RUBRIC_FILE not in files:
        issues.error(RUBRIC_FILE, "missing (track: lld)")
    if content.rubric is not None:
        for message in rubric_issues(content.rubric, LLD_RUBRIC_SECTIONS):
            issues.error(RUBRIC_FILE, message)


def _perf(issues: _Issues, content: ProblemContent) -> None:
    """S9: expected values come from a Python approach; the size ladder ascends."""
    meta = content.problem.meta
    python = _python_approaches(content)
    source = meta.perf.expected_from
    if source is not None and source not in python:
        issues.error(META_FILE, f'"{source}" has no Python reference', "perf.expected_from")
    generated = any(isinstance(case.input, GeneratedInput) for case in content.problem.cases)
    if source is None and generated and expected_source(meta, python) is None:
        message = "generate cases need it, or an optimal approach with a Python reference"
        issues.error(META_FILE, message, "perf.expected_from")
    ladder = meta.perf.size_ladder
    if any(later <= earlier for earlier, later in pairwise(ladder)):
        issues.error(META_FILE, "must be ascending", "perf.size_ladder")


def _python_approaches(content: ProblemContent) -> set[str]:
    suffix = f".{SOURCE_EXTENSIONS[Language.PYTHON]}"
    return {name.removesuffix(suffix) for name in content.solution_files if name.endswith(suffix)}


def _levels(issues: _Issues, problem: Problem) -> None:
    """S10: progressive levels are contiguous and cases use only unlocked methods."""
    meta = problem.meta
    signature = meta.signature
    if meta.kind is not ProblemKind.PROGRESSIVE or not isinstance(signature, ClassSignature):
        return
    numbers = [level.number for level in meta.levels]
    if numbers != list(range(1, len(numbers) + 1)):
        issues.error(META_FILE, "levels must be numbered 1, 2, ... without gaps", "levels")
    method_levels = {method.name: method.level for method in signature.methods}
    for name, level in method_levels.items():
        if level not in numbers:
            message = f"method {name} needs a level from 1 to {len(numbers)}"
            issues.error(META_FILE, message, "signature")
    levels_with_cases = {case.level for case in problem.cases}
    for number in numbers:
        if number not in levels_with_cases:
            issues.error(TESTS_FILE, f"level {number} has no cases")
    for index, case in enumerate(problem.cases):
        location = f"cases[{index}] {case.id}"
        for message in _case_level_problems(case, method_levels, len(numbers)):
            issues.error(TESTS_FILE, message, location)


def _case_level_problems(
    case: Case, method_levels: dict[str, int | None], level_count: int
) -> Iterator[str]:
    if case.level is None or not 1 <= case.level <= level_count:
        yield f"level must be from 1 to {level_count}"
        return
    if isinstance(case.input, GeneratedInput) and case.level != level_count:
        yield f"a generate case belongs to the last level ({level_count})"
    if not isinstance(case.input, OperationSequence):
        return
    for operation in dict.fromkeys(case.input.ops[1:]):
        level = method_levels.get(operation)
        if level is not None and level > case.level:
            yield f"{operation} is introduced at level {level}"


class _ProblemMarkdown:
    """S5: required headings, example markers, hint numbering, no placeholders."""

    def __init__(self, issues: _Issues, problem: Problem, document: MarkdownDocument) -> None:
        self._issues = issues
        self._problem = problem
        self._document = document

    def check(self) -> None:
        self._title()
        self._sections()
        self._examples()
        self._hints()
        self._placeholders()

    def _error(self, message: str) -> None:
        self._issues.error(PROBLEM_FILE, message)

    def _title(self) -> None:
        title, expected = self._document.title, self._problem.meta.title
        if title != expected:
            self._error(f'title "{title}" must equal meta.yaml title "{expected}"')

    def _sections(self) -> None:
        sections = {section.title: section for section in self._document.sections(2)}
        progressive = self._problem.meta.kind is ProblemKind.PROGRESSIVE
        for title in REQUIRED_SECTIONS:
            if progressive and title == EXAMPLES_SECTION:
                continue
            section = sections.get(title)
            if section is None:
                self._error(f'missing "## {title}"')
            elif not section.text:
                self._error(f'"## {title}" is empty')
        if progressive:
            self._level_sections(sections)
        self._order([title for title in sections if title in PROBLEM_SECTIONS])

    def _level_sections(self, sections: dict[str, MarkdownSection]) -> None:
        if EXAMPLES_SECTION in sections:
            self._error(
                f'progressive problems put examples in "## Level" sections, '
                f'not in "## {EXAMPLES_SECTION}"'
            )
        found = [
            (number, section)
            for section in sections.values()
            if (number := level_heading(section.title)) is not None
        ]
        declared = {level.number: level.title for level in self._problem.meta.levels}
        for number, section in found:
            self._level_section(number, section, declared.get(number))
        numbers = [number for number, _ in found]
        if numbers != sorted(numbers):
            self._error(
                '"## Level" sections must be in level order: '
                + ", ".join(str(number) for number in sorted(declared))
            )
        for number, title in declared.items():
            if number not in numbers:
                self._error(f'missing "## Level {number}: {title}"')

    def _level_section(self, number: int, section: MarkdownSection, title: str | None) -> None:
        expected = f"Level {number}: {title}"
        if title is None:
            self._error(f'"## {section.title}" names no level in meta.yaml')
        elif section.title != expected:
            self._error(f'"## {section.title}" must be titled "## {expected}"')
        elif not self._document.sections(3, section):
            self._error(f'"## {section.title}" needs at least one "### Example <n>"')

    def _order(self, titles: list[str]) -> None:
        for position, title in enumerate(titles):
            rank = PROBLEM_SECTIONS.index(title)
            later = next(
                (
                    earlier
                    for earlier in titles[:position]
                    if PROBLEM_SECTIONS.index(earlier) > rank
                ),
                None,
            )
            if later is not None:
                self._error(f'"## {title}" must come before "## {later}"')

    def _examples(self) -> None:
        cases = {case.id: case for case in self._problem.cases}
        for example in self._example_sections():
            self._example(example, cases)
        markers = Counter(
            case_id for line in self._document.lines if (case_id := example_marker(line))
        )
        for case in self._problem.cases:
            count = markers.get(case.id, 0)
            if case.visible and count == 0:
                self._error(f'visible case "{case.id}" has no example')
            elif case.visible and count > 1:
                self._error(f'visible case "{case.id}" is referenced {count} times')
        if self._problem.meta.kind is ProblemKind.PROGRESSIVE:
            self._example_levels(cases)

    def _example_levels(self, cases: dict[str, Case]) -> None:
        """The example of a level-L case sits in the `## Level L` section."""
        level_sections = [
            (number, section)
            for section in self._document.sections(2)
            if (number := level_heading(section.title)) is not None
        ]
        for index, line in enumerate(self._document.lines):
            case = cases.get(example_marker(line) or "")
            if case is None or not case.visible or case.level is None:
                continue
            where = next(
                (found for found in level_sections if found[1].start <= index < found[1].end),
                None,
            )
            example = f'case "{case.id}" is a level {case.level} example but sits'
            if where is None:
                self._error(f'{example} outside the "## Level" sections')
            elif where[0] != case.level:
                self._error(f'{example} in "## {where[1].title}"')

    def _example_sections(self) -> Iterator[MarkdownSection]:
        parents = (
            section
            for section in self._document.sections(2)
            if section.title == EXAMPLES_SECTION or level_heading(section.title) is not None
        )
        for parent in parents:
            yield from self._document.sections(3, parent)

    def _example(self, example: MarkdownSection, cases: dict[str, Case]) -> None:
        markers = [case_id for line in example.body if (case_id := example_marker(line))]
        if len(markers) != 1:
            self._error(f"{example.title} needs exactly one <!-- case: <id> --> marker")
        for case_id in markers:
            case = cases.get(case_id)
            if case is None:
                self._error(f'{example.title}: no case "{case_id}" in tests.json')
            elif not case.visible:
                self._error(f'{example.title}: case "{case_id}" is not visible')
        explained = any(line.strip() and example_marker(line) is None for line in example.body)
        if markers and not explained:
            self._error(f"{example.title} needs at least one line of explanation")

    def _hints(self) -> None:
        hints = self._document.section(HINTS_SECTION)
        if hints is None:
            return
        for position, hint in enumerate(self._document.sections(3, hints), start=1):
            if hint.title != f"Hint {position}":
                self._error(f'hint {position} is titled "{hint.title}"')

    def _placeholders(self) -> None:
        for section in self._document.sections(2):
            if PLACEHOLDER in section.text:
                self._error(f'"## {section.title}" contains {PLACEHOLDER}')


class _ExplanationChecks:
    """S6: one complete section per approach, matching meta.yaml and the overview."""

    def __init__(self, issues: _Issues, meta: ProblemMeta, explanation: Explanation) -> None:
        self._issues = issues
        self._approaches = meta.approaches
        self._explanation = explanation
        self._requires_language_notes = meta.kind is ProblemKind.CONCURRENT
        """Concurrent problems: every optimal approach explains each language's primitives."""

    def check(self) -> None:
        sections = self._explanation.approaches()
        declared = {approach.id for approach in self._approaches}
        for section in sections:
            if section.approach_id not in declared:
                self._error(f'"## Approach: {section.approach_id}" names no approach in meta.yaml')
        found = {section.approach_id: section for section in sections}
        for approach in self._approaches:
            if approach.id not in found:
                self._error(f'missing "## Approach: {approach.id} ({approach.name})"')
        in_file = [section.approach_id for section in sections if section.approach_id in declared]
        in_meta = [approach.id for approach in self._approaches if approach.id in found]
        if in_file != in_meta:
            self._error(f"approach sections must follow meta.yaml order: {', '.join(in_meta)}")
        for approach in self._approaches:
            if approach.id in found:
                self._approach(approach, found[approach.id])
        self._overview()

    def _approach(self, approach: Approach, found: ApproachSection) -> None:
        if found.name is not None and found.name != approach.name:
            self._error(
                f'approach {approach.id} is named "{approach.name}" in meta.yaml, '
                f'not "{found.name}"'
            )
        document = self._explanation.document
        subsections = {sub.title: sub for sub in document.sections(3, found.section)}
        for title in APPROACH_SUBSECTIONS:
            sub = subsections.get(title)
            if sub is None:
                self._error(f'missing "### {title}" in approach {approach.id}')
            elif not sub.text:
                self._error(f'"### {title}" is empty in approach {approach.id}')
        complexity = subsections.get(COMPLEXITY_SUBSECTION)
        if complexity is not None:
            self._complexity(approach, complexity)
        notes = subsections.get(LANGUAGE_NOTES)
        if approach.role is ApproachRole.OPTIMAL and (notes is None or not notes.text):
            message = f'approach {approach.id}: no "### {LANGUAGE_NOTES}"'
            if self._requires_language_notes:
                self._error(message)
            else:
                self._issues.warn(EXPLANATION_FILE, message)

    def _complexity(self, approach: Approach, complexity: MarkdownSection) -> None:
        for label, value in (("Time", approach.time), ("Space", approach.space)):
            line = re.compile(rf"- {label}: {re.escape(value)}\s+\S")
            if not any(line.match(text) for text in complexity.body):
                self._error(f'approach {approach.id}: needs a line "- {label}: {value} — <why>"')

    def _overview(self) -> None:
        overview = self._explanation.overview
        if overview is None:
            self._error('missing "## Overview"')
            return
        rows = {row[0]: row for row in _table_rows(overview.body)}
        declared = {approach.id for approach in self._approaches}
        for approach_id in rows.keys() - declared:
            self._error(f"## Overview row {approach_id} names no approach in meta.yaml")
        for approach in self._approaches:
            row = rows.get(approach.id)
            if row is None:
                self._error(f"## Overview has no row for {approach.id}")
                continue
            expected = (
                ("role", approach.role.value),
                ("time", approach.time),
                ("space", approach.space),
            )
            for (field, value), cell in zip(expected, row[1:], strict=False):
                if cell != value:
                    self._error(
                        f'## Overview row {approach.id}: {field} "{cell}" '
                        f'must equal meta.yaml "{value}"'
                    )

    def _error(self, message: str) -> None:
        self._issues.error(EXPLANATION_FILE, message)


def _table_rows(lines: Iterable[str]) -> list[list[str]]:
    """Body rows of a Markdown table: the header and separator rows are skipped."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
        if line.strip().startswith("|")
    ]
    return [row for row in rows[1:] if not all(_TABLE_SEPARATOR.fullmatch(cell) for cell in row)]
