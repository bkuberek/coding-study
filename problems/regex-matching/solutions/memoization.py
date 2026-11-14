def is_match(s: str, p: str) -> bool:
    # known[i][j] caches whether s[i:] matches p[j:]; None is unknown.
    known: list[list[bool | None]] = [[None] * (len(p) + 1) for _ in range(len(s) + 1)]

    def solve(i: int, j: int) -> bool:
        if j == len(p):
            return i == len(s)
        cached = known[i][j]
        if cached is None:
            first = i < len(s) and p[j] in (s[i], ".")
            if j + 1 < len(p) and p[j + 1] == "*":
                # Skip "x*" entirely, or let it eat one more character and stay on it.
                cached = solve(i, j + 2) or (first and solve(i + 1, j))
            else:
                cached = first and solve(i + 1, j + 1)
            known[i][j] = cached
        return cached

    return solve(0, 0)
