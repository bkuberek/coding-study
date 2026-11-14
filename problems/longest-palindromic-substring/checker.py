"""Accept any palindromic substring of s whose length is the maximum."""


def _longest_length(s: str) -> int:
    best = 0
    for center in range(2 * len(s) - 1):
        left, right = center // 2, (center + 1) // 2
        while left >= 0 and right < len(s) and s[left] == s[right]:
            left -= 1
            right += 1
        best = max(best, right - left - 1)
    return best


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    s = case_input["s"]
    if not isinstance(output, str):
        return f"expected a string, got {output!r}"
    if output not in s:
        return f"{output!r} is not a substring of s"
    if output != output[::-1]:
        return f"{output!r} is not a palindrome"
    longest = _longest_length(s)
    if len(output) != longest:
        return f"{output!r} has length {len(output)}, but the longest palindrome has length {longest}"
    return None
