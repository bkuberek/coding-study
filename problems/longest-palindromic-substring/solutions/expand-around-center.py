def longest_palindrome(s: str) -> str:
    best_start, best_length = 0, 1
    # Center c sits on character c // 2 when c is even, between two characters when c is odd.
    for center in range(2 * len(s) - 1):
        left, right = center // 2, (center + 1) // 2
        while left >= 0 and right < len(s) and s[left] == s[right]:
            left -= 1
            right += 1
        # The loop overshoots by one on each side: the palindrome is s[left + 1 .. right - 1].
        if right - left - 1 > best_length:
            best_start, best_length = left + 1, right - left - 1
    return s[best_start : best_start + best_length]
