def contains_duplicate(nums: list[int]) -> bool:
    for i, value in enumerate(nums):
        try:
            # list.index scans nums[i + 1:] in C: still one comparison per later element.
            nums.index(value, i + 1)
        except ValueError:
            continue
        return True
    return False
