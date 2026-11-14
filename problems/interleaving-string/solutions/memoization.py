def is_interleave(s1: str, s2: str, s3: str) -> bool:
    if len(s1) + len(s2) != len(s3):
        return False
    # known[i][j] caches whether s1[i:] and s2[j:] interleave to s3[i + j:]; None is unknown.
    known: list[list[bool | None]] = [[None] * (len(s2) + 1) for _ in range(len(s1) + 1)]

    def solve(i: int, j: int) -> bool:
        if i == len(s1) and j == len(s2):
            return True
        cached = known[i][j]
        if cached is None:
            # The next character of s3 comes from s1 or from s2.
            cached = (i < len(s1) and s1[i] == s3[i + j] and solve(i + 1, j)) or (
                j < len(s2) and s2[j] == s3[i + j] and solve(i, j + 1)
            )
            known[i][j] = cached
        return cached

    return solve(0, 0)
