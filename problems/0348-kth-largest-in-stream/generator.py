"""Seeded operation sequences for kth-largest-in-stream.

`n` is the number of `add` calls after the constructor. From 100 calls on, the sizes the ladder
times, the width is k = n // 2, the constructor gets n // 2 starting numbers, and every number is
uniform over the full value range. A sorted list then grows from n / 2 to 3n / 2 entries and each
insertion shifts a large share of them, while a heap that holds k numbers stays at k entries.

Below 100 calls, which covers the oracle's inputs, k is between 1 and 8, the constructor gets
between k - 1 and k + 5 starting numbers (so the first `add` can be the one that makes the
collection reach k numbers), and the added numbers come from one of four families: the full
range, two distinct values (many ties at the kth place), ascending (every add enters the top k)
or descending (no add enters it once the top k is full).
"""

import random

MAX_K = 10**5
MAX_START = 10**5
MAX_CALLS = 10**5
VALUE_LIMIT = 10**4
BIG_FROM = 100
SMALL_MAX_K = 8
FEW_DISTINCT = 1


def _values(rng: random.Random, count: int, family: str) -> list[int]:
    limit = FEW_DISTINCT if family == "ties" else VALUE_LIMIT
    values = [rng.randint(-limit, limit) for _ in range(count)]
    if family == "ascending":
        values.sort()
    elif family == "descending":
        values.sort(reverse=True)
    return values


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    if calls >= BIG_FROM:
        k = calls // 2
        start = _values(rng, calls // 2, "wide")
        added = _values(rng, calls, "wide")
    else:
        k = rng.randint(1, SMALL_MAX_K)
        family = rng.choice(("wide", "ties", "ascending", "descending"))
        start = _values(rng, rng.randint(k - 1, k + 5), "wide")
        added = _values(rng, calls, family)
    ops = ["KthLargestTracker"] + ["add"] * calls
    args: list[list] = [[k, start]] + [[value] for value in added]
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "KthLargestTracker" and len(args[0]) == 2, "the first op must be the constructor"
    k, start = args[0]
    assert 1 <= k <= MAX_K, "k out of range"
    assert len(start) <= MAX_START, "too many starting numbers"
    assert len(start) >= k - 1, "the first add must leave at least k numbers"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in start), "starting value out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op == "add" and len(arguments) == 1, f"bad call {op}{arguments}"
        assert -VALUE_LIMIT <= arguments[0] <= VALUE_LIMIT, "value out of range"
