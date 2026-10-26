"""Seeded inputs for min-cost-tickets.

`n` is the number of travel days, clamped to 1..365. The last possible day W is drawn between
n and min(365, 2n), so the calendar grows with `n`, and the travel days are a random sorted
sample of 1..W. Prices usually grow with the pass length (each longer pass costing between one
and several times the shorter one); one input in five draws all three prices independently,
so a longer pass can be cheaper than a shorter one.
"""

import random

MIN_TRIPS = 1
MAX_DAY = 365
MAX_PRICE = 1000
INDEPENDENT_PRICES_SHARE = 0.2


def _costs(rng: random.Random) -> list[int]:
    if rng.random() < INDEPENDENT_PRICES_SHARE:
        return [rng.randint(1, MAX_PRICE) for _ in range(3)]
    day_price = rng.randint(1, 100)
    week_price = min(MAX_PRICE, rng.randint(day_price, 7 * day_price))
    month_price = min(MAX_PRICE, rng.randint(week_price, 5 * week_price))
    return [day_price, week_price, month_price]


def generate(rng: random.Random, n: int) -> dict:
    trips = min(max(n, MIN_TRIPS), MAX_DAY)
    last_day = min(MAX_DAY, trips + rng.randint(0, trips))
    days = sorted(rng.sample(range(1, last_day + 1), trips))
    return {"days": days, "costs": _costs(rng)}


def validate(case_input: dict) -> None:
    days, costs = case_input["days"], case_input["costs"]
    assert MIN_TRIPS <= len(days) <= MAX_DAY, "number of travel days out of range"
    assert all(1 <= day <= MAX_DAY for day in days), "travel day out of range"
    assert all(a < b for a, b in zip(days, days[1:])), "days must be strictly increasing"
    assert len(costs) == 3, "costs must have three prices"
    assert all(1 <= price <= MAX_PRICE for price in costs), "price out of range"
