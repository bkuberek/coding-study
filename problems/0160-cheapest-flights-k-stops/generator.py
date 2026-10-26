"""Seeded flight networks for cheapest-flights-k-stops.

`n` is the number of flights (capped at 10^4); there are about n / 10 cities (at least 2, at
most 1000, and never more pairs than the cities allow). Flights are random distinct pairs with
prices from 1 to 10^4; one random route from `src` to `dst` of up to 12 legs is always added
with cheap prices, so that cheaper trips with more stops compete with expensive trips with
fewer. `k` is between 0 and 30 (and below n), so some inputs cannot afford the cheap route
and some have no trip at all.

From UNIFORM_FROM flights on (the bench ladder), every input has one shape instead: the cheap
route has the full 12 legs (fewer only when there are fewer cities), each priced 1, and
k = LADDER_K. Round r of Bellman-Ford then lowers the price of the r-th city on the cheap
route to r, far below any trip of random flights, so all k + 1 rounds run on every seed; a
random k, or a route that settles early, would stop the rounds after a number that varies
from seed to seed.
"""

import random

MAX_FLIGHTS = 10**4
MAX_CITIES = 1000
MAX_PRICE = 10**4
MAX_K = 30
MAX_STOPOVERS = 11
UNIFORM_FROM = 100
LADDER_K = 8


def generate(rng: random.Random, n: int) -> dict:
    wanted = min(max(n, 1), MAX_FLIGHTS)
    cities = min(MAX_CITIES, max(2, wanted // 10))
    capacity = cities * (cities - 1)
    src, dst = rng.sample(range(cities), 2)
    flights: dict[tuple[int, int], int] = {}
    uniform = wanted >= UNIFORM_FROM
    stopovers = MAX_STOPOVERS if uniform else rng.randint(0, MAX_STOPOVERS)
    others = [c for c in range(cities) if c not in (src, dst)]
    route = [src, *rng.sample(others, min(cities - 2, stopovers)), dst]
    for a, b in zip(route, route[1:]):
        flights[(a, b)] = 1 if uniform else rng.randint(1, MAX_PRICE // 20)
    target = min(wanted, capacity)
    while len(flights) < target:
        a, b = rng.randrange(cities), rng.randrange(cities)
        if a != b and (a, b) not in flights:
            flights[(a, b)] = rng.randint(1, MAX_PRICE)
    listed = [[a, b, price] for (a, b), price in flights.items()]
    rng.shuffle(listed)
    k = LADDER_K if uniform else rng.randint(0, min(MAX_K, cities - 1))
    return {"n": cities, "flights": listed, "src": src, "dst": dst, "k": k}


def validate(case_input: dict) -> None:
    n, flights = case_input["n"], case_input["flights"]
    src, dst, k = case_input["src"], case_input["dst"], case_input["k"]
    assert 1 <= n <= MAX_CITIES, "city count out of range"
    assert len(flights) <= MAX_FLIGHTS, "too many flights"
    pairs = set()
    for a, b, price in flights:
        assert 0 <= a < n and 0 <= b < n and a != b, "bad flight endpoints"
        assert 1 <= price <= MAX_PRICE, "price out of range"
        pairs.add((a, b))
    assert len(pairs) == len(flights), "a flight appears twice"
    assert 0 <= src < n and 0 <= dst < n and src != dst, "bad src or dst"
    assert 0 <= k < n, "k out of range"
