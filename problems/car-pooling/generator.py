"""Seeded inputs for car-pooling.

`n` is the number of trips. Locations run from 0 to L = 4n (at least 4, at most 10^5), so the
difference array grows with n. Each trip starts at a uniform location and runs for up to a
quarter of the road, so trips overlap heavily. The capacity is the true peak load (answer
`true`) or one less (answer `false`, decided at the busiest point); one input in five uses a
random capacity instead. None of the references stops early, so every input costs the same.
"""

import random

MAX_TRIPS = 10**4
MAX_LOCATION = 10**5
MAX_PASSENGERS = 100
MAX_CAPACITY = 10**6
LOCATIONS_PER_TRIP = 4
SPAN_SHARE = 4
RANDOM_CAPACITY_SHARE = 0.2


def _peak_load(trips: list[list[int]], last: int) -> int:
    change = [0] * (last + 1)
    for passengers, start, end in trips:
        change[start] += passengers
        change[end] -= passengers
    load = peak = 0
    for delta in change:
        load += delta
        peak = max(peak, load)
    return peak


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_TRIPS)
    last = min(max(LOCATIONS_PER_TRIP * count, 4), MAX_LOCATION)
    span = max(last // SPAN_SHARE, 1)
    trips = []
    for _ in range(count):
        start = rng.randrange(last)
        end = rng.randint(start + 1, min(last, start + span))
        trips.append([rng.randint(1, MAX_PASSENGERS), start, end])
    peak = _peak_load(trips, last)
    if rng.random() < RANDOM_CAPACITY_SHARE:
        capacity = rng.randint(1, min(2 * peak, MAX_CAPACITY))
    else:
        capacity = max(peak - rng.randint(0, 1), 1)
    return {"trips": trips, "capacity": capacity}


def validate(case_input: dict) -> None:
    trips, capacity = case_input["trips"], case_input["capacity"]
    assert 1 <= len(trips) <= MAX_TRIPS, "trip count out of range"
    for trip in trips:
        assert len(trip) == 3, "a trip has three fields"
        passengers, start, end = trip
        assert 1 <= passengers <= MAX_PASSENGERS, "passengers out of range"
        assert 0 <= start < end <= MAX_LOCATION, "locations out of range"
    assert 1 <= capacity <= MAX_CAPACITY, "capacity out of range"
