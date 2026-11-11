"""Seeded operation sequences for org-chart-outline.

`n` is the number of rows of each of two charts, loaded one after the other.

The first chart is a chain of managers n deep, its rows in a shuffled order, which is what a
solution that recurses once per level cannot survive; it is questioned only through the methods
whose answers stay small (a chain, a lowest common manager, subtree sizes). The second chart is a
random tree of n rows, also shuffled, with a few orphans and a few cycles added to it; its
outline is read once, in size order, which uses the subtree sizes, the name order and the
fallback to the id. A chain n deep has an outline of order n^2 characters, so it is never
printed.

validate checks the shape of the calls and the promises of the statement: unique non-empty ids,
printable ASCII text and the size limits.
"""

import random

MAX_ROWS = 10**5
MAX_ID_LENGTH = 20
MAX_NAME_LENGTH = 30
SMALL = 30
ORPHAN_SHARE = 0.002
CYCLE_COUNT = 3
CYCLE_LENGTH = 3
PROBES = 6
NAMES = ["Ada", "Grace", "Linus", "Ken", "Dennis", "Margaret", "Barbara", "Edsger", "Tim", "Radia"]
ARITY = {
    "load": 1,
    "roots": 0,
    "nameOf": 1,
    "children": 1,
    "orphans": 0,
    "cycles": 0,
    "chain": 1,
    "lowestCommonManager": 2,
    "subtreeSize": 1,
    "outline": 1,
}


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_ROWS)
    ops: list[str] = ["OrgChart"]
    args: list[list] = [[]]
    chain_rows, deepest = _chain(rng, count)
    _call(ops, args, "load", chain_rows)
    _call(ops, args, "roots")
    _call(ops, args, "chain", deepest)
    _call(ops, args, "subtreeSize", "e0")
    for _ in range(PROBES):
        probe = f"e{rng.randrange(count)}"
        _call(ops, args, "lowestCommonManager", deepest, probe)
        _call(ops, args, "subtreeSize", probe)
    random_rows = _random_tree(rng, count)
    _call(ops, args, "load", random_rows)
    _call(ops, args, "roots")
    _call(ops, args, "orphans")
    _call(ops, args, "cycles")
    for _ in range(PROBES):
        first, second = f"e{rng.randrange(count)}", f"e{rng.randrange(count)}"
        _call(ops, args, "lowestCommonManager", first, second)
        _call(ops, args, "chain", first)
        _call(ops, args, "subtreeSize", second)
    _call(ops, args, "outline", "size" if count > SMALL else rng.choice(["input", "name", "size"]))
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "OrgChart", "the first op must be the constructor"
    assert args[0] == [], "the constructor takes nothing"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op == "load":
            _validate_rows(arguments[0])
        if op == "outline":
            assert arguments[0] in ("input", "name", "size"), "unknown order"


def _call(ops: list[str], args: list[list], op: str, *arguments) -> None:
    ops.append(op)
    args.append(list(arguments))


def _chain(rng: random.Random, count: int) -> tuple[list[list[str]], str]:
    rows = [[f"e{i}", f"e{i - 1}" if i else "", _name(rng)] for i in range(count)]
    rng.shuffle(rows)
    return rows, f"e{count - 1}"


def _random_tree(rng: random.Random, count: int) -> list[list[str]]:
    parents = [""] + [f"e{rng.randrange(i)}" for i in range(1, count)]
    for i in range(1, count):
        if rng.random() < ORPHAN_SHARE:
            parents[i] = f"gone{i}"
    if count >= CYCLE_COUNT * CYCLE_LENGTH + 1:
        cut = rng.sample(range(1, count), CYCLE_COUNT * CYCLE_LENGTH)
        for start in range(0, len(cut), CYCLE_LENGTH):
            ring = cut[start : start + CYCLE_LENGTH]
            for at, member in enumerate(ring):
                parents[member] = f"e{ring[(at + 1) % CYCLE_LENGTH]}"
    rows = [[f"e{i}", parents[i], _name(rng)] for i in range(count)]
    rng.shuffle(rows)
    return rows


def _name(rng: random.Random) -> str:
    return f"{rng.choice(NAMES)} {rng.randrange(1000)}"


def _validate_rows(rows: list[list[str]]) -> None:
    assert len(rows) <= MAX_ROWS, "too many rows"
    seen: set[str] = set()
    for row in rows:
        assert len(row) == 3, "a row is [id, parentId, name]"
        row_id, parent, name = row
        assert row_id, "ids are not empty"
        assert row_id not in seen, "ids are unique"
        seen.add(row_id)
        assert len(row_id) <= MAX_ID_LENGTH, "id too long"
        assert len(parent) <= MAX_ID_LENGTH, "parent id too long"
        assert len(name) <= MAX_NAME_LENGTH, "name too long"
        assert all(32 <= ord(ch) <= 126 for ch in row_id + parent + name), "printable ASCII only"
