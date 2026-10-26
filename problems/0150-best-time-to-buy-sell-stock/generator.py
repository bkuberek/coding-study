"""Seeded inputs for best-time-to-buy-sell-stock.

`n` is the number of days, clamped to 1..10^5, with prices in 0..10^4. Each input picks one
shape: uniform random prices, a random walk (long trends, so the best buy is often far from
the best sell), or a downward walk with small rebounds (the answer is small or 0).
"""

import random

MIN_DAYS = 1
MAX_DAYS = 10**5
MAX_PRICE = 10**4
WALK_STEP = 100


def generate(rng: random.Random, n: int) -> dict:
    days = min(max(n, MIN_DAYS), MAX_DAYS)
    shape = rng.choice(("uniform", "walk", "falling"))
    if shape == "uniform":
        return {"prices": [rng.randint(0, MAX_PRICE) for _ in range(days)]}
    price = rng.randint(0, MAX_PRICE) if shape == "walk" else MAX_PRICE
    low, high = (-WALK_STEP, WALK_STEP) if shape == "walk" else (-WALK_STEP, WALK_STEP // 4)
    prices = []
    for _ in range(days):
        prices.append(price)
        price = min(MAX_PRICE, max(0, price + rng.randint(low, high)))
    return {"prices": prices}


def validate(case_input: dict) -> None:
    prices = case_input["prices"]
    assert MIN_DAYS <= len(prices) <= MAX_DAYS, "length out of range"
    assert all(0 <= price <= MAX_PRICE for price in prices), "price out of range"
