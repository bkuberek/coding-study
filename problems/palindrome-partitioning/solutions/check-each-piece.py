def partition(s: str) -> list[list[str]]:
    result: list[list[str]] = []
    pieces: list[str] = []

    def is_palindrome(left: int, right: int) -> bool:
        while left < right:
            if s[left] != s[right]:
                return False
            left += 1
            right -= 1
        return True

    def cut_from(start: int) -> None:
        if start == len(s):
            result.append(pieces.copy())
            return
        for end in range(start, len(s)):
            if is_palindrome(start, end):
                pieces.append(s[start : end + 1])
                cut_from(end + 1)
                pieces.pop()

    cut_from(0)
    return result
