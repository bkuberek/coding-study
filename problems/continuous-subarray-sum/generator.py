"""Seeded inputs for continuous-subarray-sum.

`n` is the length of `nums`. Most inputs are built from their prefix remainders: pick
`k` between n + 2 and 10^9, choose n distinct non-zero remainders, and set each value to the
step between consecutive remainders plus a random multiple of `k` (within 10^9). Every
prefix then has its own remainder, so no run qualifies and both approaches scan everything.
Half of those inputs plant one repeated remainder near the end (a qualifying run that ends
at the last value), so the answer is `true` but is still found only late.

Inputs of at most 50 values may instead be uniform random arrays with a small `k`, which
usually contain an early answer; they keep the oracle cross-check varied, while large inputs
always exercise the full scan.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**9
K_LIMIT = 2**31 - 1
SMALL_LENGTH = 50
RANDOM_SHARE = 0.3
PLANTED_SHARE = 0.5
TAIL_SHARE = 10


def _random_input(rng: random.Random, length: int) -> dict:
    limit = rng.choice([10, 100, VALUE_LIMIT])
    nums = [rng.randint(0, limit) for _ in range(length)]
    return {"nums": nums, "k": rng.randint(1, 50)}


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, 1), MAX_LENGTH)
    if length <= SMALL_LENGTH and rng.random() < RANDOM_SHARE:
        return _random_input(rng, length)
    k = rng.randint(length + 2, VALUE_LIMIT)
    # remainders[t] is the remainder of the first t values; all distinct for now.
    remainders = [0] + rng.sample(range(1, k), length)
    if length >= 2 and rng.random() < PLANTED_SHARE:
        tail = max(length // TAIL_SHARE, 1)
        earlier = rng.randint(max(length - 1 - tail, 0), length - 2)
        remainders[length] = remainders[earlier]
    nums = []
    for before, after in zip(remainders, remainders[1:]):
        step = (after - before) % k
        nums.append(step + k * rng.randint(0, (VALUE_LIMIT - step) // k))
    return {"nums": nums, "k": k}


def validate(case_input: dict) -> None:
    nums, k = case_input["nums"], case_input["k"]
    assert 1 <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(0 <= value <= VALUE_LIMIT for value in nums), "value out of range"
    assert 1 <= k <= K_LIMIT, "k out of range"
