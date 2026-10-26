def is_match(s: str, p: str) -> bool:
    rows, columns = len(s), len(p)
    # matches[i][j]: s[:i] matches p[:j].
    matches = [[False] * (columns + 1) for _ in range(rows + 1)]
    matches[0][0] = True
    for i in range(rows + 1):
        for j in range(1, columns + 1):
            if p[j - 1] == "*":
                # "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                matches[i][j] = matches[i][j - 2] or (
                    i > 0 and p[j - 2] in (s[i - 1], ".") and matches[i - 1][j]
                )
            else:
                matches[i][j] = i > 0 and p[j - 1] in (s[i - 1], ".") and matches[i - 1][j - 1]
    return matches[rows][columns]
