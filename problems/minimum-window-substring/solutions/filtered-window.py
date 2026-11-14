from collections import Counter


def min_window(s: str, t: str) -> str:
    deficit = Counter(t)
    useful = [(index, ch) for index, ch in enumerate(s) if ch in deficit]
    missing = len(t)
    best_start, best_length = 0, 0
    left = 0
    for right, ch in useful:
        if deficit[ch] > 0:
            missing -= 1
        deficit[ch] -= 1
        while missing == 0:
            start, leaving = useful[left]
            if best_length == 0 or right - start + 1 < best_length:
                best_start, best_length = start, right - start + 1
            deficit[leaving] += 1
            if deficit[leaving] > 0:
                missing += 1
            left += 1
    return s[best_start : best_start + best_length]
