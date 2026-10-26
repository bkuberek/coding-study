"""Seeded inputs for car-fleet: distinct starting miles with speeds that create many fleets.

The destination lies between n and 10^6 miles away; with fewer than 200 cars it is close (at
most max(10n, 20) miles), so equal arrival times, and therefore merges exactly at the
destination, are common. Half of the seeds draw every speed uniformly, which leaves only a few fleets (about
ln n). The other half give cars closer to the destination higher speeds, with noise, so many
cars arrive on their own and the stack grows large.

The brute force always compares every pair of cars (n^2), whatever the fleets look like.
"""

import random

MIN_CARS = 1
MAX_CARS = 10**5
MAX_TARGET = 10**6
MAX_SPEED = 1000
FEW_CARS = 200
SMALL_TARGET_FACTOR = 10
MIN_SMALL_TARGET = 20


def generate(rng: random.Random, n: int) -> dict:
    cars = min(max(n, MIN_CARS), MAX_CARS)
    if cars >= FEW_CARS:
        target_cap = MAX_TARGET
    else:
        target_cap = max(SMALL_TARGET_FACTOR * cars, MIN_SMALL_TARGET)
    target = rng.randint(cars, target_cap)
    position = rng.sample(range(target), cars)
    if rng.random() < 0.5:
        speed = [rng.randint(1, MAX_SPEED) for _ in range(cars)]
    else:
        speed = [_rising_speed(rng, mile, target) for mile in position]
    return {"target": target, "position": position, "speed": speed}


def _rising_speed(rng: random.Random, mile: int, target: int) -> int:
    base = 1 + (MAX_SPEED - 1) * mile // target
    return min(MAX_SPEED, max(1, base + rng.randint(-20, 20)))


def validate(case_input: dict) -> None:
    target, position, speed = case_input["target"], case_input["position"], case_input["speed"]
    assert MIN_CARS <= len(position) <= MAX_CARS, "number of cars out of range"
    assert len(speed) == len(position), "position and speed differ in length"
    assert 1 <= target <= MAX_TARGET, "target out of range"
    assert all(0 <= mile < target for mile in position), "position out of range"
    assert len(set(position)) == len(position), "positions must be distinct"
    assert all(1 <= value <= MAX_SPEED for value in speed), "speed out of range"
