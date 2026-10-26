def longest_consecutive(nums: list[int]) -> int:
    if not nums:
        return 0
    ordered = sorted(nums)
    longest = current = 1
    for previous, value in zip(ordered, ordered[1:]):
        if value == previous:
            continue
        current = current + 1 if value == previous + 1 else 1
        longest = max(longest, current)
    return longest
