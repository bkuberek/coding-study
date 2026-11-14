from functools import cache


def length_of_lis(nums: list[int]) -> int:
    @cache
    def longest_from(start: int) -> int:
        # Length of the longest increasing subsequence whose first element is nums[start].
        best = 1
        for following in range(start + 1, len(nums)):
            if nums[following] > nums[start]:
                best = max(best, 1 + longest_from(following))
        return best

    return max(longest_from(start) for start in range(len(nums)))
