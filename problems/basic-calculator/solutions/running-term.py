def calculate(s: str) -> int:
    total = 0  # the sum of the finished terms
    term = 0  # the signed term still being built
    number = 0
    operator = "+"  # the operator in front of the number being read
    for i, character in enumerate(s):
        if character.isdigit():
            number = number * 10 + int(character)
        if character in "+-*/" or i == len(s) - 1:
            if operator in "+-":
                total += term
                term = number if operator == "+" else -number
            elif operator == "*":
                term *= number
            else:
                term = _truncating_divide(term, number)
            operator = character
            number = 0
    return total + term


def _truncating_divide(left: int, right: int) -> int:
    # Python's // floors; the statement truncates toward zero, and terms can be negative here.
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient
