OPERATORS = frozenset("+-*/")


def eval_rpn(tokens: list[str]) -> int:
    # Operators stay as strings; numbers are parsed once.
    items: list = [token if token in OPERATORS else int(token) for token in tokens]
    while len(items) > 1:
        # The leftmost operator always has its two operands directly in front of it.
        position = next(i for i, item in enumerate(items) if isinstance(item, str))
        operator, left, right = items[position], items[position - 2], items[position - 1]
        items[position - 2 : position + 1] = [_apply(operator, left, right)]
    return items[0]


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
