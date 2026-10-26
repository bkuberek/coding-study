def min_remove_to_make_valid(s: str) -> str:
    while (position := _first_offender(s)) is not None:
        s = s[:position] + s[position + 1 :]
    return s


def _first_offender(s: str) -> int | None:
    """A parenthesis that cannot be matched, or None when `s` is balanced."""
    depth = 0
    for position, character in enumerate(s):
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return position  # a closer with nothing open before it
            depth -= 1
    if depth == 0:
        return None
    # Some openers are never closed: the last opener with no closer left after it is one.
    closers = 0
    for position in range(len(s) - 1, -1, -1):
        if s[position] == ")":
            closers += 1
        elif s[position] == "(":
            if closers == 0:
                return position
            closers -= 1
    return None
