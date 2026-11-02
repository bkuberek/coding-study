"""The generated test file of one level of a project problem, before a language spells it
(docs/specs/problem-format.md#generated-test-files).

A level's file holds one test per visible case of that level, in tests.json order. A test builds
the entry class with the case's constructor arguments, then makes each call in turn; a call to a
method that returns a value is checked against the case's expected output with that method's
comparator, `exact`, `unordered` or `float`. Each language's generator spells this plan in its
native test framework (the `ProjectTestGenerator` port).

A project on the virtual clock (docs/specs/problem-format.md#generated-tests-on-the-virtual-clock)
also has the harness operations between its calls: the clock advances, a call is spawned as a task
and joined later, and the clock is read. They are part of the plan only in the languages whose
generator expresses them (`HARNESS_TEST_LANGUAGES`); any other refuses them by name.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from coding_study.domain.cases import (
    Case,
    HarnessOp,
    JsonValue,
    OperationSequence,
    is_harness_operation,
    joined_task,
    spawned_call,
)
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import ComparatorType, Language, Problem, ProblemKind
from coding_study.domain.project import Project, level_test_file, project_language
from coding_study.domain.project_checks import GENERATED_TEST_COMPARATORS
from coding_study.domain.signature import ClassSignature, Method
from coding_study.domain.type_dsl import VoidType
from coding_study.domain.virtual_clock import ProjectClock

EDIT_NOTICE = "Yours to edit and extend: cstudy never rewrites this file."
"""Closes the header of every generated test file."""
FIRST_LEVEL_WRITER = "cstudy start"
LATER_LEVEL_WRITER = "cstudy submit"
"""The command that writes a level's file: start for level 1, the submission that opens a later
level for the others."""
HARNESS_TEST_LANGUAGES = frozenset({Language.GO})
"""The languages whose generated tests express the harness operations of the virtual clock. Each
step of docs/decisions/0017-async-project-problems.md#scope-and-order adds its languages."""


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
class Advance:
    """`@advance`: the clock moves forward."""

    milliseconds: int


@dataclass(frozen=True, slots=True)
class Spawn:
    """`@spawn`: starts a call as the task `task` without waiting for it."""

    task: str
    method: Method
    arguments: tuple[JsonValue, ...]


@dataclass(frozen=True, slots=True)
class Join:
    """`@join`: waits for the task and checks the result of the call it ran, with that method's
    comparator."""

    task: str
    call: Call
    """The spawned call, with the result the case expects of it."""


@dataclass(frozen=True, slots=True)
class Now:
    """`@now`: the virtual milliseconds since the case started."""

    expected: int


type Operation = Call | Advance | Spawn | Join | Now
"""One step of a test after the constructor."""


@dataclass(frozen=True, slots=True)
class LevelTest:
    """One visible case."""

    case_id: str
    note: str | None
    constructor_arguments: tuple[JsonValue, ...]
    operations: tuple[Operation, ...]

    @property
    def calls(self) -> tuple[Call, ...]:
        """The operations of a test on the real clock, which are all calls.

        Raises ValueError for a test that holds harness operations: the languages that express
        them read `operations`.
        """
        calls = tuple(operation for operation in self.operations if isinstance(operation, Call))
        if len(calls) != len(self.operations):
            raise ValueError(
                f"case {self.case_id} holds harness operations, which this language's tests "
                "do not express"
            )
        return calls


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
    def virtual_clock(self) -> bool:
        """True when every test runs on the virtual clock, from the constructor on."""
        return self.project.clock is ProjectClock.VIRTUAL

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
    language = project_language(meta)
    harness = project.clock is ProjectClock.VIRTUAL and language in HARNESS_TEST_LANGUAGES
    builder = _TestBuilder(signature, meta.comparator.per_method, harness=harness)
    cases = (case for case in problem.cases if case.visible and case.level == level)
    return LevelTests(
        slug=meta.slug,
        level=level,
        language=language,
        project=project,
        signature=signature,
        tolerance=meta.comparator.tolerance,
        tests=tuple(builder.test(case) for case in cases),
    )


