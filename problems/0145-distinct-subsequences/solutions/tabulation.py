def num_distinct(s: str, t: str) -> int:
    rows, columns = len(s), len(t)
    # ways[i][j] counts the occurrences of t[:j] in s[:i]; the empty t[:0] occurs once.
    ways = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows + 1):
        ways[i][0] = 1
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            # Occurrences that skip s[i - 1], plus those that match it with t[j - 1].
            ways[i][j] = ways[i - 1][j]
            if s[i - 1] == t[j - 1]:
                ways[i][j] += ways[i - 1][j - 1]
    return ways[rows][columns]
