"""Seeded operation sequences for snapshot-array.

The array has n positions and the constructor is followed by n calls (both capped at
5 * 10^4): `set` 45%, `snap` 15%, `get` 40%. A `get` comes only after the first `snap`
(earlier draws become a `snap`) and asks about a uniform snapshot taken so far. Half of the
positions in `set` and `get` come from up to 8 hot positions, which build long histories;
the other half are uniform, so most of them were never written. Scanning the write log
backwards for a cold position reads the whole log, which keeps the scan quadratic at every
seed, while per-position histories answer with one binary search.
"""

import random

MAX_LENGTH = 5 * 10**4
MAX_CALLS = 5 * 10**4
MAX_VALUE = 10**9
HOT_POSITIONS = 8
SET_SHARE = 0.45
SNAP_SHARE = 0.15


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    calls = min(max(n, 1), MAX_CALLS)
    hot = [rng.randrange(length) for _ in range(min(HOT_POSITIONS, length))]

    def position() -> int:
        return rng.choice(hot) if rng.random() < 0.5 else rng.randrange(length)

    ops: list[str] = ["SnapshotArray"]
    args: list[list[int]] = [[length]]
    snaps = 0
    for _ in range(calls):
        roll = rng.random()
        if roll < SET_SHARE:
            ops.append("set")
            args.append([position(), rng.randint(0, MAX_VALUE)])
        elif roll < SET_SHARE + SNAP_SHARE or snaps == 0:
            ops.append("snap")
            args.append([])
            snaps += 1
        else:
            ops.append("get")
            args.append([position(), rng.randrange(snaps)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "SnapshotArray", "the first op must be the constructor"
    assert len(args[0]) == 1, "the constructor takes the length"
    length = args[0][0]
    assert 1 <= length <= MAX_LENGTH, "length out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    snaps = 0
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        if op == "set":
            index, value = arguments
            assert 0 <= index < length, "index out of bounds"
            assert 0 <= value <= MAX_VALUE, "value out of range"
        elif op == "snap":
            assert arguments == [], "snap takes no arguments"
            snaps += 1
        else:
            assert op == "get", f"unknown op {op}"
            index, snap_id = arguments
            assert 0 <= index < length, "index out of bounds"
            assert 0 <= snap_id < snaps, "get must name a snapshot already taken"
