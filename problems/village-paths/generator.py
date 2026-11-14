"""Seeded operation sequences for village-paths.

`n` is the number of villages (capped at 33,333), and the constructor is followed by 3n calls:
about n `addPath`, n `canReach`, n/2 `groupSize` and n/2 `groupCount`, in random order. Every
call picks its villages uniformly at random, so a village can be paired with itself, which
happens often only on the small inputs the oracle uses.

Most of the `addPath` calls are real merges: at n = 4000, a seed measured 3,358 merges in 4,025
`addPath` calls. The brute force relabels all n villages on every merge, so the whole sequence
takes about 0.8 * n^2 steps, while the forest stays near linear.
"""

import random

MAX_VILLAGES = 33_333
MAX_CALLS = 10**5
CALL_WEIGHTS = (("addPath", 6), ("canReach", 6), ("groupSize", 3), ("groupCount", 3))


def generate(rng: random.Random, n: int) -> dict:
    villages = min(max(n, 1), MAX_VILLAGES)
    names = [name for name, _ in CALL_WEIGHTS]
    weights = [weight for _, weight in CALL_WEIGHTS]
    ops: list[str] = ["VillageMap"]
    args: list[list[int]] = [[villages]]
    for _ in range(3 * villages):
        op = rng.choices(names, weights)[0]
        ops.append(op)
        if op in ("addPath", "canReach"):
            args.append([rng.randrange(villages), rng.randrange(villages)])
        elif op == "groupSize":
            args.append([rng.randrange(villages)])
        else:
            args.append([])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "VillageMap", "the first op must be the constructor"
    assert len(args[0]) == 1, "the constructor takes the number of villages"
    villages = args[0][0]
    assert 1 <= villages <= 10**5, "village count out of range"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    arities = {"addPath": 2, "canReach": 2, "groupSize": 1, "groupCount": 0}
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in arities, f"unknown op {op}"
        assert len(arguments) == arities[op], f"wrong number of arguments for {op}"
        assert all(0 <= village < villages for village in arguments), "village out of range"
