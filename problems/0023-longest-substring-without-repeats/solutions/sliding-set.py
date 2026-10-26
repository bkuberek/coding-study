def length_of_longest_substring(s: str) -> int:
    window: set[str] = set()
    left = 0
    best = 0
    for ch in s:
        while ch in window:
            window.remove(s[left])
            left += 1
        window.add(ch)
        best = max(best, len(window))
    return best
