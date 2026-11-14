def valid_palindrome(s: str) -> bool:
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return _is_palindrome(s, left + 1, right) or _is_palindrome(s, left, right - 1)
        left += 1
        right -= 1
    return True


def _is_palindrome(s: str, left: int, right: int) -> bool:
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
