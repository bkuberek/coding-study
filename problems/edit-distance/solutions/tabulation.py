def min_distance(word1: str, word2: str) -> int:
    rows, columns = len(word1), len(word2)
    # cost[i][j] is the distance between the prefixes word1[:i] and word2[:j]. Turning a prefix
    # into the empty word takes one deletion per character, and the reverse one insertion.
    cost = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows + 1):
        cost[i][0] = i
    for j in range(columns + 1):
        cost[0][j] = j
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            if word1[i - 1] == word2[j - 1]:
                cost[i][j] = cost[i - 1][j - 1]
            else:
                cost[i][j] = 1 + min(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1])
    return cost[rows][columns]
