def first_missing_positive(nums: list[int]) -> int:
    candidate = 1
    # `in` on a list is a linear scan in C: O(n) per candidate.
    while candidate in nums:
        candidate += 1
    return candidate
