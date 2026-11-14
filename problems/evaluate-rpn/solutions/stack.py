from collections.abc import Callable


def _divide(left: int, right: int) -> int:
    # Python's // floors; the statement truncates toward zero.
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient


APPLY: dict[str, Callable[[int, int], int]] = {
    "+": lambda left, right: left + right,
    "-": lambda left, right: left - right,
    "*": lambda left, right: left * right,
    "/": _divide,
}


def eval_rpn(tokens: list[str]) -> int:
    operands: list[int] = []
    for token in tokens:
        apply = APPLY.get(token)
        if apply is None:
            operands.append(int(token))
        else:
            right = operands.pop()
            left = operands.pop()
            operands.append(apply(left, right))
    return operands[0]
