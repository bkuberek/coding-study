from collections import Counter


def subarray_sum(nums: list[int], k: int) -> int:
    # seen[s] counts the prefixes seen so far whose sum is s; the empty prefix sums to 0.
    seen = Counter({0: 1})
    total = 0
    count = 0
    for value in nums:
        total += value
        # Counter returns 0 for a missing key without inserting it.
        count += seen[total - k]
        seen[total] += 1
    return count
