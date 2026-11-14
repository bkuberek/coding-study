def split_array(nums: list[int], k: int) -> int:
    # Feasibility only improves as the limit grows: find the smallest feasible limit.
    low, high = max(nums), sum(nums)
    while low < high:
        limit = (low + high) // 2
        if _pieces_needed(nums, limit) <= k:
            high = limit
        else:
            low = limit + 1
    return low


def _pieces_needed(nums: list[int], limit: int) -> int:
    # Greedy: extend the current piece while it fits under the limit.
    pieces, running = 1, 0
    for value in nums:
        if running + value > limit:
            pieces += 1
            running = value
        else:
            running += value
    return pieces
