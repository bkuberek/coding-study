def longest_common_subsequence(text1: str, text2: str) -> int:
    # best[i][j] caches the answer for the suffixes text1[i:] and text2[j:]; -1 is unknown.
    best = [[-1] * len(text2) for _ in range(len(text1))]

    def solve(i: int, j: int) -> int:
        if i == len(text1) or j == len(text2):
            return 0
        if best[i][j] < 0:
            if text1[i] == text2[j]:
                best[i][j] = 1 + solve(i + 1, j + 1)
            else:
                best[i][j] = max(solve(i + 1, j), solve(i, j + 1))
        return best[i][j]

    return solve(0, 0)
