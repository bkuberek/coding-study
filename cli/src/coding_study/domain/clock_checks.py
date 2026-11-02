"""`cstudy verify --static` check S18 on the virtual clock (docs/specs/authoring.md#static).

S18 holds the declarations (`async`, `project.clock`) and the harness operations of a case. The
types of the operations' arguments and expected values are S4's (`value_checks.case_issues`); S18
reads what only the whole case shows: that the clock is declared, that a task is spawned once and
joined once, and that a spawned method is one the case's level has.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from coding_study.domain.cases import (
    Case,
    HarnessOp,
    JsonValue,
    OperationSequence,
    is_harness_operation,
    joined_task,
    spawned_call,
)
from coding_study.domain.errors import ContentIssue
from coding_study.domain.problem import Language, Problem, ProblemKind
from coding_study.domain.problem_files import META_FILE, TESTS_FILE
from coding_study.domain.signature import ClassSignature, Method, async_issues
from coding_study.domain.virtual_clock import ProjectClock, clock_declaration_issues

MIN_ADVANCE_MS = 1
MAX_ADVANCE_MS = 2**31 - 1
"""Node accepts no timer delay above this, so the TypeScript clock cannot honor a longer one."""


def clock_issues(directory: str, problem: Problem) -> tuple[ContentIssue, ...]:
    """S18 on one problem of any kind: `async` and harness operations belong to projects."""
    meta = problem.meta
    is_project = meta.kind is ProblemKind.PROJECT
    declarations = clock_declaration_issues(meta) if is_project else async_issues(meta.signature)
    issues = [
        ContentIssue(f"{directory}/{META_FILE}", declaration.location, declaration.message)
        for declaration in declarations
    ]
    issues += _Cases(f"{directory}/{TESTS_FILE}", problem).issues()
    return tuple(issues)


class _Cases:
    """The operation sequences of a problem, checked case by case."""

    def __init__(self, file: str, problem: Problem) -> None:
        meta = problem.meta
        self._file = file
        self._cases = problem.cases
        self._is_project = meta.kind is ProblemKind.PROJECT
        project = meta.project
        self._on_virtual_clock = project is not None and project.clock is ProjectClock.VIRTUAL
        one_language = self._is_project and len(meta.languages) == 1
        self._language = meta.languages[0] if one_language else None
        signature = meta.signature
        self._methods = (
            {method.name: method for method in signature.methods}
            if isinstance(signature, ClassSignature)
            else {}
        )

    def issues(self) -> Iterator[ContentIssue]:
        for index, case in enumerate(self._cases):
            if isinstance(case.input, OperationSequence):
                for message in self._messages(case, case.input):
                    yield ContentIssue(self._file, f"cases[{index}] {case.id}", message)

    def _messages(self, case: Case, sequence: OperationSequence) -> Iterator[str]:
        first = next(
            (
                index
                for index, op in enumerate(sequence.ops)
                if index > 0 and is_harness_operation(op)
            ),
            None,
        )
        if first is None:
            return
        if self._on_virtual_clock:
            yield from _CaseWalk(self._methods, self._language, case).messages(sequence)
        elif self._is_project:
            yield f"ops[{first}]: {sequence.ops[first]} needs project.clock: virtual"
        else:
            yield f"ops[{first}]: {sequence.ops[first]} is a harness operation of project problems"


@dataclass(slots=True)
class _CaseWalk:
    """The operations of one case on the virtual clock, in order, with the tasks they spawn."""

    methods: dict[str, Method]
    language: Language | None
    case: Case
    spawned: dict[str, int] = field(default_factory=dict[str, int])
    """Each task with the index of the `@spawn` that started it."""
    joined: set[str] = field(default_factory=set[str])

    def messages(self, sequence: OperationSequence) -> Iterator[str]:
        operations = zip(sequence.ops, sequence.args, strict=False)
        for index, (operation, arguments) in enumerate(operations):
            if index == 0:
                continue
            match operation:
                case HarnessOp.ADVANCE:
                    yield from _advance_messages(index, arguments)
                case HarnessOp.SPAWN:
                    yield from self._spawn_messages(index, arguments)
                case HarnessOp.JOIN:
                    yield from self._join_messages(index, arguments)
                case _:
                    continue
        for task, index in self.spawned.items():
            if task not in self.joined:
                yield f'ops[{index}]: task "{task}" is never joined'

    def _spawn_messages(self, index: int, arguments: Sequence[JsonValue]) -> Iterator[str]:
        call = spawned_call(arguments)
        if call is None:
            return
        if call.task in self.spawned:
            yield f'ops[{index}]: task "{call.task}" is spawned twice'
        self.spawned.setdefault(call.task, index)
        method = self.methods.get(call.method)
        if method is None:
            return
        level = self.case.level
        if level is not None and method.level is not None and method.level > level:
            yield f"ops[{index}]: {call.method} is introduced at level {method.level}"
        if self.language is not Language.GO and not method.is_async:
            yield (
                f"ops[{index}]: {call.method} is not async, and only go spawns a method that blocks"
            )

    def _join_messages(self, index: int, arguments: Sequence[JsonValue]) -> Iterator[str]:
        task = joined_task(arguments)
        if task is None:
            return
        if task not in self.spawned:
            yield f'ops[{index}]: task "{task}" is joined before any @spawn starts it'
            return
        if task in self.joined:
            yield f'ops[{index}]: task "{task}" is joined twice'
        self.joined.add(task)


def _advance_messages(index: int, arguments: Sequence[JsonValue]) -> Iterator[str]:
    milliseconds = _single_integer(arguments)
    if milliseconds is not None and not MIN_ADVANCE_MS <= milliseconds <= MAX_ADVANCE_MS:
        yield (
            f"ops[{index}]: @advance moves the clock {MIN_ADVANCE_MS} to {MAX_ADVANCE_MS} ms, "
            f"not {milliseconds}"
        )


def _single_integer(arguments: Sequence[JsonValue]) -> int | None:
    match arguments:
        case [int() as value] if not isinstance(value, bool):
            return value
        case _:
            return None
