"""Seeded inputs for evaluate-rpn: a valid postfix expression of about `n` tokens.

An expression with k numbers has k - 1 operators, so the generator uses k = (n + 1) / 2
numbers between -200 and 200 and emits 2k - 1 tokens. It simulates evaluation while it
builds: after each number it either pushes another number (probability 0.7, while numbers
remain) or emits an operator for the top two values. The operator is drawn among those whose
result stays within 10^9 in absolute value; division needs a non-zero divisor. One of `+` and
`-` always qualifies, so the build never gets stuck.

The 0.7 bias makes the pending operands grow by about 0.4 per token while numbers remain, to
about k/2, so finding the leftmost operator by rescanning from the front grows with n^2 at
every seed, while the stack stays linear.
"""

import random

MIN_TOKENS = 1
MAX_TOKENS = 10**4
NUMBER_LIMIT = 200
VALUE_LIMIT = 10**9
PUSH_PROBABILITY = 0.7
OPERATORS = ("+", "-", "*", "/")


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_TOKENS), MAX_TOKENS)
    numbers_left = (count + 1) // 2
    tokens: list[str] = []
    values: list[int] = []
    while numbers_left or len(values) > 1:
        if numbers_left and (len(values) < 2 or rng.random() < PUSH_PROBABILITY):
            number = rng.randint(-NUMBER_LIMIT, NUMBER_LIMIT)
            tokens.append(str(number))
            values.append(number)
            numbers_left -= 1
            continue
        right = values.pop()
        left = values.pop()
        results = {
            operator: result
            for operator in OPERATORS
            if (result := _apply(operator, left, right)) is not None
            and abs(result) <= VALUE_LIMIT
        }
        operator = rng.choice(sorted(results))
        tokens.append(operator)
        values.append(results[operator])
    return {"tokens": tokens}


def _apply(operator: str, left: int, right: int) -> int | None:
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if right == 0:
        return None
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient


def validate(case_input: dict) -> None:
    tokens = case_input["tokens"]
    assert MIN_TOKENS <= len(tokens) <= MAX_TOKENS, "token count out of range"
    values: list[int] = []
    for token in tokens:
        if token in OPERATORS:
            assert len(values) >= 2, "an operator lacks operands"
            right = values.pop()
            left = values.pop()
            result = _apply(token, left, right)
            assert result is not None, "division by zero"
            assert abs(result) <= 2**31 - 1, "intermediate value out of 32-bit range"
            values.append(result)
        else:
            assert -NUMBER_LIMIT <= int(token) <= NUMBER_LIMIT, "number out of range"
            values.append(int(token))
    assert len(values) == 1, "the tokens do not form one expression"
