"""Seeded inputs for fast-power: large exponents with a base close enough to 1 to stay in range.

`n` is the size of the exponent: |exponent| is drawn between n / 2 and n, with a random sign.
The base has a random sign and a magnitude e^t with t uniform in [-a, a], where
a = ln(10^4) / |exponent| (capped so that |x| < 100). That keeps |x^exponent| at most about
10^4 whatever the sign of the exponent, as the constraints require. Repeated multiplication
does |exponent| steps on these inputs (its early stops never trigger), while squaring needs
about log2 |exponent|.
"""

import math
import random

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
RESULT_LIMIT = 10**4
BASE_LIMIT = 100.0
SAFETY = 0.99


def generate(rng: random.Random, n: int) -> dict:
    size = min(max(n, 1), INT_MAX)
    magnitude = rng.randint(size // 2, size)
    exponent = magnitude if rng.random() < 0.5 else -magnitude
    spread = min(math.log(RESULT_LIMIT) / max(magnitude, 1), math.log(BASE_LIMIT - 1)) * SAFETY
    base = math.exp(rng.uniform(-spread, spread))
    if rng.random() < 0.5:
        base = -base
    return {"x": base, "n": exponent}


def validate(case_input: dict) -> None:
    x, n = case_input["x"], case_input["n"]
    assert -BASE_LIMIT < x < BASE_LIMIT, "x out of range"
    assert INT_MIN <= n <= INT_MAX, "n out of range"
    assert x != 0 or n > 0, "0 to a non-positive power is undefined"
    if x != 0:
        log_result = n * math.log(abs(x))
        assert log_result <= math.log(RESULT_LIMIT) + 1e-9, "result out of range"
