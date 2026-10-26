"""Seeded operation sequences for {{title}} (docs/specs/problem-format.md#progressive-problems).

`n` is the number of calls after the constructor, across every level's method, with strictly
increasing timestamps. TODO: how the calls are mixed.
"""

import random
from typing import Any

MAX_CALLS = 10**5
KEYS = 50
VALUES = ("x", "y", "z")


def generate(rng: random.Random, n: int) -> dict[str, Any]:
    ops: list[str] = ["{{class_name}}"]
    args: list[list[Any]] = [[]]
    for timestamp in range(1, min(n, MAX_CALLS) + 1):
        key = f"k{rng.randrange(KEYS)}"
        op = rng.choice(("put", "get", "remove", "size"))
        ops.append(op)
        if op == "put":
            args.append([timestamp, key, rng.choice(VALUES)])
        elif op == "size":
            args.append([timestamp])
        else:
            args.append([timestamp, key])
    return {"ops": ops, "args": args}


def validate(case_input: dict[str, Any]) -> None:
    args: list[list[Any]] = case_input["args"]
    timestamps = [arguments[0] for arguments in args[1:]]
    assert len(timestamps) <= MAX_CALLS, "too many calls"
    assert timestamps == sorted(set(timestamps)), "timestamps must strictly increase"
