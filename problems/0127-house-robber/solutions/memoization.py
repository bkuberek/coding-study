from functools import cache


def rob(nums: list[int]) -> int:
    @cache
    def best_from(house: int) -> int:
        # The most cash obtainable from houses house, house + 1, ..., the last one.
        if house >= len(nums):
            return 0
        skip = best_from(house + 1)
        take = nums[house] + best_from(house + 2)
        return max(skip, take)

    return best_from(0)
