def longest_palindrome(s: str) -> str:
    n = len(s)
    # is_palindrome[i][j] tells whether s[i..j] (inclusive) is a palindrome.
    is_palindrome = [[False] * n for _ in range(n)]
    best_start, best_length = 0, 1
    for i in range(n):
        is_palindrome[i][i] = True
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j] and (length == 2 or is_palindrome[i + 1][j - 1]):
                is_palindrome[i][j] = True
                best_start, best_length = i, length
    return s[best_start : best_start + best_length]
