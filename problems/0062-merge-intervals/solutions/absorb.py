def merge(intervals: list[list[int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for start, end in intervals:
        # Fold every merged interval that shares a point with [start, end] into it.
        separate = []
        for other_start, other_end in merged:
            if other_start <= end and start <= other_end:
                start, end = min(start, other_start), max(end, other_end)
            else:
                separate.append([other_start, other_end])
        separate.append([start, end])
        merged = separate
    return merged
