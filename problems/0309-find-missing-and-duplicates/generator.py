"""Seeded inputs for find-missing-and-duplicates: a shuffled permutation with a few values overwritten.

The array starts as a random ordering of 1..n. Then `gaps` positions are overwritten with
copies of values taken from other positions, so each overwritten value goes missing and the
copied ones appear twice, or three times when two positions copy the same value.

Up to 30 values the number of gaps is anything from 0 (a permutation) to n / 2, so the
oracle cross-check sees permutations, heavy repetition and everything between. Above that it
is 1 to 3 at every seed, so the answer stays tiny while n grows: the memory a hash set needs
then stands out against the constant memory of the swap and sort approaches, and the time of
every approach is the work on n values, not on the size of the output.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
SMALL_LENGTH = 30
MAX_LARGE_GAPS = 3


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    nums = list(range(1, length + 1))
    rng.shuffle(nums)
    gaps = _gap_count(rng, length)
    positions = rng.sample(range(length), length)
    overwritten, kept = positions[:gaps], positions[gaps:]
    for position in overwritten:
        nums[position] = nums[rng.choice(kept)]
    return {"nums": nums}


def _gap_count(rng: random.Random, length: int) -> int:
    if length <= SMALL_LENGTH:
        return rng.randint(0, length // 2)
    return rng.randint(1, MAX_LARGE_GAPS)


def validate(case_input: dict) -> None:
    nums = case_input["nums"]
    assert MIN_LENGTH <= len(nums) <= MAX_LENGTH, "length out of range"
    assert all(1 <= value <= len(nums) for value in nums), "value out of range"
