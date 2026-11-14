def max_coins(nums: list[int]) -> int:
    # Pad with the virtual balloons of value 1 at both ends.
    values = [1, *nums, 1]
    # best[left][right] caches the most coins from bursting every balloon strictly between
    # left and right, while those two are still standing; -1 is unknown.
    best = [[-1] * len(values) for _ in range(len(values))]

    def solve(left: int, right: int) -> int:
        if right - left < 2:
            return 0
        if best[left][right] < 0:
            # Choose the balloon `last` that is burst last between them: its neighbors are then
            # exactly left and right, and the two sides are independent.
            best[left][right] = max(
                solve(left, last) + values[left] * values[last] * values[right] + solve(last, right)
                for last in range(left + 1, right)
            )
        return best[left][right]

    return solve(0, len(values) - 1)
