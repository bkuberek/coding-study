def climb_stairs(n: int) -> int:
    # ways[step] counts the move sequences that end exactly on `step`.
    ways = [0] * (n + 1)
    ways[0] = 1
    ways[1] = 1
    for step in range(2, n + 1):
        ways[step] = ways[step - 1] + ways[step - 2]
    return ways[n]
