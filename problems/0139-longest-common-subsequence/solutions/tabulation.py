def longest_common_subsequence(text1: str, text2: str) -> int:
    rows, columns = len(text1), len(text2)
    # best[i][j] is the answer for the prefixes text1[:i] and text2[:j]; row and column 0
    # stand for an empty prefix.
    best = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            if text1[i - 1] == text2[j - 1]:
                best[i][j] = best[i - 1][j - 1] + 1
            else:
                best[i][j] = max(best[i - 1][j], best[i][j - 1])
    return best[rows][columns]
