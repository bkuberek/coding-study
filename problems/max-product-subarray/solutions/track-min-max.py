def max_product(nums: list[int]) -> int:
    # largest and smallest are the extreme products of subarrays that end at the current index.
    largest = smallest = best = nums[0]
    for value in nums[1:]:
        candidates = (value, largest * value, smallest * value)
        largest, smallest = max(candidates), min(candidates)
        best = max(best, largest)
    return best
