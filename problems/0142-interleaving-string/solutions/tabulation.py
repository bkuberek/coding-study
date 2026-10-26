def is_interleave(s1: str, s2: str, s3: str) -> bool:
    rows, columns = len(s1), len(s2)
    if rows + columns != len(s3):
        return False
    # reach[i][j]: s1[:i] and s2[:j] interleave to s3[:i + j].
    reach = [[False] * (columns + 1) for _ in range(rows + 1)]
    reach[0][0] = True
    for i in range(rows + 1):
        for j in range(columns + 1):
            # The last character of s3[:i + j] came from s1 or from s2.
            if i > 0 and reach[i - 1][j] and s1[i - 1] == s3[i + j - 1]:
                reach[i][j] = True
            elif j > 0 and reach[i][j - 1] and s2[j - 1] == s3[i + j - 1]:
                reach[i][j] = True
    return reach[rows][columns]
