"""Seeded inputs for coin-change.

`n` is the amount, clamped to 0..2000. Between 1 and 12 distinct coin values are drawn, mostly
up to about the amount, with an occasional value far above it (which can never be used). One
input in five uses only even coins, so an odd amount has no answer; otherwise whether the
amount can be paid depends on the draw.
"""

import random

MAX_COINS = 12
MAX_AMOUNT = 2000
MAX_COIN = 2**31 - 1
EVEN_ONLY_SHARE = 0.2
HUGE_COIN_SHARE = 0.1


def generate(rng: random.Random, n: int) -> dict:
    amount = min(max(n, 0), MAX_AMOUNT)
    count = rng.randint(1, MAX_COINS)
    even_only = rng.random() < EVEN_ONLY_SHARE
    ceiling = max(amount, 2) + 10
    coins: set[int] = set()
    while len(coins) < count:
        if rng.random() < HUGE_COIN_SHARE:
            coin = rng.randint(MAX_AMOUNT + 1, MAX_COIN)
        else:
            coin = rng.randint(1, ceiling)
        if even_only and coin % 2 == 1:
            coin = coin + 1 if coin < MAX_COIN else coin - 1
        coins.add(coin)
    values = sorted(coins)
    rng.shuffle(values)
    return {"coins": values, "amount": amount}


def validate(case_input: dict) -> None:
    coins, amount = case_input["coins"], case_input["amount"]
    assert 1 <= len(coins) <= MAX_COINS, "coin count out of range"
    assert len(set(coins)) == len(coins), "coin values are not distinct"
    assert all(1 <= coin <= MAX_COIN for coin in coins), "coin value out of range"
    assert 0 <= amount <= MAX_AMOUNT, "amount out of range"
