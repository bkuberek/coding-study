"""Seeded inputs for median-of-two-sorted-arrays.

`n` is the total length m + n. The split between the two arrays is uniform (either array
can be empty, and the total is at least 1). Values are drawn from [-10^6, 10^6] and sorted;
long arrays therefore contain repeats, and the two arrays interleave. Sorting the
concatenation costs (m + n) log(m + n), merging up to the middle costs (m + n) / 2 steps,
and the partition search costs about log2(min(m, n)) probes.
"""

import random

MAX_LENGTH = 10**5
VALUE_LIMIT = 10**6


def generate(rng: random.Random, n: int) -> dict:
    total = min(max(n, 1), 2 * MAX_LENGTH)
    first = rng.randint(max(0, total - MAX_LENGTH), min(total, MAX_LENGTH))
    nums1 = sorted(rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(first))
    nums2 = sorted(rng.randint(-VALUE_LIMIT, VALUE_LIMIT) for _ in range(total - first))
    return {"nums1": nums1, "nums2": nums2}


def validate(case_input: dict) -> None:
    nums1, nums2 = case_input["nums1"], case_input["nums2"]
    assert len(nums1) <= MAX_LENGTH and len(nums2) <= MAX_LENGTH, "length out of range"
    assert len(nums1) + len(nums2) >= 1, "at least one value is required"
    for nums in (nums1, nums2):
        assert all(-VALUE_LIMIT <= value <= VALUE_LIMIT for value in nums), "value out of range"
        assert all(left <= right for left, right in zip(nums, nums[1:])), "arrays must be sorted"
