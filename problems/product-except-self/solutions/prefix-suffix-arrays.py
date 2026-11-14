def product_except_self(nums: list[int]) -> list[int]:
    n = len(nums)
    left = [1] * n  # left[i] is the product of nums[:i]
    for i in range(1, n):
        left[i] = left[i - 1] * nums[i - 1]
    right = [1] * n  # right[i] is the product of nums[i + 1:]
    for i in range(n - 2, -1, -1):
        right[i] = right[i + 1] * nums[i + 1]
    return [before * after for before, after in zip(left, right)]
