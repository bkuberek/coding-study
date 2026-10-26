def length_of_longest_substring(s: str) -> int:
    last_seen: dict[str, int] = {}
    left = 0
    best = 0
    for right, ch in enumerate(s):
        previous = last_seen.get(ch)
        if previous is not None and previous >= left:
            left = previous + 1
        last_seen[ch] = right
        best = max(best, right - left + 1)
    return best
