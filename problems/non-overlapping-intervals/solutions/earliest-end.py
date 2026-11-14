def erase_overlap_intervals(intervals: list[list[int]]) -> int:
    kept = 0
    last_end = None
    for start, end in sorted(intervals, key=lambda interval: interval[1]):
        if last_end is None or start >= last_end:
            kept += 1
            last_end = end
    return len(intervals) - kept
