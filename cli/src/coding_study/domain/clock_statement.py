"""A case on the virtual clock, in words, for the rendered statement
(docs/specs/problem-format.md#statement).

The statement shows a case that holds harness operations as the steps it takes, numbered as the
runner numbers operations (the constructor is 0), so that `op 4 (@join r1)` in a report names the
line of the example:

    0  MessageLog(30000)
    1  r1 = Receive(5000) starts
    2  1000 ms pass
    3  Publish("a") returns 1
    4  r1 returns "a"
    5  the clock reads 1000 ms
"""

from collections.abc import Sequence

from coding_study.domain.cases import (
    Case,
    HarnessOp,
    JsonValue,
    OperationSequence,
    is_harness_operation,
    joined_task,
    spawned_call,
)
from coding_study.domain.signature import ClassSignature, Method, output_type
from coding_study.domain.type_dsl import ValueType, VoidType
from coding_study.domain.value_text import display_text

OPERATIONS_LABEL = "Operations:"
INDENT = "  "
SEPARATOR = "  "
"""Between a step's number and its words."""
VIRTUAL_CLOCK_NOTICE = (
    "The project runs on a virtual clock: time moves only while every task waits, so a wait of "
    "any length takes no real time. A wait that nothing can end is a deadlock, which "
    "`cstudy submit` reports as `STALLED`. In the examples, `N ms pass` moves the clock and "
    "`the clock reads N ms` reads it."
)
"""The line that `## Project` of a virtual-clock project's statement gains."""


def spoken_example(signature: ClassSignature, case: Case) -> tuple[str, ...] | None:
    """The lines of the case's operations in words; None for a case without harness operations,
    which the statement shows as lists of operations, arguments and outputs."""
    sequence = case.input
    if not isinstance(sequence, OperationSequence) or not any(
        is_harness_operation(operation) for operation in sequence.ops[1:]
    ):
        return None
    outputs = case.expected.value if case.expected is not None else None
    steps = _Steps(signature, outputs if isinstance(outputs, list) else [])
    spoken = [
        steps.say(index, operation, arguments)
        for index, (operation, arguments) in enumerate(
            zip(sequence.ops, sequence.args, strict=True)
        )
    ]
    width = len(str(len(spoken) - 1))
    numbered = (f"{index:>{width}}{SEPARATOR}{text}" for index, text in enumerate(spoken))
    return (OPERATIONS_LABEL, *(f"{INDENT}{line}" for line in numbered))


class _Steps:
    """The steps of one case, in order: a join remembers the method its spawn started."""

    def __init__(self, signature: ClassSignature, outputs: Sequence[JsonValue]) -> None:
        self._signature = signature
        self._methods = {method.name: method for method in signature.methods}
        self._outputs = outputs
        self._running: dict[str, Method | None] = {}
        """The method each spawned task runs, until its join; None for one the class lacks."""

    def say(self, index: int, operation: str, arguments: Sequence[JsonValue]) -> str:
        output = self._outputs[index] if index < len(self._outputs) else None
        if index == 0:
            types = [param.type for param in self._signature.constructor_params]
            return f"{operation}({_listed(arguments, types)})"
        if not is_harness_operation(operation):
            return self._call(operation, arguments, output)
        match operation:
            case HarnessOp.ADVANCE if len(arguments) == 1:
                return f"{display_text(arguments[0], None)} ms pass"
            case HarnessOp.SPAWN if (call := spawned_call(arguments)) is not None:
                method = self._methods.get(call.method)
                self._running[call.task] = method
                types = [param.type for param in method.params] if method else []
                return f"{call.task} = {call.method}({_listed(call.arguments, types)}) starts"
            case HarnessOp.JOIN if (task := joined_task(arguments)) is not None:
                return self._join(task, output)
            case HarnessOp.NOW:
                return f"the clock reads {display_text(output, None)} ms"
            case _:
                return f"{operation}({_listed(arguments, [])})"

    def _call(self, operation: str, arguments: Sequence[JsonValue], output: JsonValue) -> str:
        method = self._methods.get(operation)
        types = [param.type for param in method.params] if method else []
        call = f"{operation}({_listed(arguments, types)})"
        return call if method is None else _with_result(call, method, output)

    def _join(self, task: str, output: JsonValue) -> str:
        method = self._running.pop(task, None)
        if method is None or isinstance(method.returns.type, VoidType):
            return f"{task} finishes"
        return _with_result(task, method, output)


def _with_result(subject: str, method: Method, output: JsonValue) -> str:
    """`subject returns <output>`, or `subject` alone for a method that returns nothing."""
    if isinstance(method.returns.type, VoidType):
        return subject
    return f"{subject} returns {display_text(output, output_type(method))}"


def _listed(values: Sequence[JsonValue], types: Sequence[ValueType]) -> str:
    shown = (
        display_text(value, types[index] if index < len(types) else None)
        for index, value in enumerate(values)
    )
    return ", ".join(shown)
