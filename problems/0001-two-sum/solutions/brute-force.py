def two_sum(nums: list[int], target: int) -> list[int]:
    for i, value in enumerate(nums):
        complement = target - value
        try:
            # list.index scans nums[i + 1:] in C: still one check per later element.
            return [i, nums.index(complement, i + 1)]
        except ValueError:
            continue
    return []
