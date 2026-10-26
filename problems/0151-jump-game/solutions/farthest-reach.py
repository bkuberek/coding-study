def can_jump(nums: list[int]) -> bool:
    farthest = 0  # every index up to `farthest` is reachable
    for i, jump in enumerate(nums):
        if i > farthest:
            return False
        farthest = max(farthest, i + jump)
    return True
