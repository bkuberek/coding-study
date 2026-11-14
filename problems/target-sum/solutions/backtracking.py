def find_target_sum_ways(nums: list[int], target: int) -> int:
    def count(index: int, total: int) -> int:
        if index == len(nums):
            return 1 if total == target else 0
        # Give nums[index] a plus sign, then a minus sign.
        return count(index + 1, total + nums[index]) + count(index + 1, total - nums[index])

    return count(0, 0)
