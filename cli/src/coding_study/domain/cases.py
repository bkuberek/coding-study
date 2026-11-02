"""Test cases from tests.json (docs/specs/problem-format.md#testsjson)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from coding_study.domain.stress import StressScenario

type JsonValue = bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None


@dataclass(frozen=True, slots=True)
class FunctionInput:
    """Arguments of a `function` kind case, keyed by canonical parameter name."""

    arguments: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class OperationSequence:
    """A class-kind case: `ops[0]` is the constructor, `args[i]` the arguments of `ops[i]`. A
    project on the virtual clock may also hold harness operations (`HarnessOp`)."""

    ops: tuple[str, ...]
    args: tuple[tuple[JsonValue, ...], ...]


HARNESS_PREFIX = "@"
"""Starts every harness operation, so no method name (which starts with a letter) can clash."""


class HarnessOp(StrEnum):
    """The operations besides methods that a case of a project on the virtual clock may hold
    (docs/specs/problem-format.md#asynchronous-code-and-the-virtual-clock)."""

    ADVANCE = "@advance"
    """`[ms]`: the clock moves forward; outputs null."""
    SPAWN = "@spawn"
    """`[task, method, ...arguments]`: starts the call as `task` without waiting; outputs null."""
    JOIN = "@join"
    """`[task]`: waits for the task and outputs the call's result."""
    NOW = "@now"
    """`[]`: outputs the virtual milliseconds since the case started."""


def is_harness_operation(operation: str) -> bool:
    return operation.startswith(HARNESS_PREFIX)


@dataclass(frozen=True, slots=True)
class SpawnedCall:
    """The call a `@spawn` starts, as its arguments name it."""

    task: str
    method: str
    arguments: tuple[JsonValue, ...]


def spawned_call(arguments: Sequence[JsonValue]) -> SpawnedCall | None:
    """The call that `@spawn` arguments start; None when they do not name a task and a method."""
    match arguments:
        case [str() as task, str() as method, *call_arguments]:
            return SpawnedCall(task, method, tuple(call_arguments))
        case _:
            return None


def joined_task(arguments: Sequence[JsonValue]) -> str | None:
    """The task that `@join` arguments wait for; None when they do not name exactly one."""
    match arguments:
        case [str() as task]:
            return task
        case _:
            return None


@dataclass(frozen=True, slots=True)
class GeneratedInput:
    """An input produced by `generator.py` for size `n` and `seed`."""

    n: int
    seed: int


type CaseInput = FunctionInput | OperationSequence | GeneratedInput | StressScenario
"""`StressScenario` (concurrent problems, `coding_study.domain.stress`) is a stress case."""


@dataclass(frozen=True, slots=True)
class Expected:
    """An expected output; wrapped because `null` is a legitimate expected value."""

    value: JsonValue


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    input: CaseInput
    expected: Expected | None = None
    visible: bool = False
    level: int | None = None
    hang_guard_ms: int | None = None
    note: str | None = None
