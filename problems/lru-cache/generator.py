"""Seeded operation sequences for lru-cache.

`n` is the number of get and put calls after the constructor; the capacity is n/10 (at
least 1). Keys come from a range about twice the capacity, so once the cache has filled up
roughly half of the gets hit, and puts of new keys keep evicting. Every call is a get or a
put with equal probability.
"""

import random

MAX_CALLS = 10**5
MAX_CAPACITY = 10**4
MAX_KEY = 10**5
MAX_VALUE = 10**9
GENERATED_MAX_VALUE = 999
ARITY = {"get": 1, "put": 2}


def generate(rng: random.Random, n: int) -> dict:
    calls = min(n, MAX_CALLS)
    capacity = min(max(1, calls // 10), MAX_CAPACITY)
    key_count = 2 * capacity + 1
    ops: list[str] = ["LRUCache"]
    args: list[list[int]] = [[capacity]]
    for _ in range(calls):
        key = rng.randrange(key_count)
        if rng.random() < 0.5:
            ops.append("get")
            args.append([key])
        else:
            ops.append("put")
            args.append([key, rng.randint(0, GENERATED_MAX_VALUE)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "LRUCache", "the first op must be the constructor"
    assert len(args[0]) == 1, "the constructor takes only the capacity"
    assert 1 <= args[0][0] <= MAX_CAPACITY, "capacity out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        assert 0 <= arguments[0] <= MAX_KEY, "key out of range"
        assert op == "get" or 0 <= arguments[1] <= MAX_VALUE, "value out of range"
