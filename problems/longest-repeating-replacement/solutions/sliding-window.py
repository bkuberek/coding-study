def character_replacement(s: str, k: int) -> int:
    counts = [0] * 26
    most = 0
    left = 0
    best = 0
    for right, ch in enumerate(s):
        letter = ord(ch) - 65
        counts[letter] += 1
        most = max(most, counts[letter])
        if right - left + 1 - most > k:
            counts[ord(s[left]) - 65] -= 1
            left += 1
        best = max(best, right - left + 1)
    return best
