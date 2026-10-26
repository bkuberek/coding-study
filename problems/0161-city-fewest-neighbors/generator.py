"""Seeded road networks for city-fewest-neighbors.

`n` is the number of cities (2 to 100). Roads form a random spanning tree (each city linked
to one of the last few cities, so long chains appear) plus extra random roads, about 3n roads
in total and never more than n·(n - 1)/2; on some inputs a few cities are left without roads.
Road lengths are 1 to 10^4 on a random scale, and the threshold is drawn around a typical
road length, so the reachable counts vary between cities and ties are common.
"""

import random

MAX_CITIES = 100
MAX_WEIGHT = 10**4
RECENT = 4


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 2), MAX_CITIES)
    scale = rng.choice([10, 100, 1000, MAX_WEIGHT])
    roads: dict[tuple[int, int], int] = {}
    linked = count if rng.random() < 0.8 else rng.randint(2, count)
    for city in range(1, linked):
        other = rng.randint(max(0, city - RECENT), city - 1)
        roads[(other, city)] = rng.randint(1, scale)
    target = min(3 * count, count * (count - 1) // 2)
    attempts = 0
    while len(roads) < target and attempts < 20 * target:
        attempts += 1
        a, b = sorted(rng.sample(range(count), 2))
        if (a, b) not in roads:
            roads[(a, b)] = rng.randint(1, scale)
    if not roads:
        roads[(0, 1)] = rng.randint(1, scale)
    edges = [[a, b, w] for (a, b), w in roads.items()]
    rng.shuffle(edges)
    threshold = min(MAX_WEIGHT, max(1, int(scale * rng.uniform(0.2, 2.5))))
    return {"n": count, "edges": edges, "distanceThreshold": threshold}


def validate(case_input: dict) -> None:
    n, edges, threshold = case_input["n"], case_input["edges"], case_input["distanceThreshold"]
    assert 2 <= n <= MAX_CITIES, "city count out of range"
    assert 1 <= len(edges) <= n * (n - 1) // 2, "road count out of range"
    pairs = set()
    for a, b, w in edges:
        assert 0 <= a < b < n, "bad road endpoints"
        assert 1 <= w <= MAX_WEIGHT, "road length out of range"
        pairs.add((a, b))
    assert len(pairs) == len(edges), "a road appears twice"
    assert 1 <= threshold <= MAX_WEIGHT, "threshold out of range"
