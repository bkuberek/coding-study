def rob(nums: list[int]) -> int:
    # best[i] is the most cash obtainable from the first i houses.
    best = [0] * (len(nums) + 1)
    best[1] = nums[0]
    for i in range(2, len(nums) + 1):
        best[i] = max(best[i - 1], best[i - 2] + nums[i - 1])
    return best[len(nums)]
