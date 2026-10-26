def longest_consecutive(nums: list[int]) -> int:
    present = set(nums)
    longest = 0
    for value in present:
        if value - 1 in present:
            continue
        end = value + 1
        while end in present:
            end += 1
        longest = max(longest, end - value)
    return longest
