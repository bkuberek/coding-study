def length_of_longest_substring(s: str) -> int:
    best = 0
    for start in range(len(s)):
        seen: set[str] = set()
        for end in range(start, len(s)):
            if s[end] in seen:
                break
            seen.add(s[end])
        best = max(best, len(seen))
    return best
