"""Seeded point sets for min-cost-connect-points.

`n` is the number of points (capped at 1000). Points are distinct, either spread uniformly over
a square whose side is drawn per input (from 10 to 2·10^6, so small squares produce many tied
distances), or gathered into a few clusters far apart, where the expensive cables are the
ones between clusters. All coordinates stay within -10^6..10^6.
"""

import random

MAX_POINTS = 1000
LIMIT = 10**6


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_POINTS)
    half = rng.choice([5, 50, 1000, LIMIT])
    while (2 * half + 1) ** 2 < count:
        half *= 2
    half = min(half, LIMIT)
    clusters = None if rng.random() < 0.6 else [
        (rng.randint(-LIMIT, LIMIT), rng.randint(-LIMIT, LIMIT)) for _ in range(rng.randint(2, 5))
    ]
    spread = max(10, half // 20)
    seen: set[tuple[int, int]] = set()
    points: list[list[int]] = []
    while len(points) < count:
        if clusters is None:
            x, y = rng.randint(-half, half), rng.randint(-half, half)
        else:
            cx, cy = rng.choice(clusters)
            x = min(LIMIT, max(-LIMIT, cx + rng.randint(-spread, spread)))
            y = min(LIMIT, max(-LIMIT, cy + rng.randint(-spread, spread)))
        if (x, y) not in seen:
            seen.add((x, y))
            points.append([x, y])
    return {"points": points}


def validate(case_input: dict) -> None:
    points = case_input["points"]
    assert 1 <= len(points) <= MAX_POINTS, "point count out of range"
    assert all(len(point) == 2 and all(-LIMIT <= c <= LIMIT for c in point) for point in points), "bad point"
    assert len({tuple(point) for point in points}) == len(points), "points repeat"
