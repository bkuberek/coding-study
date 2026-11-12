"""Seeded inputs for first-bad-commit: a history with a boundary and scattered skips.

From 100 commits on, the sizes the ladder times, the first bad commit sits somewhere in the
middle third of the history and one commit in ten is skipped, wherever it is; the last commit
is always bad. A scan from the oldest commit therefore reads at least n/3 statuses at every
seed (linear), while a binary search needs about log2(n) probes, each stepping past a skipped
commit now and then.

Below 100 commits, which covers the oracle's inputs, the boundary is anywhere, and the share of
skipped commits is none, a third or two thirds of the history, so that single answers,
ambiguous answers, histories that begin with skips and histories with no good commit all occur.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
GOOD, BAD, SKIP = 0, 1, 2
LADDER_FROM = 100
LADDER_SKIP_SHARE = 0.1
SMALL_SKIP_SHARES = (0.0, 0.33, 0.67)


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    if length >= LADDER_FROM:
        boundary = rng.randint(length // 3, 2 * length // 3)
        share = LADDER_SKIP_SHARE
    else:
        boundary = rng.randint(0, length - 1)
        share = rng.choice(SMALL_SKIP_SHARES)
    statuses = [GOOD if i < boundary else BAD for i in range(length)]
    for i in range(length):
        if rng.random() < share:
            statuses[i] = SKIP
    statuses[length - 1] = BAD
    return {"statuses": statuses}


def validate(case_input: dict) -> None:
    statuses = case_input["statuses"]
    assert MIN_LENGTH <= len(statuses) <= MAX_LENGTH, "length out of range"
    assert all(value in (GOOD, BAD, SKIP) for value in statuses), "status out of range"
    assert BAD in statuses, "at least one commit must be bad"
    first_bad = statuses.index(BAD)
    assert GOOD not in statuses[first_bad:], "a good commit comes after a bad one"
