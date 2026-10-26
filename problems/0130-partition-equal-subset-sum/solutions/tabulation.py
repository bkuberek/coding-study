def can_partition(nums: list[int]) -> bool:
    total = sum(nums)
    if total % 2 == 1:
        return False
    target = total // 2
    # reach[i][s] is True when some of the first i elements add up to exactly s.
    reach = [[False] * (target + 1) for _ in range(len(nums) + 1)]
    reach[0][0] = True
    for i, value in enumerate(nums, start=1):
        previous, current = reach[i - 1], reach[i]
        for s in range(target + 1):
            current[s] = previous[s] or (s >= value and previous[s - value])
    return reach[len(nums)][target]
