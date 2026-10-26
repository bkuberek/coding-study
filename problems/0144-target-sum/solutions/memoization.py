from functools import cache


def find_target_sum_ways(nums: list[int], target: int) -> int:
    # At most len(nums) * (2 * sum(nums) + 1) states, about 40,000 here, so a dict cache is fine.
    @cache
    def count(index: int, total: int) -> int:
        if index == len(nums):
            return 1 if total == target else 0
        return count(index + 1, total + nums[index]) + count(index + 1, total - nums[index])

    return count(0, 0)
