import re

LEVELS = (("*", "/"), ("+", "-"))


def calculate(s: str) -> int:
    tokens = re.findall(r"\d+|[-+*/]", s)
    values = [int(token) for token in tokens[::2]]
    operators = tokens[1::2]  # operators[i] joins values[i] and values[i + 1]
    for level in LEVELS:
        while (position := _leftmost(operators, level)) is not None:
            result = _apply(operators[position], values[position], values[position + 1])
            values[position : position + 2] = [result]
            del operators[position]
    return values[0]


def _leftmost(operators: list[str], level: tuple[str, ...]) -> int | None:
    """Position of the first operator of this level; each `index` call scans from the front in C."""
    positions = [operators.index(symbol) for symbol in level if symbol in operators]
    return min(positions) if positions else None


def _apply(operator: str, left: int, right: int) -> int:
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    # Python's // floors; the statement truncates toward zero.
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient
