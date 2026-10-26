def calculate(s: str) -> int:
    terms: list[int] = []  # signed terms; the last one may still be multiplied or divided
    number = 0
    operator = "+"  # the operator in front of the number being read
    for i, character in enumerate(s):
        if character.isdigit():
            number = number * 10 + int(character)
        if character in "+-*/" or i == len(s) - 1:
            if operator == "+":
                terms.append(number)
            elif operator == "-":
                terms.append(-number)
            elif operator == "*":
                terms.append(terms.pop() * number)
            else:
                terms.append(_truncating_divide(terms.pop(), number))
            operator = character
            number = 0
    return sum(terms)


def _truncating_divide(left: int, right: int) -> int:
    # Python's // floors; the statement truncates toward zero, and terms can be negative here.
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient
