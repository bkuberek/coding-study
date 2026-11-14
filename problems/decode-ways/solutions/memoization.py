from functools import cache


def num_decodings(s: str) -> int:
    @cache
    def ways_from(start: int) -> int:
        # The number of readings of the suffix s[start:].
        if start == len(s):
            return 1
        if s[start] == "0":
            return 0
        count = ways_from(start + 1)
        if start + 1 < len(s) and 10 <= int(s[start : start + 2]) <= 26:
            count += ways_from(start + 2)
        return count

    return ways_from(0)
