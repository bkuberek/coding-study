def character_replacement(s: str, k: int) -> int:
    best = 0
    for target in set(s):
        left = 0
        others = 0
        for right, ch in enumerate(s):
            if ch != target:
                others += 1
            while others > k:
                if s[left] != target:
                    others -= 1
                left += 1
            best = max(best, right - left + 1)
    return best
