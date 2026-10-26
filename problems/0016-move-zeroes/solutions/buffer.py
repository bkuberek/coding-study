def move_zeroes(nums: list[int]) -> None:
    non_zero = [value for value in nums if value != 0]
    nums[:] = non_zero + [0] * (len(nums) - len(non_zero))
