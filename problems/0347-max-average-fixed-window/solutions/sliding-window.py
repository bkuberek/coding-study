def max_window_average(nums: list[int], k: int) -> float:
    window_sum = sum(nums[:k])
    best = window_sum
    for right in range(k, len(nums)):
        # Slide one step: the number at `right` enters and the one k places back leaves.
        window_sum += nums[right] - nums[right - k]
        best = max(best, window_sum)
    # Every window has k numbers, so the largest sum is the largest average. Divide once.
    return best / k
