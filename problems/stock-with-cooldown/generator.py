"""Seeded inputs for stock-with-cooldown.

`n` is the number of days, clamped to 1..2000, with prices in 0..1000. Each input picks one
shape: uniform random prices (many short rises, where the cooldown often blocks a back-to-back
trade), a random walk with small steps (long trends), or a sawtooth that rises and falls every
few days (where choosing which rises to skip matters most).
"""

import random

MIN_DAYS = 1
MAX_DAYS = 2000
MAX_PRICE = 1000
WALK_STEP = 30


def generate(rng: random.Random, n: int) -> dict:
    days = min(max(n, MIN_DAYS), MAX_DAYS)
    shape = rng.choice(("uniform", "walk", "sawtooth"))
    if shape == "uniform":
        prices = [rng.randint(0, MAX_PRICE) for _ in range(days)]
    elif shape == "walk":
        price = rng.randint(0, MAX_PRICE)
        prices = []
        for _ in range(days):
            prices.append(price)
            price = min(MAX_PRICE, max(0, price + rng.randint(-WALK_STEP, WALK_STEP)))
    else:
        period = rng.randint(2, 5)
        prices = [
            min(MAX_PRICE, (day % period) * rng.randint(50, 200) + rng.randint(0, 50))
            for day in range(days)
        ]
    return {"prices": prices}


def validate(case_input: dict) -> None:
    prices = case_input["prices"]
    assert MIN_DAYS <= len(prices) <= MAX_DAYS, "length out of range"
    assert all(0 <= price <= MAX_PRICE for price in prices), "price out of range"
