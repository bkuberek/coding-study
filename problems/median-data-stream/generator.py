"""Seeded operation sequences for median-data-stream.

`n` is the number of calls after the constructor. The first call is `addNum`; after it, each
call is `addNum` with probability 0.6 and `findMedian` otherwise, so the median is always
defined. The stream is random over the full range, ascending, descending, or drawn from only
a few distinct values (many ties at the median), chosen per sequence. A descending stream
makes every binary insertion into a sorted array shift the whole array.
"""

import random

MAX_CALLS = 10**5
VALUE_LIMIT = 10**5
FEW_DISTINCT = 2
ADD_PROBABILITY = 0.6
ARITY = {"addNum": 1, "findMedian": 0}


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    shape = rng.choice(("random", "random", "ascending", "descending", "few-distinct"))
    limit = FEW_DISTINCT if shape == "few-distinct" else VALUE_LIMIT
    ops: list[str] = ["MedianFinder"]
    args: list[list[int]] = [[]]
    values: list[int] = []
    for call in range(calls):
        if call == 0 or rng.random() < ADD_PROBABILITY:
            ops.append("addNum")
            values.append(rng.randint(-limit, limit))
            args.append([])  # filled below, once the stream's order is known
        else:
            ops.append("findMedian")
            args.append([])
    if shape == "ascending":
        values.sort()
    elif shape == "descending":
        values.sort(reverse=True)
    stream = iter(values)
    for position, op in enumerate(ops):
        if op == "addNum":
            args[position] = [next(stream)]
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "MedianFinder" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    added = 0
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op == "addNum":
            assert -VALUE_LIMIT <= arguments[0] <= VALUE_LIMIT, "value out of range"
            added += 1
        else:
            assert added > 0, "findMedian before any number was added"
