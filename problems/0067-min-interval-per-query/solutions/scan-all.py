def min_interval(intervals: list[list[int]], queries: list[int]) -> list[int]:
    return [
        min((right - left + 1 for left, right in intervals if left <= query <= right), default=-1)
        for query in queries
    ]
