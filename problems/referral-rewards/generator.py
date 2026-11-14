"""Seeded operation sequences for referral-rewards.

`n` is the number of referral rows, all given to one `referAll` call, and about n people appear.

The rows hold three kinds of structure, so that every part of a solution has work to do:
a random forest of referrals in which half of the referrers are chosen among the first thousand
people (a few big hubs and a lot of leaves); a chain of n/10 people, each referred by the
previous one, which is the input that a solution recursing once per level cannot survive; and
about 3% of rows that do not count (repeats of an earlier row, a second referrer for someone,
people naming themselves, and referrals that name the root of the forest and would close a loop),
mixed in at random places. The rows after `referAll` ask for the top referrer, the board and the
totals and points of a few people.

validate checks the shape of the calls and the promises of the statement: the bonus and the
sizes, and printable ASCII names of at most 20 characters.
"""

import random

MAX_ROWS = 10**6
MAX_NAME_LENGTH = 20
SMALL = 30
HUBS = 1000
HUB_SHARE = 0.5
CHAIN_SHARE = 10
NOISE_PERCENT = 3
PROBES = 5
BOARD_SIZE = 10
BONUS = 10
MAX_BONUS = 1000
ARITY = {
    "refer": 2,
    "points": 1,
    "referralsOf": 1,
    "totalReferrals": 1,
    "topReferrer": 0,
    "referAll": 1,
    "leaderboard": 1,
}


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 4), MAX_ROWS)
    noise = count * NOISE_PERCENT // 100
    chain = max(count // CHAIN_SHARE, 2)
    forest = max(count - noise - chain, 1)
    people = forest + 1
    rows = _forest(rng, forest)
    rows.append([f"p{rng.randrange(people)}", "c0"])
    rows.extend([f"c{i}", f"c{i + 1}"] for i in range(chain - 1))
    rows = _mix(rng, rows, _noise(rng, rows, people, noise))
    bonus = BONUS if count > SMALL else rng.randint(1, 20)
    ops: list[str] = ["ReferralProgram", "referAll", "topReferrer", "leaderboard"]
    args: list[list] = [[bonus], [rows], [], [BOARD_SIZE]]
    probes = ["p0", "c0", f"c{chain // 2}"] + [f"p{rng.randrange(people)}" for _ in range(PROBES)]
    for probe in probes:
        ops.extend(["totalReferrals", "points"])
        args.extend([[probe], [probe]])
    ops.append("referralsOf")
    args.append(["p0"])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "ReferralProgram", "the first op must be the constructor"
    assert len(args[0]) == 1, "the constructor takes only the bonus"
    assert 1 <= args[0][0] <= MAX_BONUS, "bonus out of range"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op == "referAll":
            assert len(arguments[0]) <= MAX_ROWS, "too many rows"
            for row in arguments[0]:
                assert len(row) == 2, "a row is [referrer, referred]"
                _validate_name(row[0])
                _validate_name(row[1])
        elif op not in ("leaderboard", "topReferrer"):
            for name in arguments:
                _validate_name(name)


def _forest(rng: random.Random, forest: int) -> list[list[str]]:
    rows = []
    for referred in range(1, forest + 1):
        pool = min(referred, HUBS) if rng.random() < HUB_SHARE else referred
        rows.append([f"p{rng.randrange(pool)}", f"p{referred}"])
    return rows


def _noise(rng: random.Random, rows: list[list[str]], people: int, count: int) -> list[list[str]]:
    extra = []
    for _ in range(count):
        kind = rng.randrange(4)
        referrer = f"p{rng.randrange(people)}"
        if kind == 0:
            extra.append(list(rng.choice(rows)))
        elif kind == 1:
            extra.append([referrer, rng.choice(rows)[1]])
        elif kind == 2:
            extra.append([referrer, referrer])
        else:
            extra.append([referrer, "p0"])
    return extra


def _mix(rng: random.Random, rows: list[list[str]], extra: list[list[str]]) -> list[list[str]]:
    keyed = [(float(at), row) for at, row in enumerate(rows)]
    keyed.extend((rng.random() * len(rows), row) for row in extra)
    keyed.sort(key=lambda pair: pair[0])
    return [row for _, row in keyed]


def _validate_name(name: str) -> None:
    assert isinstance(name, str), "names are strings"
    assert 1 <= len(name) <= MAX_NAME_LENGTH, "name length out of range"
    assert all(32 <= ord(char) <= 126 for char in name), "printable ASCII only"
