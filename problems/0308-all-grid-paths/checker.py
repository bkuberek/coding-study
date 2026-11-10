"""Accept exactly the list of every grid path, each once, in ascending order with D before R.

Each listed string is checked for its characters and its numbers of downs and rights, and
each must be greater than the one before it, which also rules out duplicates. The count is
then compared with C(2n - 2, n - 1), the number of orders of n - 1 downs and n - 1 rights.
Strictly ascending distinct valid strings that are as many as all valid strings are all of
them, in the one allowed order, so no list of expected strings needs to be stored: at n = 10
there are 48,620 of them.
"""

from math import comb

DOWN = "D"
RIGHT = "R"


def _problem_with_path(text: object, moves: int) -> str | None:
    if not isinstance(text, str):
        return f"expected a string, got {text!r}"
    if len(text) != 2 * moves or text.count(DOWN) != moves or text.count(RIGHT) != moves:
        return f"{text!r} is not {moves} downs and {moves} rights"
    return None


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    moves = case_input["n"] - 1
    if not isinstance(output, list):
        return f"expected a list of strings, got {output!r}"[:200]
    for index, text in enumerate(output):
        problem = _problem_with_path(text, moves)
        if problem is not None:
            return problem[:200]
        if index > 0 and text <= output[index - 1]:
            return f"{text!r} at index {index} does not come after {output[index - 1]!r}"[:200]
    total = comb(2 * moves, moves)
    if len(output) != total:
        return f"listed {len(output)} paths, but a grid of side {moves + 1} has {total}"
    return None
