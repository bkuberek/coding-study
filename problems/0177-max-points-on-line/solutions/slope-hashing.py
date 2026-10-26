from collections import Counter
from math import gcd


def max_points(points: list[list[int]]) -> int:
    best = 1
    for i, (x1, y1) in enumerate(points):
        directions: Counter[tuple[int, int]] = Counter()
        for x2, y2 in points[i + 1 :]:
            dx, dy = x2 - x1, y2 - y1
            divisor = gcd(dx, dy)  # never 0: the points are distinct
            dx, dy = dx // divisor, dy // divisor
            # One representative per direction: dx > 0, or dx == 0 and dy > 0.
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            directions[(dx, dy)] += 1
        if directions:
            best = max(best, max(directions.values()) + 1)  # + 1 for the anchor
    return best
