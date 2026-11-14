from functools import cache


def can_partition(nums: list[int]) -> bool:
    total = sum(nums)
    if total % 2 == 1:
        return False

    @cache
    def reachable(index: int, remaining: int) -> bool:
        # Can some elements of nums[index:] add up to exactly `remaining`?
        if remaining == 0:
            return True
        if index == len(nums) or remaining < 0:
            return False
        return reachable(index + 1, remaining - nums[index]) or reachable(index + 1, remaining)

    return reachable(0, total // 2)