class _TestBuilder:
    def __init__(
        self, signature: ClassSignature, per_method: Mapping[str, ComparatorType], *, harness: bool
    ) -> None:
        self._class_name = signature.name
        self._methods = {method.name: method for method in signature.methods}
        self._per_method = per_method
        self._harness = harness
        """Whether the language's generator expresses the harness operations of this project."""

    def test(self, case: Case) -> LevelTest:
        sequence, outputs = _operations(case)
        operations = zip(sequence.ops[1:], sequence.args[1:], outputs[1:], strict=True)
        running: dict[str, Spawn] = {}
        steps = tuple(
            self._operation(case.id, name, arguments, expected, running)
            for name, arguments, expected in operations
        )
        if running:
            task = next(iter(running))
            raise ValueError(f"case {case.id}: @spawn of {task} is never joined")
        return LevelTest(case.id, case.note, sequence.args[0], steps)

    def _operation(
        self,
        case_id: str,
        name: str,
        arguments: tuple[JsonValue, ...],
        expected: JsonValue,
        running: dict[str, Spawn],
    ) -> Operation:
        if not is_harness_operation(name):
            return self._call(case_id, name, arguments, expected)
        if not self._harness:
            raise ValueError(
                f"case {case_id} uses {name}, which the generated tests do not express yet"
            )
        if name not in HarnessOp:
            raise ValueError(f"case {case_id} uses {name}, which is not a harness operation")
        match HarnessOp(name):
            case HarnessOp.ADVANCE:
                return _advance(case_id, arguments)
            case HarnessOp.SPAWN:
                return self._spawn(case_id, arguments, running)
            case HarnessOp.JOIN:
                return self._join(case_id, arguments, expected, running)
            case HarnessOp.NOW:
                return _now(case_id, arguments, expected)

    def _call(
        self, case_id: str, name: str, arguments: tuple[JsonValue, ...], expected: JsonValue
    ) -> Call:
        return Call(self._method(case_id, name), arguments, expected, self._comparator(name))

    def _spawn(
        self, case_id: str, arguments: tuple[JsonValue, ...], running: dict[str, Spawn]
    ) -> Spawn:
        started = spawned_call(arguments)
        if started is None:
            raise ValueError(
                f"case {case_id}: {HarnessOp.SPAWN} takes a task name, a method and its arguments"
            )
        if started.task in running:
            raise ValueError(
                f"case {case_id}: {HarnessOp.SPAWN} of {started.task}, which is running already"
            )
        spawn = Spawn(started.task, self._method(case_id, started.method), started.arguments)
        running[started.task] = spawn
        return spawn

    def _join(
        self,
        case_id: str,
        arguments: tuple[JsonValue, ...],
        expected: JsonValue,
        running: dict[str, Spawn],
    ) -> Join:
        task = joined_task(arguments)
        if task is None:
            raise ValueError(f"case {case_id}: {HarnessOp.JOIN} takes the name of one spawned task")
        spawn = running.pop(task, None)
        if spawn is None:
            raise ValueError(
                f"case {case_id}: {HarnessOp.JOIN} of {task}, which no {HarnessOp.SPAWN} started"
            )
        comparator = self._comparator(spawn.method.name)
        return Join(task, Call(spawn.method, spawn.arguments, expected, comparator))

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


def _advance(case_id: str, arguments: tuple[JsonValue, ...]) -> Advance:
    match arguments:
        case [int() as milliseconds] if not isinstance(milliseconds, bool):
            return Advance(milliseconds)
        case _:
            raise ValueError(
                f"case {case_id}: {HarnessOp.ADVANCE} takes one whole number of milliseconds"
            )


def _now(case_id: str, arguments: tuple[JsonValue, ...], expected: JsonValue) -> Now:
    if arguments:
        raise ValueError(f"case {case_id}: {HarnessOp.NOW} takes no arguments")
    if not isinstance(expected, int) or isinstance(expected, bool):
        raise ValueError(f"case {case_id}: {HarnessOp.NOW} expects a whole number of milliseconds")
    return Now(expected)


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
