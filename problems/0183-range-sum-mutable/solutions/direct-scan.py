class NumArray:
    def __init__(self, nums: list[int]) -> None:
        self.nums = list(nums)

    def update(self, index: int, value: int) -> None:
        self.nums[index] = value

    def sum_range(self, left: int, right: int) -> int:
        return sum(self.nums[left : right + 1])
