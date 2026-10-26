from itertools import accumulate


class NumArray:
    def __init__(self, nums: list[int]) -> None:
        # prefix[i] is the sum of nums[:i]; the leading 0 makes ranges that start at 0 uniform.
        self.prefix = list(accumulate(nums, initial=0))

    def sum_range(self, left: int, right: int) -> int:
        return self.prefix[right + 1] - self.prefix[left]
