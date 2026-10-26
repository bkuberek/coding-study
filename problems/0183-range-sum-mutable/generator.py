"""Seeded operation sequences for range-sum-mutable.

`n` is the length of `nums`, and the constructor is followed by `n` calls (at most 10^5),
each an `update` or a `sumRange` with equal probability. Positions and range ends are
uniform, so a range covers about a third of the array: adding it up costs O(n) per query and
O(n^2) per sequence, while both trees answer every call in O(log n). One input in eight
uses only the extreme values +10^5 and -10^5 with a single sign, so range sums pass 2^31.
"""

import random

MAX_LENGTH = 10**5
MAX_CALLS = 10**5
VALUE_LIMIT = 10**5
EXTREME_SHARE = 0.125


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if rng.random() < EXTREME_SHARE:
        sign = rng.choice([1, -1])
        nums = [sign * VALUE_LIMIT] * length

        def new_value() -> int:
            return sign * VALUE_LIMIT
    else:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]

        def new_value() -> int:
            return rng.randint(-VALUE_LIMIT, VALUE_LIMIT)
    ops: list[str] = ["NumArray"]
    args: list[list] = [[nums]]
    for _ in range(min(length, MAX_CALLS)):
        if rng.random() < 0.5:
            ops.append("update")
            args.append([rng.randrange(length), new_value()])
        else:
            first, second = rng.randrange(length), rng.randrange(length)
            ops.append("sumRange")
            args.append([min(first, second), max(first, second)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "NumArray" and len(args[0]) == 1, "the first op must be the constructor"
    nums = args[0][0]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        if op == "update":
            index, value = arguments
            assert 0 <= index < len(nums), "index out of bounds"
            assert -VALUE_LIMIT <= value <= VALUE_LIMIT, "value out of range"
        else:
            assert op == "sumRange", f"unknown op {op}"
            left, right = arguments
            assert 0 <= left <= right < len(nums), "range out of bounds"
