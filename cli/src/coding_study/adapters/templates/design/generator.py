"""Seeded operation sequences for {{title}}.

Format: docs/specs/problem-format.md#operation-sequences-design-problems. `n` is the number
of calls after the constructor; TODO: how the calls are mixed.
"""

import random
from typing import Any

MAX_CALLS = 10**5
MAX_CAPACITY = 10**4
MAX_KEY = 10**4
MAX_VALUE = 10**9
ARITY = {"put": 2, "get": 1}


def generate(rng: random.Random, n: int) -> dict[str, Any]:
    calls = min(n, MAX_CALLS)
    ops: list[str] = ["{{class_name}}"]
    args: list[list[int]] = [[rng.randint(1, MAX_CAPACITY)]]
    for _ in range(calls):
        key = rng.randint(0, MAX_KEY)
        if rng.random() < 0.5:
            ops.append("put")
            args.append([key, rng.randint(0, MAX_VALUE)])
        else:
            ops.append("get")
            args.append([key])
    return {"ops": ops, "args": args}


def validate(case_input: dict[str, Any]) -> None:
    ops: list[str] = case_input["ops"]
    args: list[list[int]] = case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    assert 1 <= args[0][0] <= MAX_CAPACITY, "capacity out of range"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
