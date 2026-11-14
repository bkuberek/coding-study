"""Seeded operation sequences for min-stack.

`n` is the number of calls after the constructor. On a non-empty stack each call is `push`
with probability 0.5, `pop` 0.2, `top` 0.1 and `getMin` 0.2; an empty stack always gets a
`push`. The stack therefore grows by about 0.3 elements per call, to about 0.3 n. Values are
mostly in [-1000, 1000], so equal minimums are common, with occasional 32-bit extremes.

Scanning for the minimum on every `getMin` then reads about 0.03 n^2 elements in total; the
O(1) approaches stay linear in the number of calls.
"""

import random

MAX_CALLS = 10**5
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
SMALL_LIMIT = 1000
EXTREME_PROBABILITY = 0.02
CALL_WEIGHTS = (("push", 0.5), ("pop", 0.2), ("top", 0.1), ("getMin", 0.2))
ARITY = {"push": 1, "pop": 0, "top": 0, "getMin": 0}


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    names = [name for name, _ in CALL_WEIGHTS]
    weights = [weight for _, weight in CALL_WEIGHTS]
    ops: list[str] = ["MinStack"]
    args: list[list[int]] = [[]]
    size = 0
    for _ in range(calls):
        op = rng.choices(names, weights)[0] if size else "push"
        ops.append(op)
        if op == "push":
            args.append([_value(rng)])
            size += 1
        else:
            args.append([])
            size -= op == "pop"
    return {"ops": ops, "args": args}


def _value(rng: random.Random) -> int:
    roll = rng.random()
    if roll < EXTREME_PROBABILITY:
        return INT_MIN
    if roll < 2 * EXTREME_PROBABILITY:
        return INT_MAX
    return rng.randint(-SMALL_LIMIT, SMALL_LIMIT)


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "MinStack" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    size = 0
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op == "push":
            assert INT_MIN <= arguments[0] <= INT_MAX, "value out of range"
            size += 1
            continue
        assert size > 0, f"{op} on an empty stack"
        size -= op == "pop"
