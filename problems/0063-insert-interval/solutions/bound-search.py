from bisect import bisect_left, bisect_right


def insert(intervals: list[list[int]], new_interval: list[int]) -> list[list[int]]:
    start, end = new_interval
    # Separate sorted intervals have increasing starts and increasing ends.
    first = bisect_left([interval[1] for interval in intervals], start)
    after = bisect_right([interval[0] for interval in intervals], end)
    if first < after:
        start = min(start, intervals[first][0])
        end = max(end, intervals[after - 1][1])
    return intervals[:first] + [[start, end]] + intervals[after:]
