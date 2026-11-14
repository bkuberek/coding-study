"""Seeded inputs for coin-change-ways: amount n with 5 to 25 distinct coin values.

The amount is n (at most 2000). There are 5 to 25 coin values (fewer for tiny amounts),
drawn log-uniformly between 1 and the amount (or twice the number of values, if that is
larger), so small and large values mix as in a real currency. Small coins make the counts explode, so while some total up to the amount has more
than 2^31 - 1 combinations, the smallest coin is replaced by a somewhat larger value. That
keeps the constraint that every count fits in 32 bits, whatever order a solution fills its
table in, and it leaves answers anywhere from a few to about 2 * 10^9. Every table approach
does k * amount steps, linear in n for this bounded k.
"""

import math
import random

MAX_AMOUNT = 2000
MAX_COIN = 5000
MAX_COINS = 300
MIN_GENERATED_COINS = 5
MAX_GENERATED_COINS = 25
LIMIT = 2**31 - 1


def generate(rng: random.Random, n: int) -> dict:
    amount = min(max(n, 0), MAX_AMOUNT)
    count = rng.randint(min(MIN_GENERATED_COINS, amount + 1), min(MAX_GENERATED_COINS, amount + 1))
    # Tiny amounts still need room for `count` distinct values (some larger than the amount).
    upper = max(amount, 2 * count)
    values: set[int] = set()
    while len(values) < count:
        values.add(min(upper, int(math.exp(rng.uniform(0, math.log(upper + 1))))))
    coins = sorted(values)
    while _overflows(amount, coins):
        smallest = coins.pop(0)
        replacement = smallest + rng.randint(1, smallest + 1)
        while replacement in coins:
            replacement += 1
        coins = sorted([*coins, replacement])
    rng.shuffle(coins)
    return {"amount": amount, "coins": coins}


def _overflows(amount: int, coins: list[int]) -> bool:
    """True if some total up to `amount` has more than LIMIT combinations of these coins."""
    counts = [1] + [0] * amount
    for coin in coins:
        for total in range(coin, amount + 1):
            counts[total] += counts[total - coin]
            # Counts only grow as coins are added, so one excess decides.
            if counts[total] > LIMIT:
                return True
    return False


def validate(case_input: dict) -> None:
    amount, coins = case_input["amount"], case_input["coins"]
    assert 0 <= amount <= MAX_AMOUNT, "amount out of range"
    assert 1 <= len(coins) <= MAX_COINS, "number of coins out of range"
    assert all(1 <= coin <= MAX_COIN for coin in coins), "coin value out of range"
    assert len(set(coins)) == len(coins), "coin values must be distinct"
    assert not _overflows(amount, coins), "a count exceeds 32 bits"
