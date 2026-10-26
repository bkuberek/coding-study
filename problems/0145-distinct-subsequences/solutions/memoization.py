def num_distinct(s: str, t: str) -> int:
    # ways[i][j] caches the occurrences of t[j:] as a subsequence of s[i:]; -1 is unknown.
    ways = [[-1] * len(t) for _ in range(len(s))]

    def count(i: int, j: int) -> int:
        if j == len(t):
            return 1  # the empty suffix of t occurs once
        if len(s) - i < len(t) - j:
            return 0  # not enough characters left in s
        if ways[i][j] < 0:
            # Either s[i] is skipped, or it is matched with t[j].
            ways[i][j] = count(i + 1, j) + (count(i + 1, j + 1) if s[i] == t[j] else 0)
        return ways[i][j]

    return count(0, 0)
