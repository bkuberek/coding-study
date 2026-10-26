"""Seeded inputs for remove-k-digits: a long non-decreasing prefix, then random digits.

The number starts with a sorted run of non-zero digits covering half to three quarters of
it, then random digits; on a third of the seeds those start with a few zeros, so the deletions of
the prefix expose leading zeros. `k` is between n/4 and n/2 (any value from 0 to n for tiny
inputs). The first peak sits at the end of the sorted run, so every rescan from the start
walks the whole remaining run: at least k * (run - k), about n^2 / 16 steps. The stack
touches each digit at most twice.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
TINY = 4
MAX_LEADING_ZEROS = 5


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length < TINY:
        num = str(rng.randint(0 if length == 1 else 10 ** (length - 1), 10**length - 1))
        return {"num": num, "k": rng.randint(0, length)}
    run_length = rng.randint(length // 2, (3 * length) // 4)
    run = sorted(rng.choices("123456789", k=run_length))
    rest = rng.choices("0123456789", k=length - run_length)
    if rng.random() < 1 / 3:
        zeros = min(len(rest), rng.randint(1, MAX_LEADING_ZEROS))
        rest[:zeros] = ["0"] * zeros
    k = rng.randint(length // 4, length // 2)
    return {"num": "".join(run) + "".join(rest), "k": k}


def validate(case_input: dict) -> None:
    num, k = case_input["num"], case_input["k"]
    assert MIN_LENGTH <= len(num) <= MAX_LENGTH, "length out of range"
    assert num.isdigit() and num.isascii(), "num must contain only digits"
    assert num == "0" or num[0] != "0", "num must not have leading zeros"
    assert 0 <= k <= len(num), "k out of range"
