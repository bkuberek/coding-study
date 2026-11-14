from collections import Counter


def min_window(s: str, t: str) -> str:
    need = Counter(t)
    best_start, best_length = 0, 0
    for start in range(len(s)):
        remaining = dict(need)
        missing = len(t)
        for end in range(start, len(s)):
            count = remaining.get(s[end])
            if count is not None:
                if count > 0:
                    missing -= 1
                remaining[s[end]] = count - 1
            if missing == 0:
                if best_length == 0 or end - start + 1 < best_length:
                    best_start, best_length = start, end - start + 1
                break
    return s[best_start : best_start + best_length]
