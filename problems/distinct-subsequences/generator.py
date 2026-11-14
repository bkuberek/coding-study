"""Seeded inputs for distinct-subsequences: s of length n and a subsequence t of it.

s has n letters (at most 1000) drawn from an alphabet whose size grows with n (from 2
letters for tiny inputs to all 52 English letters, upper and lower case, from about 800 on),
which keeps the counts moderate. t is a random subsequence of s with a tenth to a quarter
of its length, so the answer is at least 1. The constraints promise that the counts for all
prefix pairs and all suffix pairs fit in 32 bits; inputs that break this are drawn again.
Every table approach fills about len(s) * len(t) cells, which grows like n^2.
"""

import math
import random
import string

MAX_LENGTH = 1000
LETTERS = string.ascii_lowercase + string.ascii_uppercase
LIMIT = 2**31 - 1
MIN_SPREAD = 8
MAX_SPREAD = 15


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    while True:
        size = rng.randint(
            min(len(LETTERS), max(2, math.ceil(length / MAX_SPREAD))),
            min(len(LETTERS), max(2, math.ceil(length / MIN_SPREAD))),
        )
        s = "".join(rng.choices(LETTERS[:size], k=length))
        picked = sorted(rng.sample(range(length), rng.randint(max(1, length // 10), max(1, length // 4))))
        t = "".join(s[i] for i in picked)
        if _fits(s, t):
            return {"s": s, "t": t}


def _fits(s: str, t: str) -> bool:
    """True if every prefix-pair and suffix-pair count is at most LIMIT."""
    return _largest_prefix_count(s, t) <= LIMIT and _largest_prefix_count(s[::-1], t[::-1]) <= LIMIT


def _largest_prefix_count(s: str, t: str) -> int:
    # counts[j] = occurrences of t[:j] in the prefix of s read so far.
    counts = [1] + [0] * len(t)
    largest = 1
    for character in s:
        for j in range(len(t), 0, -1):
            if t[j - 1] == character:
                counts[j] += counts[j - 1]
                largest = max(largest, counts[j])
    return largest


def validate(case_input: dict) -> None:
    s, t = case_input["s"], case_input["t"]
    assert 1 <= len(s) <= MAX_LENGTH and 1 <= len(t) <= MAX_LENGTH, "length out of range"
    assert all(character in LETTERS for character in s + t), "only English letters"
    assert _fits(s, t), "a prefix-pair or suffix-pair count exceeds 32 bits"
