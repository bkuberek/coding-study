def remove_covered_intervals(intervals: list[list[int]]) -> int:
    remaining = 0
    reach = -1  # the largest end among the intervals already swept
    # Equal starts: the longer interval comes first, so it covers the shorter ones after it.
    for _, end in sorted(intervals, key=lambda interval: (interval[0], -interval[1])):
        if end > reach:
            remaining += 1
            reach = end
    return remaining
