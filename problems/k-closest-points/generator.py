"""Seeded inputs for k-closest-points with a unique answer.

Coordinates come from a tiny box (|x|, |y| <= 3) a fifth of the time, which produces repeated
points and many equal distances, and from the full range otherwise. `k` is then drawn
uniformly from the ranks where the k-th smallest squared distance is strictly smaller than
the next one (k = n always qualifies), so the set of k closest points is unique, as the
constraints promise.
"""

import random

MIN_POINTS = 1
MAX_POINTS = 10**5
COORD_LIMIT = 10**4
TINY_LIMIT = 3


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, MIN_POINTS), MAX_POINTS)
    limit = TINY_LIMIT if rng.random() < 0.2 else COORD_LIMIT
    points = [[rng.randint(-limit, limit), rng.randint(-limit, limit)] for _ in range(count)]
    distances = sorted(x * x + y * y for x, y in points)
    ranks = [k for k in range(1, count + 1) if k == count or distances[k - 1] < distances[k]]
    return {"points": points, "k": rng.choice(ranks)}


def validate(case_input: dict) -> None:
    points, k = case_input["points"], case_input["k"]
    assert MIN_POINTS <= len(points) <= MAX_POINTS, "point count out of range"
    assert all(len(point) == 2 for point in points), "a point has two coordinates"
    assert all(abs(value) <= COORD_LIMIT for point in points for value in point), "coordinate out of range"
    assert 1 <= k <= len(points), "k out of range"
    distances = sorted(x * x + y * y for x, y in points)
    assert k == len(points) or distances[k - 1] < distances[k], "the answer is not unique"
