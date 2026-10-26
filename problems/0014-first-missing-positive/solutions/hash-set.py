def first_missing_positive(nums: list[int]) -> int:
    present = set(nums)
    # The answer is at most len(nums) + 1, so this loop runs at most n + 1 times.
    candidate = 1
    while candidate in present:
        candidate += 1
    return candidate
