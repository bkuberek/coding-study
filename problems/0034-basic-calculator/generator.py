"""Seeded inputs for basic-calculator: an expression with `n` operands.

The expression is a sum of terms. Each term is a chain of 1 to 3 operands between 0 and 1000
joined by `*` (when the product stays within 10^6) or `/` (with a divisor of at least 1), so
every term stays between 0 and 10^6. Terms are joined by `+` or `-`, choosing the sign that
keeps the running total within 10^9 in absolute value when one of them would leave it. Every
partial sum then fits in 32 bits, from the left or from the right. Tokens are separated by 0
to 2 spaces, and the expression may start or end with a space.

About half of the operators are `*` or `/`, so reducing the leftmost one by rescanning from
the front grows with n^2 at every seed, while the one-pass approaches stay linear.
"""

import random

MIN_OPERANDS = 1
MAX_OPERANDS = 5 * 10**4
OPERAND_LIMIT = 1000
TERM_LIMIT = 10**6
TOTAL_LIMIT = 10**9
MAX_FACTORS = 3
MAX_LENGTH = 3 * 10**5
ALLOWED = set("0123456789 +-*/")


def generate(rng: random.Random, n: int) -> dict:
    operands = min(max(n, MIN_OPERANDS), MAX_OPERANDS)
    tokens: list[str] = []
    total = 0
    while operands:
        factors = min(rng.randint(1, MAX_FACTORS), operands)
        operands -= factors
        term_tokens, term = _term(rng, factors)
        if tokens:
            if total + term > TOTAL_LIMIT:
                sign = "-"
            elif total - term < -TOTAL_LIMIT:
                sign = "+"
            else:
                sign = rng.choice("+-")
            tokens.append(sign)
            total += term if sign == "+" else -term
        else:
            total = term
        tokens.extend(term_tokens)
    gaps = [" " * rng.randint(0, 2) for _ in range(len(tokens) + 1)]
    return {"s": "".join(gap + token for gap, token in zip(gaps, tokens)) + gaps[-1]}


def _term(rng: random.Random, factors: int) -> tuple[list[str], int]:
    value = rng.randint(0, OPERAND_LIMIT)
    tokens = [str(value)]
    for _ in range(factors - 1):
        operand = rng.randint(1, OPERAND_LIMIT)
        if value * operand <= TERM_LIMIT and rng.random() < 0.5:
            tokens += ["*", str(operand)]
            value *= operand
        else:
            tokens += ["/", str(operand)]
            value //= operand
    return tokens, value


def validate(case_input: dict) -> None:
    s = case_input["s"]
    assert 1 <= len(s) <= MAX_LENGTH, "length out of range"
    assert set(s) <= ALLOWED, "unexpected character"
    assert s.strip(), "the expression is empty"
