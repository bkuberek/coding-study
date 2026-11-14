def insert(intervals: list[list[int]], new_interval: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    start, end = new_interval
    index, count = 0, len(intervals)
    while index < count and intervals[index][1] < start:
        result.append(intervals[index])
        index += 1
    while index < count and intervals[index][0] <= end:
        start = min(start, intervals[index][0])
        end = max(end, intervals[index][1])
        index += 1
    result.append([start, end])
    result.extend(intervals[index:])
    return result
