"""Test cases from tests.json (docs/specs/problem-format.md#testsjson)."""

from collections.abc import Mapping
from dataclasses import dataclass
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
    """A class-kind case: `ops[0]` is the constructor, `args[i]` the arguments of `ops[i]`."""

    ops: tuple[str, ...]
    args: tuple[tuple[JsonValue, ...], ...]


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
