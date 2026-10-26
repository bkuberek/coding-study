from itertools import combinations


def is_balanced(brackets: list[str]) -> bool:
    # depth is the height a stack of unmatched "(" would have.
    depth = 0
    for bracket in brackets:
        depth += 1 if bracket == "(" else -1
        if depth < 0:
            return False
    return depth == 0


def generate_parenthesis(n: int) -> list[str]:
    result: list[str] = []
    for opening_positions in combinations(range(2 * n), n):
        brackets = [")"] * (2 * n)
        for position in opening_positions:
            brackets[position] = "("
        if is_balanced(brackets):
            result.append("".join(brackets))
    return result
