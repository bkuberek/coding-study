"""Seeded operation sequences for range-module.

`n` is the number of calls after the constructor: about 40% `addRange`, 20% `removeRange`
and 40% `queryRange`. Added ranges are short compared with the line (up to 10^9 / (4n) long)
and placed uniformly, so most stay disjoint and the number of stored intervals grows with n:
the interval list then costs O(n) per call and O(n^2) per sequence, while the segment tree
costs O(log 10^9) per call. Removals and most queries target a range added earlier (a part
of it, all of it, or a little beyond it), so both answers of `queryRange` are common; one
query in four is a uniformly random range, which is almost always uncovered.
"""

import random

LOW, HIGH = 1, 10**9
MAX_CALLS = 3 * 10**4
ADD_SHARE, REMOVE_SHARE = 0.4, 0.2


def _random_range(rng: random.Random, max_length: int) -> list[int]:
    length = rng.randint(1, max_length)
    left = rng.randint(LOW, HIGH - length)
    return [left, left + length]


def _near(rng: random.Random, target: list[int]) -> list[int]:
    """A sub-range of target, all of it, or target widened by a little on one side."""
    start, end = target
    choice = rng.random()
    if choice < 0.5 and end - start >= 2:
        left = rng.randint(start, end - 1)
        return [left, rng.randint(left + 1, end)]
    if choice < 0.75:
        return [start, end]
    slack = max((end - start) // 4, 1)
    if rng.random() < 0.5:
        return [max(LOW, start - slack), end]
    return [start, min(HIGH, end + slack)]


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    max_length = max((HIGH - LOW) // (4 * calls), 2)
    added: list[list[int]] = []
    ops: list[str] = ["RangeModule"]
    args: list[list] = [[]]
    for _ in range(calls):
        roll = rng.random()
        if roll < ADD_SHARE or not added:
            target = _random_range(rng, max_length)
            if added and rng.random() < 0.2:
                target = _near(rng, rng.choice(added))  # overlap or extend an earlier range
            added.append(target)
            ops.append("addRange")
            args.append(target)
        elif roll < ADD_SHARE + REMOVE_SHARE:
            ops.append("removeRange")
            args.append(_near(rng, rng.choice(added)))
        else:
            ops.append("queryRange")
            if rng.random() < 0.25:
                args.append(_random_range(rng, max_length))
            else:
                args.append(_near(rng, rng.choice(added)))
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "RangeModule" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in ("addRange", "queryRange", "removeRange"), f"unknown op {op}"
        left, right = arguments
        assert LOW <= left < right <= HIGH, "range out of bounds"
