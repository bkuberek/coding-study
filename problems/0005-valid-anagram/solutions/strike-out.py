def is_anagram(s: str, t: str) -> bool:
    if len(s) != len(t):
        return False
    remaining = list(t)
    for letter in s:
        try:
            # list.index scans from the front in C; a struck-out slot holds "" and never matches.
            position = remaining.index(letter)
        except ValueError:
            return False
        remaining[position] = ""
    return True
