def missing_number(nums: list[int]) -> int:
    # Start with n, then fold in every index and value; present numbers cancel in pairs.
    result = len(nums)
    for index, value in enumerate(nums):
        result ^= index ^ value
    return result
