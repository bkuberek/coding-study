from bisect import bisect_left


def min_interval(intervals: list[list[int]], queries: list[int]) -> list[int]:
    points = sorted(set(queries))
    size_at = [-1] * len(points)
    # next_open[k]: a link toward the first point at or after k without an answer yet;
    # len(points) is a sentinel meaning "none left".
    next_open = list(range(len(points) + 1))

    def first_open(k: int) -> int:
        root = k
        while next_open[root] != root:
            root = next_open[root]
        while next_open[k] != root:
            next_open[k], k = root, next_open[k]
        return root

    for left, right in sorted(intervals, key=lambda interval: interval[1] - interval[0]):
        k = first_open(bisect_left(points, left))
        while k < len(points) and points[k] <= right:
            size_at[k] = right - left + 1
            next_open[k] = k + 1
            k = first_open(k + 1)
    position = {point: k for k, point in enumerate(points)}
    return [size_at[position[query]] for query in queries]
