def find_target_sum_ways(nums: list[int], target: int) -> int:
    total = sum(nums)
    if abs(target) > total:
        return 0
    # ways[i][running + total] counts the sign assignments of nums[:i] with that running total.
    ways = [[0] * (2 * total + 1) for _ in range(len(nums) + 1)]
    ways[0][total] = 1
    for i, value in enumerate(nums):
        for offset, count in enumerate(ways[i]):
            if count:
                ways[i + 1][offset + value] += count
                ways[i + 1][offset - value] += count
    return ways[len(nums)][target + total]
