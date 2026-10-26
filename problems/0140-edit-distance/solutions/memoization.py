def min_distance(word1: str, word2: str) -> int:
    # cost[i][j] caches the distance between the suffixes word1[i:] and word2[j:]; -1 is unknown.
    cost = [[-1] * (len(word2) + 1) for _ in range(len(word1) + 1)]

    def solve(i: int, j: int) -> int:
        if i == len(word1):
            return len(word2) - j  # insert the rest of word2
        if j == len(word2):
            return len(word1) - i  # delete the rest of word1
        if cost[i][j] < 0:
            if word1[i] == word2[j]:
                cost[i][j] = solve(i + 1, j + 1)
            else:
                cost[i][j] = 1 + min(
                    solve(i + 1, j),  # delete word1[i]
                    solve(i, j + 1),  # insert word2[j]
                    solve(i + 1, j + 1),  # replace word1[i] with word2[j]
                )
        return cost[i][j]

    return solve(0, 0)
