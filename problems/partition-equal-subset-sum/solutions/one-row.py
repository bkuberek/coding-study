def can_partition(nums: list[int]) -> bool:
    total = sum(nums)
    if total % 2 == 1:
        return False
    target = total // 2
    # reachable[s] is True when some of the elements seen so far add up to exactly s.
    reachable = [False] * (target + 1)
    reachable[0] = True
    for value in nums:
        # Right to left, so reachable[s - value] still describes the elements before `value`.
        for s in range(target, value - 1, -1):
            if reachable[s - value]:
                reachable[s] = True
        if reachable[target]:
            return True
    return reachable[target]
