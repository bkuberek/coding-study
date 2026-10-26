def min_window(s: str, t: str) -> str:
    deficit = [0] * 128
    for ch in t:
        deficit[ord(ch)] += 1
    missing = len(t)
    best_start, best_length = 0, 0
    left = 0
    for right, ch in enumerate(s):
        code = ord(ch)
        if deficit[code] > 0:
            missing -= 1
        deficit[code] -= 1
        while missing == 0:
            if best_length == 0 or right - left + 1 < best_length:
                best_start, best_length = left, right - left + 1
            leaving = ord(s[left])
            deficit[leaving] += 1
            if deficit[leaving] > 0:
                missing += 1
            left += 1
    return s[best_start : best_start + best_length]
