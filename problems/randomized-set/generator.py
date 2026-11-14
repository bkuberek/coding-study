"""Seeded operation sequences for randomized-set.

`n` is the number of calls after the constructor. Values come from a random pool of
max(2, n/10) values, so inserts and removes of the same values meet often: about half of the
calls return `false`, and the set settles around half of the pool, about n/20 members.
`getRandom` is added only while the set holds exactly one value (with probability 0.3 at each
such moment), because its result is otherwise random.

A linear search over about n/20 members per call makes the brute force grow with n^2; the
hash-based approaches stay linear in the number of calls.
"""

import random

MAX_CALLS = 10**5
POOL_DIVISOR = 10
MIN_POOL = 2
VALUE_LIMIT = 10**9
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
GET_RANDOM_PROBABILITY = 0.3
ARITY = {"insert": 1, "remove": 1, "getRandom": 0}


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    pool = rng.sample(range(-VALUE_LIMIT, VALUE_LIMIT + 1), max(MIN_POOL, calls // POOL_DIVISOR))
    ops: list[str] = ["RandomizedSet"]
    args: list[list[int]] = [[]]
    present: set[int] = set()
    for _ in range(calls):
        if len(present) == 1 and rng.random() < GET_RANDOM_PROBABILITY:
            ops.append("getRandom")
            args.append([])
            continue
        value = rng.choice(pool)
        if rng.random() < 0.5:
            ops.append("insert")
            present.add(value)
        else:
            ops.append("remove")
            present.discard(value)
        args.append([value])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "RandomizedSet" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    present: set[int] = set()
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op == "getRandom":
            assert len(present) == 1, "getRandom is only called on a one-element set"
            continue
        value = arguments[0]
        assert INT_MIN <= value <= INT_MAX, "value out of range"
        if op == "insert":
            present.add(value)
        else:
            present.discard(value)
