"""Seeded operation sequences for range-sum-immutable.

`n` is the length of `nums`, and the constructor is followed by `n` calls to `sumRange`.
Each range takes two uniformly random positions, so a range covers about a third of the array
on average: adding it up costs O(n) per call and O(n^2) for the whole sequence, while prefix
sums answer every call in O(1). One input in eight fills the array with the extreme values
`+10^5` or `-10^5` only, so long ranges overflow 32 bits.
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
    else:
        nums = [rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(length)]
    ops: list[str] = ["NumArray"]
    args: list[list] = [[nums]]
    for _ in range(min(length, MAX_CALLS)):
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
    for op, (left, right) in zip(ops[1:], args[1:], strict=True):
        assert op == "sumRange", f"unknown op {op}"
        assert 0 <= left <= right < len(nums), "range out of bounds"
