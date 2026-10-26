def count_smaller(nums: list[int]) -> list[int]:
    return [sum(1 for later in nums[i + 1 :] if later < value) for i, value in enumerate(nums)]
