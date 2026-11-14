def find_target_sum_ways(nums: list[int], target: int) -> int:
    total = sum(nums)
    # With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
    if abs(target) > total or (total + target) % 2:
        return 0
    plus = (total + target) // 2
    # ways[p] counts the subsets of the values seen so far that add up to p.
    ways = [1] + [0] * plus
    for value in nums:
        # Decreasing p: ways[p - value] still excludes this value, so it is used at most once.
        for p in range(plus, value - 1, -1):
            ways[p] += ways[p - value]
    return ways[plus]
