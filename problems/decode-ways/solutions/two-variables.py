def num_decodings(s: str) -> int:
    # Before digit i: one_back counts readings of s[:i] and two_back those of s[:i - 1].
    two_back, one_back = 0, 1
    previous_digit = ""
    for digit in s:
        current = one_back if digit != "0" else 0
        if previous_digit and 10 <= int(previous_digit + digit) <= 26:
            current += two_back
        two_back, one_back = one_back, current
        previous_digit = digit
    return one_back
