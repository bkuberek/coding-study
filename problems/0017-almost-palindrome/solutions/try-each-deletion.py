def valid_palindrome(s: str) -> bool:
    if s == s[::-1]:
        return True
    for index in range(len(s)):
        candidate = s[:index] + s[index + 1 :]
        if candidate == candidate[::-1]:
            return True
    return False
