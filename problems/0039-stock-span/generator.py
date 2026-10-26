"""Seeded call sequences for stock-span: a rally followed by noisy trading.

`n` is the number of `span` calls after the constructor. The first third to two thirds of
the days form a rally: prices that never fall from one day to the next (they repeat or
rise), drawn from a random band of the range. The remaining days are uniform noise over the
whole range. During the rally every walk back reaches the first day of the series, so
walking back on each call reads at least (rally length)^2 / 2 prices, about n^2 / 18 to
2n^2 / 9. The stack keeps a single entry through the whole rally, because each new price
absorbs the one before it.
"""

import random

MIN_CALLS = 1
MAX_CALLS = 10**5
MIN_PRICE = 1
MAX_PRICE = 10**5


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, MIN_CALLS), MAX_CALLS)
    rally_length = rng.randint(calls // 3, (2 * calls) // 3)
    low = rng.randint(MIN_PRICE, MAX_PRICE)
    high = rng.randint(low, MAX_PRICE)
    rally = sorted(rng.randint(low, high) for _ in range(rally_length))
    noise = [rng.randint(MIN_PRICE, MAX_PRICE) for _ in range(calls - rally_length)]
    prices = rally + noise
    return {"ops": ["StockSpanner"] + ["span"] * calls, "args": [[]] + [[price] for price in prices]}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "StockSpanner" and args[0] == [], "the first op must be the constructor"
    assert MIN_CALLS <= len(ops) - 1 <= MAX_CALLS, "number of calls out of range"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert op == "span" and len(arguments) == 1, f"bad call {op}{arguments}"
        assert MIN_PRICE <= arguments[0] <= MAX_PRICE, "price out of range"
