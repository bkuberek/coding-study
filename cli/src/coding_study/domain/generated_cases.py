"""Inputs from a problem's generator.py.

Spec: docs/specs/problem-format.md#generated-cases-and-generatorpy.

`generate` cases take their expected value from the `perf.expected_from` approach; the oracle
cross-check (`cstudy verify --oracle`) compares every approach with the `oracle: true` approach on
small generated inputs (docs/specs/authoring.md#dynamic, D4).
"""

import random
from collections.abc import Collection, Mapping
from dataclasses import dataclass

from coding_study.domain.cases import (
    Case,
    Expected,
    FunctionInput,
    JsonValue,
    OperationSequence,
)
from coding_study.domain.judging import RunnableCase
from coding_study.domain.problem import ApproachRole, ProblemKind, ProblemMeta
from coding_study.domain.runs import RunInput

DEFAULT_ORACLE_CASES = 200
ORACLE_MIN_SIZE = 1
ORACLE_MAX_SIZE = 30
ORACLE_CASE_PREFIX = "oracle-"


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    """A generated input with the expected value computed from the reference approach."""

    input: RunInput
    expected: Expected


@dataclass(frozen=True, slots=True)
class OracleInput:
    case_id: str
    seed: int
    n: int


def generated_run_input(kind: ProblemKind, document: Mapping[str, JsonValue]) -> RunInput:
    """`generate()` output: arguments for function kinds, else `{"ops": [...], "args": [...]}`.

    Raises ValueError when a class-kind document is not an operation sequence.
    """
    if kind is ProblemKind.FUNCTION:
        return FunctionInput(dict(document))
    ops, args = document.get("ops"), document.get("args")
    if not isinstance(ops, list) or not isinstance(args, list):
        raise ValueError(_NOT_AN_OPERATION_SEQUENCE)
    names = [name for name in ops if isinstance(name, str)]
    arguments = [items for items in args if isinstance(items, list)]
    if not names or len({len(ops), len(args), len(names), len(arguments)}) != 1:
        raise ValueError(_NOT_AN_OPERATION_SEQUENCE)
    return OperationSequence(tuple(names), tuple(tuple(items) for items in arguments))


_NOT_AN_OPERATION_SEQUENCE = 'expected {"ops": [names...], "args": [[...], ...]} of equal length'


def materialized_case(case: Case, generated: GeneratedCase) -> RunnableCase:
    return RunnableCase(
        id=case.id,
        input=generated.input,
        expected=generated.expected,
        generated=True,
        hang_guard_ms=case.hang_guard_ms,
        note=case.note,
    )


def oracle_inputs(count: int, first_seed: int = 1) -> tuple[OracleInput, ...]:
    """Seeds `first_seed` to `first_seed + count - 1`, each with a size drawn from 1 to 30 by
    that seed, so seed s always gives the same input (`cstudy test --stress 1 --seed s`)."""
    return tuple(
        OracleInput(
            f"{ORACLE_CASE_PREFIX}{seed}",
            seed,
            random.Random(seed).randint(ORACLE_MIN_SIZE, ORACLE_MAX_SIZE),
        )
        for seed in range(first_seed, first_seed + count)
    )


def expected_source(meta: ProblemMeta, python_approaches: Collection[str]) -> str | None:
    """`perf.expected_from`, else the first `optimal` approach that has a Python file."""
    if meta.perf.expected_from is not None:
        return meta.perf.expected_from
    return next(
        (
            approach.id
            for approach in meta.approaches
            if approach.role is ApproachRole.OPTIMAL and approach.id in python_approaches
        ),
        None,
    )


def oracle_approach(meta: ProblemMeta) -> str | None:
    return next((approach.id for approach in meta.approaches if approach.oracle), None)
