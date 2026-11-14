"""Seeded inputs for maximize-capital: `n` projects and a budget of k picks.

Required capital is spread over about what k average picks would earn, so projects unlock
gradually as capital grows, and a scan of all projects in every round costs O(k n).

Below 100 projects, which covers the oracle's inputs, `k` is uniform between 1 and n / 10 (at
least 1) and the starting capital is small, except that a tenth of the inputs start rich
enough to afford everything and a tenth start too poor to afford anything.

From 100 projects on, the sizes the ladder times, `k` is n / 10 and the starting capital is
between half and all of one maximum profit, enough to afford 10 to 20 projects at once. Every
round then finds an affordable project, so the scan runs all k = n / 10 rounds at every seed
and its O(k n) work is quadratic in n, instead of depending on a k drawn per seed or stopping
in the first round because nothing is affordable.

Final capital stays below 2^31 because w <= 10^9 and each pick adds at most 10^4.
"""

import random

MIN_PROJECTS = 1
MAX_PROJECTS = 10**5
MAX_PROFIT = 10**4
MAX_CAPITAL = 10**9
PICKS_PER_PROJECT = 10
UNIFORM_FROM = 100


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_PROJECTS), MAX_PROJECTS)
    uniform = count >= UNIFORM_FROM
    most_picks = max(1, count // PICKS_PER_PROJECT)
    k = most_picks if uniform else rng.randint(1, most_picks)
    profits = [rng.randint(0, MAX_PROFIT) for _ in range(count)]
    spread = min(MAX_CAPITAL, k * MAX_PROFIT // 2 + 1)
    capital = [rng.randint(0, spread) for _ in range(count)]
    if uniform:
        w = rng.randint(MAX_PROFIT // 2, MAX_PROFIT)
        return {"k": k, "w": w, "profits": profits, "capital": capital}
    roll = rng.random()
    if roll < 0.1:
        w = MAX_CAPITAL
    elif roll < 0.2:
        w = 0
        capital = [max(1, value) for value in capital]
    else:
        w = rng.randint(0, MAX_PROFIT)
    return {"k": k, "w": w, "profits": profits, "capital": capital}


def validate(case_input: dict) -> None:
    k, w = case_input["k"], case_input["w"]
    profits, capital = case_input["profits"], case_input["capital"]
    assert MIN_PROJECTS <= len(profits) <= MAX_PROJECTS, "project count out of range"
    assert len(capital) == len(profits), "one capital requirement per project"
    assert 1 <= k <= MAX_PROJECTS, "k out of range"
    assert 0 <= w <= MAX_CAPITAL, "w out of range"
    assert all(0 <= value <= MAX_PROFIT for value in profits), "profit out of range"
    assert all(0 <= value <= MAX_CAPITAL for value in capital), "capital out of range"
