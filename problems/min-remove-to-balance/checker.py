"""Accepts any balanced string that deletes the minimum number of parentheses from `s`."""

PARENTHESES = "()"


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    s = case_input["s"]
    if not isinstance(output, str):
        return "the result must be a string"
    if not _is_subsequence(output, s):
        return "the result is not s with some characters deleted"
    if _letters(output) != _letters(s):
        return "letters must not be deleted"
    if not _is_balanced(output):
        return "the result is not balanced"
    deleted, minimum = len(s) - len(output), _minimum_deletions(s)
    if deleted != minimum:
        return f"deleted {deleted} parentheses, but {minimum} are enough"
    return None


def _is_subsequence(candidate: str, s: str) -> bool:
    remaining = iter(s)
    # `in` advances the shared iterator, so each match starts after the previous one.
    return all(character in remaining for character in candidate)


def _letters(text: str) -> str:
    return "".join(character for character in text if character not in PARENTHESES)


def _is_balanced(text: str) -> bool:
    depth = 0
    for character in text:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _minimum_deletions(s: str) -> int:
    """Unmatched closers plus the openers still open at the end."""
    depth = unmatched_closers = 0
    for character in s:
        if character == "(":
            depth += 1
        elif character == ")":
            if depth:
                depth -= 1
            else:
                unmatched_closers += 1
    return unmatched_closers + depth
