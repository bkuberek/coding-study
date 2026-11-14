def max_sub_array(nums: list[int]) -> int:
    def best_in(low: int, high: int) -> int:
        # The best subarray sum within nums[low..high] (inclusive).
        if low == high:
            return nums[low]
        middle = (low + high) // 2
        # The best crossing subarray is a best suffix of the left half plus a best prefix of
        # the right half.
        left_suffix, total = nums[middle], 0
        for i in range(middle, low - 1, -1):
            total += nums[i]
            left_suffix = max(left_suffix, total)
        right_prefix, total = nums[middle + 1], 0
        for i in range(middle + 1, high + 1):
            total += nums[i]
            right_prefix = max(right_prefix, total)
        return max(best_in(low, middle), best_in(middle + 1, high), left_suffix + right_prefix)

    return best_in(0, len(nums) - 1)
