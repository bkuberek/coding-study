"""Seeded inputs for gas-station with a unique answer.

`n` is the number of stations, clamped to 1..10^5. Solvable inputs are built from the start
station `s` outwards: the fuel left after each of the first n - 1 legs stays strictly above a
small final value T >= 0, and the last leg brings it down to exactly T. Every other start then
fails (it begins with more fuel already spent than the trip from `s` ever recovers), so the
answer is unique, as the constraints promise. The trip is rotated so that `s` is a random index.

Shapes: rising (the fuel creeps up by small steps, so a trip from any other station survives
until the very last leg: simulating every start is quadratic), walk (a random walk of the fuel
level), and impossible (random stations whose total cost exceeds the total fuel).

From WORST_FROM stations on (the bench ladder), every input is rising with the answer at the
last station, so simulating every start does about n^2 / 2 steps on every seed: it tries all
other starts first and each of them runs until the last leg. With a random answer index the
simulation would stop after a share of the starts that varies from seed to seed.
"""

import random

MIN_STATIONS = 1
MAX_STATIONS = 10**5
MAX_AMOUNT = 10**4
MAX_FINAL = 50
WALK_STEP = 300
WORST_FROM = 100


def _station(rng: random.Random, surplus: int) -> tuple[int, int]:
    """A (gas, cost) pair with gas - cost == surplus, both within 0..MAX_AMOUNT."""
    if surplus >= 0:
        cost = rng.randint(0, MAX_AMOUNT - surplus)
        return cost + surplus, cost
    gas = rng.randint(0, MAX_AMOUNT + surplus)
    return gas, gas - surplus


def _fuel_levels(rng: random.Random, stations: int, final: int, rising: bool) -> list[int]:
    """Fuel after legs 1..n - 1, each in final + 1 .. MAX_AMOUNT, so every leg changes the
    fuel by at most MAX_AMOUNT."""
    low, high = final + 1, MAX_AMOUNT
    step_cap = max(0, (MAX_AMOUNT - 1) // max(1, stations))
    level = rng.randint(low, low + step_cap) if rising else rng.randint(low, high)
    levels = []
    for _ in range(stations - 1):
        levels.append(level)
        if rising:
            level = min(high, level + rng.randint(0, step_cap))
        else:
            level = min(high, max(low, level + rng.randint(-WALK_STEP, WALK_STEP)))
    return levels


def _solvable(
    rng: random.Random, stations: int, rising: bool, start: int | None = None
) -> tuple[list[int], list[int]]:
    """A trip with a unique answer: `start`, or a random station when it is None."""
    final = rng.randint(0, MAX_FINAL)
    levels = [0] + _fuel_levels(rng, stations, final, rising) + [final]
    surpluses = [after - before for before, after in zip(levels, levels[1:])]
    pairs = [_station(rng, surplus) for surplus in surpluses]
    if start is None:
        start = rng.randrange(stations)
    pairs = pairs[stations - start :] + pairs[: stations - start]
    return [g for g, _ in pairs], [c for _, c in pairs]


def _impossible(rng: random.Random, stations: int) -> tuple[list[int], list[int]]:
    gas = [rng.randint(0, MAX_AMOUNT) for _ in range(stations)]
    cost = [rng.randint(0, MAX_AMOUNT) for _ in range(stations)]
    while sum(gas) >= sum(cost):
        station = rng.randrange(stations)
        if cost[station] < MAX_AMOUNT:
            cost[station] = rng.randint(cost[station] + 1, MAX_AMOUNT)
        else:
            gas[station] = rng.randint(0, gas[station] - 1) if gas[station] > 0 else 0
    return gas, cost


def generate(rng: random.Random, n: int) -> dict:
    stations = min(max(n, MIN_STATIONS), MAX_STATIONS)
    if stations >= WORST_FROM:
        gas, cost = _solvable(rng, stations, rising=True, start=stations - 1)
        return {"gas": gas, "cost": cost}
    shape = rng.choice(("rising", "walk", "impossible"))
    if shape == "impossible":
        gas, cost = _impossible(rng, stations)
    else:
        gas, cost = _solvable(rng, stations, rising=shape == "rising")
    return {"gas": gas, "cost": cost}


def _valid_starts(gas: list[int], cost: list[int]) -> int:
    n = len(gas)
    balance = [0]
    for g, c in zip(gas, cost):
        balance.append(balance[-1] + g - c)
    total = balance[n]
    lowest_after = [0] * (n + 1)  # min of balance[k] for k in i + 1 .. n
    lowest_after[n] = balance[n]
    for i in range(n - 1, -1, -1):
        lowest_after[i] = min(balance[i + 1], lowest_after[i + 1])
    count = 0
    lowest_before = None  # min of balance[k] for k in 1 .. start
    for start in range(n):
        ahead_ok = lowest_after[start] >= balance[start]
        wrap_ok = lowest_before is None or total + lowest_before >= balance[start]
        count += ahead_ok and wrap_ok
        current = balance[start + 1]
        lowest_before = current if lowest_before is None else min(lowest_before, current)
    return count


def validate(case_input: dict) -> None:
    gas, cost = case_input["gas"], case_input["cost"]
    assert MIN_STATIONS <= len(gas) <= MAX_STATIONS, "number of stations out of range"
    assert len(gas) == len(cost), "gas and cost differ in length"
    assert all(0 <= value <= MAX_AMOUNT for value in gas + cost), "amount out of range"
    if sum(gas) >= sum(cost):
        assert _valid_starts(gas, cost) == 1, "the valid start is not unique"
