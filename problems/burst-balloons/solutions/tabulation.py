def max_coins(nums: list[int]) -> int:
    values = [1, *nums, 1]
    size = len(values)
    # best[left][right]: most coins from bursting everything strictly between left and right.
    best = [[0] * size for _ in range(size)]
    # An interval only depends on shorter ones, so fill by increasing gap right - left.
    for gap in range(2, size):
        for left in range(size - gap):
            right = left + gap
            outer = values[left] * values[right]
            row = best[left]
            row[right] = max(
                row[last] + outer * values[last] + best[last][right] for last in range(left + 1, right)
            )
    return best[0][size - 1]
