"""Seeded inputs for price-after-rebate: a rising run of prices followed by dearer ones.

The shelf starts with a strictly rising run covering a third to two thirds of the items,
drawn without repeats from 1..n. The remaining items are uniform between n / 2 and 2n, so
repeated prices are common at every size. Every run item that costs less than n / 2 finds no
item at least as cheap anywhere to its right, so scanning right from it reads the whole rest
of the shelf: about 3n^2 / 16 reads in total at n items. The stack holds the whole run at its
peak and still touches each item at most twice.
"""

import random

MIN_LENGTH = 1
MAX_LENGTH = 10**5
LOW = 1
HIGH = 10**6


def generate(rng: random.Random, n: int) -> dict:
    length = min(max(n, MIN_LENGTH), MAX_LENGTH)
    run_length = rng.randint(length // 3, (2 * length) // 3)
    run = sorted(rng.sample(range(LOW, length + 1), run_length))
    rest = [rng.randint(max(LOW, length // 2), 2 * length) for _ in range(length - run_length)]
    return {"prices": run + rest}


def validate(case_input: dict) -> None:
    prices = case_input["prices"]
    assert MIN_LENGTH <= len(prices) <= MAX_LENGTH, "length out of range"
    assert all(LOW <= price <= HIGH for price in prices), "price out of range"
