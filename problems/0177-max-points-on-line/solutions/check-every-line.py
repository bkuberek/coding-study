def max_points(points: list[list[int]]) -> int:
    if len(points) <= 2:
        return len(points)
    best = 2
    for i, (x1, y1) in enumerate(points):
        for x2, y2 in points[i + 1 :]:
            dx, dy = x2 - x1, y2 - y1
            # (x, y) is on the line through both points when the cross product is zero.
            on_line = sum(1 for x, y in points if dy * (x - x1) == dx * (y - y1))
            best = max(best, on_line)
    return best
