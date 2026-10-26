"""Accept exactly the correctly nested strings with n pairs, each once, in any order.

Every listed string is checked for validity and duplicates, and then the count is compared
with the n-th Catalan number, the number of correctly nested strings with n pairs. Distinct
valid strings that are as many as all valid strings are all of them, so no list of expected
strings needs to be stored: at n = 10 there are 16,796 of them.
"""

from math import comb


def _is_nested(text: str, pairs: int) -> bool:
    if len(text) != 2 * pairs:
        return False
    depth = 0
    for bracket in text:
        if bracket == "(":
            depth += 1
        elif bracket == ")":
            depth -= 1
        else:
            return False
        if depth < 0:
            return False
    return depth == 0


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    pairs = case_input["n"]
    if not isinstance(output, list) or not all(isinstance(text, str) for text in output):
        return f"expected a list of strings, got {output!r}"[:200]
    seen: set[str] = set()
    for text in output:
        if text in seen:
            return f"{text!r} is listed more than once"
        if not _is_nested(text, pairs):
            return f"{text!r} is not a correctly nested string with {pairs} pairs"
        seen.add(text)
    total = comb(2 * pairs, pairs) // (pairs + 1)
    if len(seen) != total:
        return f"listed {len(seen)} strings, but {pairs} pairs have {total} correctly nested strings"
    return None
