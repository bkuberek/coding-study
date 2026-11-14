"""Seeded operation sequences for time-based-kv-store.

`n` is the number of calls after the constructor. A clock advances by 1 to 3 on every call;
`set` writes one of up to 4 keys at the current time, so set timestamps strictly increase.
`get` asks about a uniformly random moment between 1 and slightly after the current time, so
a backwards scan of a key's history reads about half of it on average. With at most 4 keys,
histories grow linearly with n: scanning costs between about n^2/64 (4 keys) and n^2/16
(1 key) steps over the whole sequence,
while binary search costs log n per read. About one read in 20 targets a key that is never
written, and reads may fall before a key's first write; both must return "".
"""

import random
import string

MAX_CALLS = 10**5
MAX_TIMESTAMP = 10**7
MAX_LENGTH = 20
KEYS = ["alpha", "beta", "gamma", "delta"]
NEVER_WRITTEN = "omega"
ALPHABET = set(string.ascii_lowercase + string.digits)


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    keys = KEYS[: rng.randint(1, len(KEYS))]
    ops: list[str] = ["TimeMap"]
    args: list[list] = [[]]
    now = 0
    for _ in range(calls):
        now += rng.randint(1, 3)
        if rng.random() < 0.5:
            ops.append("set")
            args.append([rng.choice(keys), f"v{rng.randrange(10**6)}", now])
        else:
            key = NEVER_WRITTEN if rng.random() < 0.05 else rng.choice(keys)
            ops.append("get")
            args.append([key, rng.randint(1, now + 2)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "TimeMap" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    last_set = 0
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op in ("set", "get"), f"unknown op {op}"
        texts = arguments[:-1]
        timestamp = arguments[-1]
        assert len(arguments) == (3 if op == "set" else 2), f"bad arity for {op}"
        assert all(1 <= len(text) <= MAX_LENGTH and set(text) <= ALPHABET for text in texts), "bad string"
        assert 1 <= timestamp <= MAX_TIMESTAMP, "timestamp out of range"
        if op == "set":
            assert timestamp > last_set, "set timestamps must strictly increase"
            last_set = timestamp
