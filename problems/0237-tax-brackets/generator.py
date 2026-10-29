"""Seeded inputs for tax-brackets: n brackets whose limits rise by 1 to 10 units each.

Rates are uniform whole percents from 0 to 100. From 31 brackets on, which covers every
ladder size, the income falls inside the last bracket, so both approaches walk every bracket
and the unit-by-unit approach walks about 5.5n units at every seed. At oracle sizes (30 or
fewer) the income is uniform from 0 to the last limit, so it can end inside any bracket,
exactly on a limit, or be 0.
"""

import random
from itertools import accumulate, pairwise

MAX_BRACKETS = 10**5
MAX_LIMIT = 10**6
MAX_STEP = 10
MAX_PERCENT = 100
SMALL_UP_TO = 30


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_BRACKETS)
    limits = list(accumulate(rng.randint(1, MAX_STEP) for _ in range(count)))
    brackets = [[limit, rng.randint(0, MAX_PERCENT)] for limit in limits]
    # Oracle sizes: anywhere from 0 to the last limit. Ladder sizes: inside the last bracket.
    lowest = 0 if count <= SMALL_UP_TO else limits[-2] + 1
    income = rng.randint(lowest, limits[-1])
    return {"brackets": brackets, "income": income}


def validate(case_input: dict) -> None:
    brackets, income = case_input["brackets"], case_input["income"]
    assert 1 <= len(brackets) <= MAX_BRACKETS, "bracket count out of range"
    assert all(len(bracket) == 2 for bracket in brackets), "a bracket has a limit and a rate"
    limits = [bracket[0] for bracket in brackets]
    assert limits[0] >= 1, "limit out of range"
    assert limits[-1] <= MAX_LIMIT, "limit out of range"
    assert all(earlier < later for earlier, later in pairwise(limits)), (
        "limits must strictly increase"
    )
    assert all(0 <= bracket[1] <= MAX_PERCENT for bracket in brackets), "rate out of range"
    assert 0 <= income <= limits[-1], "income must be between 0 and the last limit"
