def longest_consecutive(nums: list[int]) -> int:
    longest = 0
    for i, value in enumerate(nums):
        # `in` and `index` on a list are linear scans in C: O(n) per check.
        if value - 1 in nums:
            continue
        if nums.index(value) < i:
            continue  # an earlier copy of this start already counted its run
        length = 1
        while value + length in nums:
            length += 1
        longest = max(longest, length)
    return longest
