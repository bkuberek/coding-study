import heapq


def min_meeting_rooms(intervals: list[list[int]]) -> int:
    # End times of the meetings currently holding a room; the smallest is on top.
    ends: list[int] = []
    for start, end in sorted(intervals):
        if ends and ends[0] <= start:
            heapq.heapreplace(ends, end)
        else:
            heapq.heappush(ends, end)
    return len(ends)
