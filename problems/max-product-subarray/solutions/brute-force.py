def max_product(nums: list[int]) -> int:
    best = nums[0]
    for start in range(len(nums)):
        product = 1
        for end in range(start, len(nums)):
            product *= nums[end]
            best = max(best, product)
    return best
