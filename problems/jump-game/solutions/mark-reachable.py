def can_jump(nums: list[int]) -> bool:
    last = len(nums) - 1
    # reachable[i] is True once some sequence of jumps from index 0 is known to land on i.
    reachable = [False] * len(nums)
    reachable[0] = True
    for i in range(len(nums)):
        if not reachable[i]:
            continue
        if i == last:
            return True
        for target in range(i + 1, min(last, i + nums[i]) + 1):
            reachable[target] = True
    return reachable[last]
