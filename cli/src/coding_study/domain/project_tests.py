"""The generated test file of one level of a project problem, before a language spells it
(docs/specs/problem-format.md#generated-test-files).

A level's file holds one test per visible case of that level, in tests.json order. A test builds
the entry class with the case's constructor arguments, then makes each call in turn; a call to a
method that returns a value is checked against the case's expected output with that method's
comparator, `exact`, `unordered` or `float`. Each language's generator spells this plan in its
native test framework (the `ProjectTestGenerator` port).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from coding_study.domain.cases import Case, JsonValue, OperationSequence
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import ComparatorType, Language, Problem, ProblemKind
from coding_study.domain.project import Project, level_test_file, project_language
from coding_study.domain.project_checks import GENERATED_TEST_COMPARATORS
from coding_study.domain.signature import ClassSignature, Method
from coding_study.domain.type_dsl import VoidType

EDIT_NOTICE = "Yours to edit and extend: cstudy never rewrites this file."
"""Closes the header of every generated test file."""
FIRST_LEVEL_WRITER = "cstudy start"
LATER_LEVEL_WRITER = "cstudy submit"
"""The command that writes a level's file: start for level 1, the submission that opens a later
level for the others."""


@dataclass(frozen=True, slots=True)
class Call:
    """One operation after the constructor."""

    method: Method
    arguments: tuple[JsonValue, ...]
    expected: JsonValue
    comparator: ComparatorType
    """`exact`, `unordered` or `float`: the method's comparator in meta.yaml."""

    @property
    def returns_value(self) -> bool:
        """False for a `void` method: the test makes the call and checks nothing."""
        return not isinstance(self.method.returns.type, VoidType)


@dataclass(frozen=True, slots=True)
class LevelTest:
    """One visible case."""

    case_id: str
    note: str | None
    constructor_arguments: tuple[JsonValue, ...]
    calls: tuple[Call, ...]


@dataclass(frozen=True, slots=True)
class LevelTests:
    """The generated test file of one level."""

    slug: str
    level: int
    language: Language
    project: Project
    signature: ClassSignature
    """The entry class, with every method of every level."""
    tolerance: float
    """Of the `float` comparator."""
    tests: tuple[LevelTest, ...]

    @property
    def entry(self) -> str:
        return self.project.entry

    @property
    def path(self) -> str:
        """Relative to the project root."""
        return level_test_file(self.project, self.language, self.level)

    @property
    def title(self) -> str:
        """The first line of the file's header; `EDIT_NOTICE` follows it."""
        writer = FIRST_LEVEL_WRITER if self.level == FIRST_LEVEL else LATER_LEVEL_WRITER
        return f"Level {self.level} examples of {self.slug}, written by `{writer}`."


def level_tests(problem: Problem, level: int) -> LevelTests:
    """The tests of `level`, from its visible cases.

    Raises ValueError for a problem that is not a well-formed project problem, a level it lacks,
    and a case a generated test cannot express; `cstudy verify` reports all of these.
    """
    meta = problem.meta
    project, signature = meta.project, meta.signature
    if meta.kind is not ProblemKind.PROJECT or project is None:
        raise ValueError(f"{meta.slug} is not a project problem")
    if not isinstance(signature, ClassSignature):
        raise ValueError(f"{meta.slug} declares no class")
    if level not in (declared.number for declared in meta.levels):
        raise ValueError(f"{meta.slug} has no level {level}")
    builder = _TestBuilder(signature, meta.comparator.per_method)
    cases = (case for case in problem.cases if case.visible and case.level == level)
    return LevelTests(
        slug=meta.slug,
        level=level,
        language=project_language(meta),
        project=project,
        signature=signature,
        tolerance=meta.comparator.tolerance,
        tests=tuple(builder.test(case) for case in cases),
    )


class _TestBuilder:
    def __init__(self, signature: ClassSignature, per_method: Mapping[str, ComparatorType]) -> None:
        self._class_name = signature.name
        self._methods = {method.name: method for method in signature.methods}
        self._per_method = per_method

    def test(self, case: Case) -> LevelTest:
        sequence, outputs = _operations(case)
        operations = zip(sequence.ops[1:], sequence.args[1:], outputs[1:], strict=True)
        calls = tuple(
            Call(self._method(case.id, name), arguments, expected, self._comparator(name))
            for name, arguments, expected in operations
        )
        return LevelTest(case.id, case.note, sequence.args[0], calls)

    def _method(self, case_id: str, name: str) -> Method:
        method = self._methods.get(name)
        if method is None:
            raise ValueError(
                f"case {case_id} calls {name}, which {self._class_name} does not declare"
            )
        return method

    def _comparator(self, name: str) -> ComparatorType:
        compared = self._per_method.get(name, ComparatorType.EXACT)
        if compared not in GENERATED_TEST_COMPARATORS:
            raise ValueError(f"a generated test cannot compare {name} with {compared}")
        return compared


def _operations(case: Case) -> tuple[OperationSequence, list[JsonValue]]:
    """The case's operations and their expected outputs, one per operation, constructor first."""
    sequence = case.input
    if not isinstance(sequence, OperationSequence) or not sequence.ops:
        raise ValueError(f"case {case.id} has no operation sequence")
    count = len(sequence.ops)
    if len(sequence.args) != count:
        raise ValueError(
            f"case {case.id} has {len(sequence.args)} argument lists for {count} operations"
        )
    outputs = case.expected.value if case.expected is not None else None
    if not isinstance(outputs, list) or len(outputs) != count:
        found = len(outputs) if isinstance(outputs, list) else 0
        raise ValueError(f"case {case.id} expects {found} outputs for {count} operations")
    return sequence, outputs
