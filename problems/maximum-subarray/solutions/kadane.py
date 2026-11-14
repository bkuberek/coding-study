def max_sub_array(nums: list[int]) -> int:
    # ending_here is the best sum of a subarray that ends at the current index.
    ending_here = best = nums[0]
    for index in range(1, len(nums)):
        ending_here = max(nums[index], ending_here + nums[index])
        best = max(best, ending_here)
    return best
