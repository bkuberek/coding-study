def subsets(nums: list[int]) -> list[list[int]]:
    # Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
    return [
        [value for i, value in enumerate(nums) if mask >> i & 1]
        for mask in range(1 << len(nums))
    ]
