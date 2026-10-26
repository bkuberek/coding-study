import heapq


def min_interval(intervals: list[list[int]], queries: list[int]) -> list[int]:
    by_left = sorted(intervals)
    answer = [-1] * len(queries)
    # Entries are (size, right) of intervals that start at or before the current query.
    candidates: list[tuple[int, int]] = []
    added = 0
    for index in sorted(range(len(queries)), key=queries.__getitem__):
        query = queries[index]
        while added < len(by_left) and by_left[added][0] <= query:
            left, right = by_left[added]
            heapq.heappush(candidates, (right - left + 1, right))
            added += 1
        # An interval that ends before this query also ends before every later one.
        while candidates and candidates[0][1] < query:
            heapq.heappop(candidates)
        if candidates:
            answer[index] = candidates[0][0]
    return answer
