def is_match(s: str, p: str) -> bool:
    columns = len(p)
    # previous[j]: s[:i - 1] matches p[:j]; current[j]: s[:i] matches p[:j].
    previous: list[bool] = []
    for i in range(len(s) + 1):
        current = [False] * (columns + 1)
        current[0] = i == 0
        for j in range(1, columns + 1):
            if p[j - 1] == "*":
                # "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                current[j] = current[j - 2] or (
                    i > 0 and p[j - 2] in (s[i - 1], ".") and previous[j]
                )
            else:
                current[j] = i > 0 and p[j - 1] in (s[i - 1], ".") and previous[j - 1]
        previous = current
    return previous[columns]
