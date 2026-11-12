def find_all_occurrences(text: str, pattern: str) -> list[int]:
    border = _border_table(pattern)
    found = []
    matched = 0
    for position, letter in enumerate(text):
        while matched > 0 and letter != pattern[matched]:
            matched = border[matched - 1]
        if letter == pattern[matched]:
            matched += 1
        if matched == len(pattern):
            found.append(position - len(pattern) + 1)
            matched = border[matched - 1]
    return found


def _border_table(pattern: str) -> list[int]:
    # border[i] is the length of the longest proper prefix of pattern[: i + 1] that is also a suffix of it.
    border = [0] * len(pattern)
    length = 0
    for i in range(1, len(pattern)):
        while length > 0 and pattern[i] != pattern[length]:
            length = border[length - 1]
        if pattern[i] == pattern[length]:
            length += 1
        border[i] = length
    return border
