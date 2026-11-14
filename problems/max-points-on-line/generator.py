"""Seeded inputs for max-points-on-line: distinct points, many of them on a few shared lines.

`n` is the number of points. Up to four lines are chosen, each through a random point with a
small random direction (vertical and horizontal ones included); about half of the points are
placed on those lines at random steps, the rest uniformly in the square. Duplicates are
skipped, so all points are distinct. The brute force checks every point against the line of
every pair, n^3 / 2 tests; slope hashing does n^2 / 2 gcd reductions.
"""

import random

MAX_POINTS = 300
COORD_LIMIT = 10**4
MAX_LINES = 4
DIRECTION_LIMIT = 5


def _on_line(rng: random.Random) -> tuple[int, int, int, int]:
    x0 = rng.randint(-COORD_LIMIT // 2, COORD_LIMIT // 2)
    y0 = rng.randint(-COORD_LIMIT // 2, COORD_LIMIT // 2)
    dx = rng.randint(-DIRECTION_LIMIT, DIRECTION_LIMIT)
    dy = rng.randint(-DIRECTION_LIMIT, DIRECTION_LIMIT)
    if dx == 0 and dy == 0:
        dx = 1
    return x0, y0, dx, dy


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_POINTS)
    lines = [_on_line(rng) for _ in range(rng.randint(1, MAX_LINES))]
    seen: set[tuple[int, int]] = set()
    points: list[list[int]] = []
    while len(points) < count:
        if rng.random() < 0.5:
            x0, y0, dx, dy = rng.choice(lines)
            step = rng.randint(-COORD_LIMIT // 10, COORD_LIMIT // 10)
            x, y = x0 + step * dx, y0 + step * dy
        else:
            x, y = rng.randint(-COORD_LIMIT, COORD_LIMIT), rng.randint(-COORD_LIMIT, COORD_LIMIT)
        if abs(x) <= COORD_LIMIT and abs(y) <= COORD_LIMIT and (x, y) not in seen:
            seen.add((x, y))
            points.append([x, y])
    return {"points": points}


def validate(case_input: dict) -> None:
    points = case_input["points"]
    assert 1 <= len(points) <= MAX_POINTS, "point count out of range"
    assert all(len(p) == 2 and all(abs(v) <= COORD_LIMIT for v in p) for p in points), "bad point"
    assert len({tuple(p) for p in points}) == len(points), "points must be distinct"
