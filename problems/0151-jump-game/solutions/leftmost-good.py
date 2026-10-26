def can_jump(nums: list[int]) -> bool:
    goal = len(nums) - 1  # the leftmost index known to reach the last index
    for i in range(len(nums) - 2, -1, -1):
        if i + nums[i] >= goal:
            goal = i
    return goal == 0
